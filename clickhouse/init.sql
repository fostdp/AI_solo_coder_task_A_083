CREATE DATABASE IF NOT EXISTS ancient_book_monitor;

USE ancient_book_monitor;

DROP TABLE IF EXISTS env_sensor_data;
CREATE TABLE env_sensor_data (
    timestamp     DateTime64(3) DEFAULT now64(3),
    sensor_id     String,
    shelf_id      String,
    slot_id       String,
    temperature   Float32 DEFAULT 22.0,
    humidity      Float32 DEFAULT 50.0,
    light_lux     Float32 DEFAULT 0.0,
    voc_ppm       Float32 DEFAULT 0.0,
    mold_spores   Float32 DEFAULT 0.0,
    active_mold   UInt8 DEFAULT 0,
    rssi          Int16 DEFAULT -60
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (shelf_id, slot_id, timestamp)
TTL timestamp + INTERVAL 3 YEAR
SETTINGS index_granularity = 8192;

DROP TABLE IF EXISTS ph_sensor_data;
CREATE TABLE ph_sensor_data (
    timestamp     DateTime64(3) DEFAULT now64(3),
    sensor_id     String,
    shelf_id      String,
    slot_id       String,
    ph_value      Float32 DEFAULT 7.0,
    paper_cond    String DEFAULT 'GOOD',
    rssi          Int16 DEFAULT -60
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (slot_id, timestamp)
TTL timestamp + INTERVAL 3 YEAR
SETTINGS index_granularity = 8192;

DROP TABLE IF EXISTS bookshelf_metadata;
CREATE TABLE bookshelf_metadata (
    shelf_id      String,
    location      String DEFAULT '',
    rows_count    UInt8 DEFAULT 6,
    cols_count    UInt8 DEFAULT 8,
    book_count    UInt32 DEFAULT 0,
    description   String DEFAULT ''
) ENGINE = ReplacingMergeTree()
ORDER BY shelf_id;

DROP TABLE IF EXISTS book_slot_metadata;
CREATE TABLE book_slot_metadata (
    slot_id       String,
    shelf_id      String,
    row_num       UInt8,
    col_num       UInt8,
    book_title    String DEFAULT '',
    book_dynasty  String DEFAULT '',
    book_type     String DEFAULT '',
    book_count    UInt16 DEFAULT 1,
    paper_type    String DEFAULT 'default',
    sensor_env_id String DEFAULT '',
    sensor_ph_id  String DEFAULT ''
) ENGINE = ReplacingMergeTree()
ORDER BY (shelf_id, slot_id);

DROP TABLE IF EXISTS alert_events;
CREATE TABLE alert_events (
    event_id         String,
    timestamp        DateTime64(3) DEFAULT now64(3),
    alert_level      String,
    alert_type       String,
    shelf_id         String DEFAULT '',
    slot_id          String DEFAULT '',
    sensor_id        String DEFAULT '',
    metric_name      String DEFAULT '',
    metric_value     Float32 DEFAULT 0,
    threshold        Float32 DEFAULT 0,
    message          String DEFAULT '',
    is_acknowledged  UInt8 DEFAULT 0,
    ack_user         String DEFAULT '',
    ack_time         Int64 DEFAULT 0
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (timestamp, alert_level)
TTL timestamp + INTERVAL 1 YEAR
SETTINGS index_granularity = 4096;

DROP TABLE IF EXISTS mv_env_hourly;
DROP VIEW IF EXISTS mv_env_hourly_view;
CREATE TABLE mv_env_hourly (
    shelf_id         String,
    slot_id          String,
    ts_hour          DateTime64(3),
    temp_avg         Float32,
    temp_max         Float32,
    temp_min         Float32,
    humi_avg         Float32,
    humi_max         Float32,
    humi_min         Float32,
    light_avg        Float32,
    light_max        Float32,
    voc_avg          Float32,
    mold_avg         Float32,
    active_mold_cnt  UInt32,
    samples          UInt32
) ENGINE = SummingMergeTree()
ORDER BY (shelf_id, slot_id, ts_hour);

CREATE MATERIALIZED VIEW mv_env_hourly_view TO mv_env_hourly AS
SELECT
    shelf_id,
    slot_id,
    toStartOfHour(timestamp) AS ts_hour,
    avg(temperature)   AS temp_avg,
    max(temperature)   AS temp_max,
    min(temperature)   AS temp_min,
    avg(humidity)      AS humi_avg,
    max(humidity)      AS humi_max,
    min(humidity)      AS humi_min,
    avg(light_lux)     AS light_avg,
    max(light_lux)     AS light_max,
    avg(voc_ppm)       AS voc_avg,
    avg(mold_spores)   AS mold_avg,
    sum(active_mold)   AS active_mold_cnt,
    count()            AS samples
FROM env_sensor_data
GROUP BY shelf_id, slot_id, ts_hour;

DROP TABLE IF EXISTS mv_ph_daily;
DROP VIEW IF EXISTS mv_ph_daily_view;
CREATE TABLE mv_ph_daily (
    shelf_id     String,
    slot_id      String,
    day          Date,
    ph_avg       Float32,
    ph_min       Float32,
    ph_max       Float32,
    samples      UInt32
) ENGINE = SummingMergeTree()
ORDER BY (shelf_id, slot_id, day);

CREATE MATERIALIZED VIEW mv_ph_daily_view TO mv_ph_daily AS
SELECT
    shelf_id,
    slot_id,
    toDate(timestamp) AS day,
    avg(ph_value) AS ph_avg,
    min(ph_value) AS ph_min,
    max(ph_value) AS ph_max,
    count()       AS samples
FROM ph_sensor_data
GROUP BY shelf_id, slot_id, day;

DROP VIEW IF EXISTS mv_alert_auto_view;
CREATE MATERIALIZED VIEW mv_alert_auto_view TO alert_events AS
SELECT
    generateUUIDv4()                                                                 AS event_id,
    timestamp                                                                        AS timestamp,
    multiIf(
        ph_value < 5.5 OR active_mold = 1, 'RED',
        ph_value < 6.0 OR light_lux > 50, 'ORANGE',
        ph_value < 6.5 OR mold_spores > 500, 'YELLOW',
        'OK'
    )                                                                                AS alert_level,
    multiIf(
        ph_value < 5.5, 'CRITICAL_ACIDOSIS',
        active_mold = 1, 'ACTIVE_MOLD',
        ph_value < 6.0, 'MODERATE_ACIDOSIS',
        light_lux > 50, 'EXCESS_LIGHT',
        ph_value < 6.5, 'MILD_ACIDOSIS',
        mold_spores > 500, 'HIGH_SPORE',
        'NONE'
    )                                                                                AS alert_type,
    shelf_id                                                                         AS shelf_id,
    slot_id                                                                          AS slot_id,
    sensor_id                                                                        AS sensor_id,
    multiIf(
        ph_value < 6.5, 'ph_value',
        mold_spores > 500, 'mold_spores',
        active_mold = 1, 'active_mold',
        light_lux > 50, 'light_lux',
        'temperature'
    )                                                                                AS metric_name,
    multiIf(
        ph_value < 6.5, ph_value,
        mold_spores > 500, mold_spores,
        active_mold = 1, toFloat32(active_mold),
        light_lux > 50, light_lux,
        temperature
    )                                                                                AS metric_value,
    multiIf(
        ph_value < 5.5, toFloat32(5.5),
        ph_value < 6.0, toFloat32(6.0),
        ph_value < 6.5, toFloat32(6.5),
        mold_spores > 500, toFloat32(500),
        light_lux > 50, toFloat32(50),
        toFloat32(0)
    )                                                                                AS threshold,
    multiIf(
        ph_value < 5.5, '严重酸化：pH低于5.5，纸张纤维已严重受损',
        active_mold = 1, '活性霉菌检测到，存在不可逆转的生物破坏风险',
        ph_value < 6.0, '中度酸化：pH低于6.0，需立即进行脱酸处理',
        light_lux > 50, '光照超标：超过50lux将加速纸张光降解',
        ph_value < 6.5, '轻度酸化：pH低于6.5，建议启动预防性脱酸',
        mold_spores > 500, '霉菌孢子浓度过高：>500 CFU/m3，存在萌发风险',
        'OK'
    )                                                                                AS message,
    toUInt8(0)                                                                       AS is_acknowledged,
    ''                                                                               AS ack_user,
    toInt64(0)                                                                       AS ack_time
FROM (
    SELECT
        e.timestamp, e.sensor_id, e.shelf_id, e.slot_id,
        e.temperature, e.humidity, e.light_lux, e.voc_ppm, e.mold_spores, e.active_mold,
        coalesce(p.ph_value, 6.8) AS ph_value
    FROM env_sensor_data e
    LEFT JOIN ph_sensor_data p ON p.slot_id = e.slot_id AND abs(toUnixTimestamp(e.timestamp) - toUnixTimestamp(p.timestamp)) < 3600
)
WHERE ph_value < 6.5 OR mold_spores > 500 OR light_lux > 50 OR active_mold = 1;

INSERT INTO bookshelf_metadata (shelf_id, location, rows_count, cols_count, book_count, description) VALUES
    ('SH-A-01', 'A区一层-01', 6, 8, 4320, '明版刻本专藏区（本草类）'),
    ('SH-A-02', 'A区一层-02', 6, 8, 4200, '明版刻本专藏区（医案类）'),
    ('SH-A-03', 'A区一层-03', 6, 8, 4280, '明版手稿与抄本专区'),
    ('SH-B-01', 'B区二层-01', 6, 8, 4250, '清版官修医书专藏（医宗金鉴等）'),
    ('SH-B-02', 'B区二层-02', 6, 8, 4310, '清版家刻本与秘方专藏'),
    ('SH-C-01', 'C区善本室-01', 6, 8, 4400, '宋元残卷·善本孤本区（恒温恒湿）'),
    ('SH-C-02', 'C区善本室-02', 6, 8, 4240, '宫廷医案·御药房档案专区');

INSERT INTO book_slot_metadata (slot_id, shelf_id, row_num, col_num, book_title, book_dynasty, book_type, book_count, paper_type, sensor_env_id, sensor_ph_id) VALUES
('SH-A-01-R01-C01','SH-A-01',1,1,'本草纲目','明','刻本',12,'bamboo','ENV-001','PH-001'),
('SH-A-01-R01-C02','SH-A-01',1,2,'本草纲目','明','刻本',10,'bamboo','ENV-001','PH-001'),
('SH-A-01-R01-C03','SH-A-01',1,3,'证类本草','明','刻本',8,'bamboo','ENV-002','PH-002'),
('SH-A-01-R01-C04','SH-A-01',1,4,'本草经疏','明','刻本',9,'xuan','ENV-002','PH-002'),
('SH-A-01-R01-C05','SH-A-01',1,5,'景岳全书','明','刻本',14,'bamboo','ENV-003','PH-003'),
('SH-A-01-R01-C06','SH-A-01',1,6,'景岳全书','明','刻本',12,'bamboo','ENV-003','PH-003'),
('SH-A-01-R01-C07','SH-A-01',1,7,'医学纲目','明','刻本',10,'xuan','ENV-004','PH-004'),
('SH-A-01-R01-C08','SH-A-01',1,8,'赤水玄珠','明','刻本',8,'bamboo','ENV-004','PH-004'),
('SH-A-01-R02-C01','SH-A-01',2,1,'伤寒论','明','刻本',6,'xuan','ENV-005','PH-005'),
('SH-A-01-R02-C02','SH-A-01',2,2,'金匮要略','明','刻本',5,'xuan','ENV-005','PH-005'),
('SH-A-01-R02-C03','SH-A-01',2,3,'黄帝内经素问','明','刻本',7,'bamboo','ENV-006','PH-006'),
('SH-A-01-R02-C04','SH-A-01',2,4,'黄帝内经灵枢','明','刻本',6,'bamboo','ENV-006','PH-006'),
('SH-A-01-R02-C05','SH-A-01',2,5,'难经本义','明','刻本',4,'xuan','ENV-007','PH-007'),
('SH-A-01-R02-C06','SH-A-01',2,6,'针灸甲乙经','明','刻本',5,'bamboo','ENV-007','PH-007'),
('SH-A-01-R02-C07','SH-A-01',2,7,'脉经','明','刻本',4,'bamboo','ENV-008','PH-008'),
('SH-A-01-R02-C08','SH-A-01',2,8,'奇经八脉考','明','刻本',3,'xuan','ENV-008','PH-008'),
('SH-A-01-R03-C01','SH-A-01',3,1,'千金要方','明','刻本',12,'bamboo','ENV-009','PH-009'),
('SH-A-01-R03-C02','SH-A-01',3,2,'千金翼方','明','刻本',10,'bamboo','ENV-009','PH-009'),
('SH-A-01-R03-C03','SH-A-01',3,3,'外台秘要','明','刻本',11,'bamboo','ENV-010','PH-010'),
('SH-A-01-R03-C04','SH-A-01',3,4,'太平惠民和剂局方','明','刻本',7,'xuan','ENV-010','PH-010'),
('SH-A-01-R03-C05','SH-A-01',3,5,'圣济总录','明','刻本',16,'bamboo','ENV-011','PH-011'),
('SH-A-01-R03-C06','SH-A-01',3,6,'三因极一病证方论','明','刻本',6,'xuan','ENV-011','PH-011'),
('SH-A-01-R03-C07','SH-A-01',3,7,'儒门事亲','明','刻本',5,'bamboo','ENV-012','PH-012'),
('SH-A-01-R03-C08','SH-A-01',3,8,'河间六书','明','刻本',8,'bamboo','ENV-012','PH-012'),
('SH-A-01-R04-C01','SH-A-01',4,1,'脾胃论','明','刻本',4,'xuan','ENV-013','PH-013'),
('SH-A-01-R04-C02','SH-A-01',4,2,'兰室秘藏','明','刻本',3,'xuan','ENV-013','PH-013'),
('SH-A-01-R04-C03','SH-A-01',4,3,'格致余论','明','刻本',3,'bamboo','ENV-014','PH-014'),
('SH-A-01-R04-C04','SH-A-01',4,4,'丹溪心法','明','刻本',6,'bamboo','ENV-014','PH-014'),
('SH-A-01-R04-C05','SH-A-01',4,5,'东垣试效方','明','刻本',5,'xuan','ENV-015','PH-015'),
('SH-A-01-R04-C06','SH-A-01',4,6,'医经溯洄集','明','刻本',3,'bamboo','ENV-015','PH-015'),
('SH-A-01-R04-C07','SH-A-01',4,7,'薛氏医案','明','医案',9,'bamboo','ENV-016','PH-016'),
('SH-A-01-R04-C08','SH-A-01',4,8,'名医类案','明','医案',10,'bamboo','ENV-016','PH-016'),
('SH-A-01-R05-C01','SH-A-01',5,1,'外科正宗','明','刻本',6,'bamboo','ENV-017','PH-017'),
('SH-A-01-R05-C02','SH-A-01',5,2,'外科发挥','明','刻本',4,'xuan','ENV-017','PH-017'),
('SH-A-01-R05-C03','SH-A-01',5,3,'妇人良方','明','刻本',8,'bamboo','ENV-018','PH-018'),
('SH-A-01-R05-C04','SH-A-01',5,4,'女科证治准绳','明','刻本',7,'xuan','ENV-018','PH-018'),
('SH-A-01-R05-C05','SH-A-01',5,5,'幼科证治准绳','明','刻本',6,'bamboo','ENV-019','PH-019'),
('SH-A-01-R05-C06','SH-A-01',5,6,'证治准绳','明','刻本',14,'bamboo','ENV-019','PH-019'),
('SH-A-01-R05-C07','SH-A-01',5,7,'审视瑶函','明','刻本',5,'xuan','ENV-020','PH-020'),
('SH-A-01-R05-C08','SH-A-01',5,8,'口齿类要','明','刻本',3,'bamboo','ENV-020','PH-020'),
('SH-A-01-R06-C01','SH-A-01',6,1,'瘟疫论','明','刻本',4,'bamboo','ENV-021','PH-001'),
('SH-A-01-R06-C02','SH-A-01',6,2,'温疫论补注','明','刻本',3,'xuan','ENV-021','PH-001'),
('SH-A-01-R06-C03','SH-A-01',6,3,'广瘟疫论','明','刻本',3,'bamboo','ENV-022','PH-002'),
('SH-A-01-R06-C04','SH-A-01',6,4,'温热暑疫全书','明','刻本',5,'bamboo','ENV-022','PH-002'),
('SH-A-01-R06-C05','SH-A-01',6,5,'素问玄机原病式','明','刻本',4,'xuan','ENV-023','PH-003'),
('SH-A-01-R06-C06','SH-A-01',6,6,'宣明论方','明','刻本',5,'bamboo','ENV-023','PH-003'),
('SH-A-01-R06-C07','SH-A-01',6,7,'伤寒六书','明','刻本',6,'bamboo','ENV-024','PH-004'),
('SH-A-01-R06-C08','SH-A-01',6,8,'伤寒准绳','明','刻本',7,'xuan','ENV-024','PH-004');
