import json
import random
import threading
import time
from datetime import datetime, timezone

try:
    import paho.mqtt.client as mqtt_client
    HAS_PAHO = True
except ImportError:
    HAS_PAHO = False

SHELF_IDS = ["SH-A-01", "SH-A-02", "SH-A-03", "SH-B-01", "SH-B-02", "SH-C-01", "SH-C-02"]
ROWS, COLS = 6, 8
BOOK_TITLES = [
    "本草纲目", "伤寒论", "金匮要略", "黄帝内经", "千金要方",
    "证类本草", "景岳全书", "医宗金鉴", "外科正宗", "针灸甲乙经",
    "脉经", "诸病源候论", "温病条辨", "温热经纬", "脾胃论",
    "兰室秘藏", "格致余论", "儒门事亲", "河间六书", "东垣试效方",
]

BASE_TEMP = 21.0
BASE_HUMI = 48.0
BASE_PH = 6.85


class SensorSimulator:
    def __init__(self, broker: str = "localhost", port: int = 1883, interval_sec: int = 300):
        self.broker = broker
        self.port = port
        self.interval_sec = interval_sec
        self._stop = threading.Event()
        self._threads = []
        self._state = self._init_state()
        if HAS_PAHO:
            self._mqtt = mqtt_client.Client(
                callback_api_version=getattr(mqtt_client, "CallbackAPIVersion", mqtt_client.MQTTv311),
                client_id=f"abm_sim_{int(time.time())}",
            )
        else:
            self._mqtt = None

    def _init_state(self):
        state = {}
        for sid in SHELF_IDS:
            for r in range(1, ROWS + 1):
                for c in range(1, COLS + 1):
                    slot_id = f"{sid}-R{r:02d}-C{c:02d}"
                    env_no = (hash(slot_id) % 50) + 1
                    ph_no = (hash(slot_id + "p") % 20) + 1
                    rseed = hash(slot_id) & 0xFFFFFFFF
                    rng = random.Random(rseed)
                    anomaly_mold = 1.0
                    anomaly_humi = 1.0
                    anomaly_ph = 0.0
                    anomaly_temp = 0.0
                    if (rseed % 37) < 3:
                        anomaly_ph = -1.2
                        anomaly_humi = 1.15
                    if (rseed % 53) < 2:
                        anomaly_mold = 4.5
                    if (rseed % 71) < 2:
                        anomaly_temp = 6.0
                        anomaly_humi = 1.25
                    state[slot_id] = {
                        "shelf_id": sid,
                        "slot_id": slot_id,
                        "row": r, "col": c,
                        "env_id": f"ENV-{env_no:03d}",
                        "ph_id": f"PH-{ph_no:03d}",
                        "temp": BASE_TEMP + anomaly_temp + rng.uniform(-1.0, 1.0),
                        "humi": BASE_HUMI * anomaly_humi + rng.uniform(-3.0, 3.0),
                        "ph": BASE_PH + anomaly_ph + rng.uniform(-0.08, 0.08),
                        "mold": 150.0 * anomaly_mold + rng.uniform(0, 150),
                        "light_factor": rng.uniform(0.5, 1.5),
                        "active_mold_prob": 0.002 if anomaly_mold > 2.0 else 0.0002,
                    }
        return state

    def start(self):
        if self._mqtt:
            try:
                self._mqtt.connect(self.broker, self.port, keepalive=60)
                self._mqtt.loop_start()
                print(f"[SIM] Connected to MQTT {self.broker}:{self.port}")
            except Exception as e:
                print(f"[SIM] MQTT connect failed, running in local-mode only: {e}")
                self._mqtt = None
        else:
            print("[SIM] paho-mqtt not installed; printing payloads to stdout.")

        env_thread = threading.Thread(target=self._env_loop, name="sim_env", daemon=True)
        ph_thread = threading.Thread(target=self._ph_loop, name="sim_ph", daemon=True)
        env_thread.start()
        ph_thread.start()
        self._threads.extend([env_thread, ph_thread])
        print(f"[SIM] Sensor simulator running. {len(self._state)} slots, env every {self.interval_sec}s, ph every {self.interval_sec}s.")

    def stop(self):
        self._stop.set()
        for t in self._threads:
            t.join(timeout=10)
        if self._mqtt:
            try:
                self._mqtt.loop_stop()
                self._mqtt.disconnect()
            except Exception:
                pass

    def _env_loop(self):
        step_sec = max(2, self.interval_sec // 2)
        t0 = time.time()
        step = 0
        while not self._stop.is_set():
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            t_hours = (time.time() - t0) / 3600.0
            diurnal = __import__("math").sin(2 * 3.14159 * (t_hours % 24) / 24)
            slot_list = list(self._state.values())
            random.shuffle(slot_list)
            for s in slot_list:
                self._step_env(s, diurnal)
                payload = {
                    "timestamp_ms": now_ms,
                    "sensor_id": s["env_id"],
                    "shelf_id": s["shelf_id"],
                    "slot_id": s["slot_id"],
                    "temperature": round(s["temp"], 2),
                    "humidity": round(s["humi"], 2),
                    "light_lux": round(max(0.0, 20 + diurnal * 25 + random.gauss(0, 3)) * s["light_factor"], 1),
                    "voc_ppm": round(random.expovariate(1 / 0.4), 3),
                    "mold_spores": round(s["mold"], 0),
                    "active_mold": 1 if random.random() < s["active_mold_prob"] else 0,
                    "rssi": -50 - random.randint(0, 40),
                }
                self._publish(f"sensor/env/{s['env_id']}", payload)
            step += 1
            time.sleep(step_sec)

    def _step_env(self, s, diurnal):
        s["temp"] += random.gauss(0, 0.15) + diurnal * 0.1
        s["temp"] = max(14.0, min(34.0, s["temp"]))
        s["humi"] += random.gauss(0, 0.8) - diurnal * 0.5
        s["humi"] = max(35.0, min(78.0, s["humi"]))
        s["mold"] += random.gauss(0, 15) + (s["humi"] - 55) * 2.5
        s["mold"] = max(20.0, min(3500.0, s["mold"]))

    def _ph_loop(self):
        step_sec = max(3, self.interval_sec)
        while not self._stop.is_set():
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            slot_list = list(self._state.values())
            random.shuffle(slot_list)
            for s in slot_list:
                self._step_ph(s)
                payload = {
                    "timestamp_ms": now_ms,
                    "sensor_id": s["ph_id"],
                    "shelf_id": s["shelf_id"],
                    "slot_id": s["slot_id"],
                    "ph_value": round(s["ph"], 3),
                    "rssi": -55 - random.randint(0, 30),
                }
                self._publish(f"sensor/ph/{s['ph_id']}", payload)
            time.sleep(step_sec)

    def _step_ph(self, s):
        temp_factor = max(0.0, (s["temp"] - 20.0) / 20.0)
        humi_factor = max(0.0, (s["humi"] - 50.0) / 40.0)
        decay_rate = (0.00008 + temp_factor * 0.00015 + humi_factor * 0.00012) * (self.interval_sec / 300.0)
        s["ph"] += random.gauss(0, 0.01) - decay_rate
        s["ph"] = max(4.0, min(7.8, s["ph"]))

    def _publish(self, topic: str, payload: dict):
        if self._mqtt:
            try:
                info = self._mqtt.publish(topic, json.dumps(payload), qos=1)
                info.wait_for_publish(timeout=2)
            except Exception as e:
                print(f"[SIM] publish error: {e}")
        else:
            short = {k: v for k, v in payload.items() if k in ("sensor_id", "shelf_id", "slot_id")}
            if "ph_value" in payload:
                short["ph"] = payload["ph_value"]
            else:
                short["T"] = payload["temperature"]
                short["H"] = payload["humidity"]
                short["M"] = payload["mold_spores"]
                short["L"] = payload["light_lux"]
            print(f"[SIM][{topic}] {json.dumps(short, ensure_ascii=False)}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="古籍微环境传感器模拟器（MQTT）")
    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--interval", type=int, default=300, help="上报周期（秒），默认300秒=5分钟")
    parser.add_argument("--fast", action="store_true", help="快速模式：每2秒上报一次，便于演示")
    args = parser.parse_args()
    interval = 2 if args.fast else args.interval
    sim = SensorSimulator(broker=args.broker, port=args.port, interval_sec=interval)
    sim.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SIM] Stopping...")
        sim.stop()


if __name__ == "__main__":
    main()
