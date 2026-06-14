import json
import logging
import smtplib
import uuid
import time
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any

import requests

from ..config import settings
from ..database import get_ch

logger = logging.getLogger(__name__)

LEVEL_COLORS = {
    "RED": 0xDC2626,
    "ORANGE": 0xEA580C,
    "YELLOW": 0xCA8A04,
    "GREEN": 0x16A34A,
}

LEVEL_LABELS = {
    "RED": "🔴 红色告警",
    "ORANGE": "🟠 橙色告警",
    "YELLOW": "🟡 黄色告警",
    "GREEN": "🟢 恢复正常",
}


class AlertManager:
    def __init__(self):
        self._last_alert_ts: Dict[str, int] = {}
        self._cooldown_ms = settings.alert_cooldown_minutes * 60 * 1000
        self._ch = get_ch()

    def _key(self, shelf_id: str, slot_id: str, alert_type: str) -> str:
        return f"{shelf_id}|{slot_id}|{alert_type}"

    def _is_cooldown(self, key: str) -> bool:
        now_ms = int(time.time() * 1000)
        last = self._last_alert_ts.get(key, 0)
        return (now_ms - last) < self._cooldown_ms

    def _update_cooldown(self, key: str):
        self._last_alert_ts[key] = int(time.time() * 1000)

    def create_alert(
        self,
        alert_level: str,
        alert_type: str,
        shelf_id: str,
        slot_id: str,
        sensor_id: str,
        metric_name: str,
        metric_value: float,
        threshold: float,
        message: str,
    ) -> Optional[str]:
        key = self._key(shelf_id, slot_id, alert_type)
        if self._is_cooldown(key):
            logger.debug(f"Alert cooldown: {key}")
            return None

        alert_level = alert_level.upper()
        event_id = str(uuid.uuid4())
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

        try:
            table_cols = [
                "event_id", "timestamp", "alert_level", "alert_type",
                "shelf_id", "slot_id", "sensor_id", "metric_name",
                "metric_value", "threshold", "message",
                "is_acknowledged", "ack_user", "ack_time",
            ]
            row = [
                f"'{event_id}'", f"{now_ms}", f"'{alert_level}'", f"'{alert_type}'",
                f"'{shelf_id}'", f"'{slot_id}'", f"'{sensor_id}'", f"'{metric_name}'",
                f"{metric_value}", f"{threshold}", f"'{message}'",
                "0", "''", "0",
            ]
            self._ch.batch_insert("alert_events", table_cols, [row])
            self._update_cooldown(key)
            self._dispatch_notifications(
                event_id, alert_level, alert_type, shelf_id, slot_id,
                metric_name, metric_value, threshold, message,
            )
            logger.info(f"Alert created: {alert_level} {alert_type} {shelf_id}/{slot_id}")
            return event_id
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            return None

    def _dispatch_notifications(
        self,
        event_id: str,
        alert_level: str,
        alert_type: str,
        shelf_id: str,
        slot_id: str,
        metric_name: str,
        metric_value: float,
        threshold: float,
        message: str,
    ):
        ts_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        title = f"{LEVEL_LABELS.get(alert_level, alert_level)} | 古籍微环境监测"
        text_lines = [
            f"**{title}**",
            f"📚 **书架/格口**: {shelf_id} / {slot_id}",
            f"📊 **告警类型**: {alert_type}",
            f"🔬 **监测指标**: {metric_name} = **{metric_value:.3f}** (阈值: {threshold})",
            f"💬 **告警信息**: {message}",
            f"⏰ **触发时间**: {ts_str}",
            f"🆔 **事件ID**: {event_id[:12]}…",
            "---",
            "请登录古籍监测系统查看详情并处置。",
        ]
        markdown_text = "\n".join(text_lines)

        dingtalk_sent = False
        if settings.dingtalk_webhook:
            dingtalk_sent = self._send_dingtalk(title, markdown_text, alert_level)

        email_sent = False
        if settings.smtp_host and settings.alert_email_to:
            email_sent = self._send_email(
                title, alert_level, alert_type, shelf_id, slot_id,
                metric_name, metric_value, threshold, message, ts_str, event_id,
            )

        logger.info(f"Alert dispatch: dingtalk={dingtalk_sent}, email={email_sent}")

    def _send_dingtalk(self, title: str, markdown_text: str, alert_level: str) -> bool:
        try:
            at_mobiles = []
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": markdown_text,
                },
                "at": {
                    "isAtAll": alert_level in ("RED", "ORANGE"),
                    "atMobiles": at_mobiles,
                },
            }
            resp = requests.post(
                settings.dingtalk_webhook,
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return bool(data.get("errcode") == 0)
        except Exception as e:
            logger.warning(f"DingTalk send failed: {e}")
            return False

    def _send_email(
        self,
        title: str,
        alert_level: str,
        alert_type: str,
        shelf_id: str,
        slot_id: str,
        metric_name: str,
        metric_value: float,
        threshold: float,
        message: str,
        ts_str: str,
        event_id: str,
    ) -> bool:
        try:
            html = f"""
            <div style="font-family:'PingFang SC',Microsoft YaHei,sans-serif;padding:24px;max-width:680px;">
                <div style="background:linear-gradient(90deg,#{LEVEL_COLORS.get(alert_level,0x999999):06x},#1e293b);
                            padding:18px 24px;border-radius:10px 10px 0 0;color:white;">
                    <h2 style="margin:0;font-size:18px;">📚 {title}</h2>
                    <p style="margin:6px 0 0 0;opacity:.9;font-size:12px;">古代医学文献馆藏微环境监测与古籍病害预测系统</p>
                </div>
                <div style="border:1px solid #e2e8f0;border-top:none;padding:20px 24px;border-radius:0 0 10px 10px;background:#fff;">
                    <table style="width:100%;border-collapse:collapse;">
                        <tr><td style="padding:8px 0;color:#64748b;width:130px;">告警级别</td>
                            <td style="padding:8px 0;font-weight:600;color:#{LEVEL_COLORS.get(alert_level,0x999999):06x};">{LEVEL_LABELS.get(alert_level, alert_level)}</td></tr>
                        <tr><td style="padding:8px 0;color:#64748b;">书架 / 格口</td>
                            <td style="padding:8px 0;font-weight:600;">{shelf_id} · {slot_id}</td></tr>
                        <tr><td style="padding:8px 0;color:#64748b;">告警类型</td>
                            <td style="padding:8px 0;">{alert_type}</td></tr>
                        <tr><td style="padding:8px 0;color:#64748b;">指标/阈值</td>
                            <td style="padding:8px 0;">
                                <span style="font-weight:600;color:#ea580c;">{metric_name}: {metric_value:.3f}</span>
                                &nbsp;·&nbsp;阈值: {threshold}
                            </td></tr>
                        <tr><td style="padding:8px 0;color:#64748b;">告警信息</td>
                            <td style="padding:8px 0;">{message}</td></tr>
                        <tr><td style="padding:8px 0;color:#64748b;">触发时间</td>
                            <td style="padding:8px 0;">{ts_str}</td></tr>
                        <tr><td style="padding:8px 0;color:#64748b;">事件ID</td>
                            <td style="padding:8px 0;font-family:monospace;font-size:12px;color:#94a3b8;">{event_id}</td></tr>
                    </table>
                    <div style="margin-top:18px;padding:12px 14px;background:#f8fafc;border-radius:8px;border-left:4px solid #3b82f6;">
                        <div style="font-size:12px;color:#475569;">建议处置流程：</div>
                        <div style="font-size:12px;color:#475569;margin-top:4px;">
                            1. 登录系统确认告警详情 → 2. 现场核查纸质载体 → 3. 启动应急处置（调温/脱酸/熏蒸）→ 4. 确认并归档
                        </div>
                    </div>
                </div>
            </div>
            """
            msg = MIMEMultipart("alternative")
            msg["Subject"] = title
            msg["From"] = settings.smtp_user or "abm@museum.local"
            msg["To"] = settings.alert_email_to
            msg.attach(MIMEText(html, "html", "utf-8"))

            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as s:
                s.ehlo()
                try:
                    s.starttls()
                except smtplib.SMTPException:
                    pass
                if settings.smtp_user and settings.smtp_password:
                    s.login(settings.smtp_user, settings.smtp_password)
                s.sendmail(msg["From"], [addr.strip() for addr in settings.alert_email_to.split(",")], msg.as_string())
            return True
        except Exception as e:
            logger.warning(f"Email send failed: {e}")
            return False

    def evaluate_and_alert(
        self,
        shelf_id: str,
        slot_id: str,
        sensor_env_id: str,
        sensor_ph_id: str,
        ph_value: Optional[float],
        temperature: float,
        humidity: float,
        light_lux: float,
        voc_ppm: float,
        mold_spores: float,
        active_mold: int,
    ) -> List[str]:
        created_ids: List[str] = []

        if active_mold == 1:
            eid = self.create_alert(
                "RED", "ACTIVE_MOLD", shelf_id, slot_id, sensor_env_id,
                "active_mold", 1.0, 0.0,
                "活性霉菌检测到，存在不可逆转的生物破坏风险，建议立即隔离并专业熏蒸处置。",
            )
            if eid: created_ids.append(eid)

        if ph_value is not None:
            if ph_value < 5.5:
                eid = self.create_alert(
                    "RED", "CRITICAL_ACIDOSIS", shelf_id, slot_id, sensor_ph_id,
                    "ph_value", ph_value, 5.5,
                    f"严重酸化：pH={ph_value:.2f} < 5.5，纸张纤维素已严重降解，需紧急脱酸并环境调控。",
                )
                if eid: created_ids.append(eid)
            elif ph_value < 6.0:
                eid = self.create_alert(
                    "ORANGE", "MODERATE_ACIDOSIS", shelf_id, slot_id, sensor_ph_id,
                    "ph_value", ph_value, 6.0,
                    f"中度酸化：pH={ph_value:.2f} < 6.0，建议尽快启动脱酸处理方案。",
                )
                if eid: created_ids.append(eid)
            elif ph_value < 6.5:
                eid = self.create_alert(
                    "YELLOW", "MILD_ACIDOSIS", shelf_id, slot_id, sensor_ph_id,
                    "ph_value", ph_value, 6.5,
                    f"轻度酸化：pH={ph_value:.2f} < 6.5，建议启动预防性脱酸并降低库温。",
                )
                if eid: created_ids.append(eid)

        if mold_spores > 500 and active_mold != 1:
            lvl = "ORANGE" if mold_spores > 1500 else "YELLOW"
            eid = self.create_alert(
                lvl, "HIGH_SPORE", shelf_id, slot_id, sensor_env_id,
                "mold_spores", mold_spores, 500.0,
                f"霉菌孢子浓度过高：{mold_spores:.0f} CFU/m³ > 500，存在萌发风险，建议降低湿度并启动熏蒸。",
            )
            if eid: created_ids.append(eid)

        if light_lux > 50:
            lvl = "RED" if light_lux > 200 else "ORANGE"
            eid = self.create_alert(
                lvl, "EXCESS_LIGHT", shelf_id, slot_id, sensor_env_id,
                "light_lux", light_lux, 50.0,
                f"光照超标：{light_lux:.1f} lux > 50，将加速纸张光降解与色素褪色，请立即遮光。",
            )
            if eid: created_ids.append(eid)

        return created_ids


alert_manager = AlertManager()
