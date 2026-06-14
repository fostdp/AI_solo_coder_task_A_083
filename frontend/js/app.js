const API = '/api/v1';
const SIMULATE = false;

class Api {
  static async get(path, params = {}) {
    const q = new URLSearchParams(params).toString();
    const url = q ? `${API}${path}?${q}` : `${API}${path}`;
    try {
      const r = await fetch(url, { headers: { 'Accept': 'application/json' } });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return await r.json();
    } catch (e) {
      console.warn(`API fallback ${path}:`, e.message);
      return null;
    }
  }
  static async post(path, body) {
    try {
      const r = await fetch(`${API}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return await r.json();
    } catch (e) {
      console.warn(`API POST fallback ${path}:`, e.message);
      return null;
    }
  }
}

const AppState = {
  currentShelfId: null,
  currentSlot: null,
  renderer: null,
  autoRefresh: true,
  shelves: [],
};

function showToast(msg, ms = 2000) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.remove('hidden');
  setTimeout(() => t.classList.add('hidden'), ms);
}

async function loadShelves() {
  const r = await Api.get('/shelves');
  const list = r?.data;
  let shelves;
  if (list && list.length) {
    shelves = list;
  } else {
    shelves = [
      { shelf_id: 'SH-A-01', location: 'A区一层-01', rows_count: 6, cols_count: 8, book_count: 4320, description: '明版刻本专藏区（本草类）' },
      { shelf_id: 'SH-A-02', location: 'A区一层-02', rows_count: 6, cols_count: 8, book_count: 4200, description: '明版刻本专藏区（医案类）' },
      { shelf_id: 'SH-A-03', location: 'A区一层-03', rows_count: 6, cols_count: 8, book_count: 4280, description: '明版手稿与抄本专区' },
      { shelf_id: 'SH-B-01', location: 'B区二层-01', rows_count: 6, cols_count: 8, book_count: 4250, description: '清版官修医书专藏' },
      { shelf_id: 'SH-B-02', location: 'B区二层-02', rows_count: 6, cols_count: 8, book_count: 4310, description: '清版家刻本与秘方专藏' },
      { shelf_id: 'SH-C-01', location: 'C区善本室-01', rows_count: 6, cols_count: 8, book_count: 4400, description: '宋元残卷·善本孤本区' },
      { shelf_id: 'SH-C-02', location: 'C区善本室-02', rows_count: 6, cols_count: 8, book_count: 4240, description: '宫廷医案·御药房档案专区' },
    ];
  }
  AppState.shelves = shelves;
  const ul = document.getElementById('shelfList');
  ul.innerHTML = '';
  shelves.forEach((s, i) => {
    const li = document.createElement('li');
    li.innerHTML = `<div class="sn">${s.shelf_id} <span style="color:var(--sub);font-size:10px;">(${s.rows_count}×${s.cols_count})</span></div>
                    <div class="sl">${s.location || ''} · ${s.description || ''}</div>`;
    li.onclick = () => selectShelf(s.shelf_id, i);
    ul.appendChild(li);
  });
  if (shelves.length) selectShelf(shelves[0].shelf_id, 0);
}

function selectShelf(shelfId, idx) {
  AppState.currentShelfId = shelfId;
  document.querySelectorAll('#shelfList li').forEach((li, i) => {
    li.classList.toggle('active', i === idx);
  });
  const s = AppState.shelves[idx];
  document.getElementById('currentShelfTitle').textContent = `🗄 ${s.shelf_id}`;
  document.getElementById('currentShelfDesc').textContent = `${s.location || ''} · ${s.description || ''} · 共 ${s.book_count || '?'} 册`;
  loadHeatmap(shelfId);
}

async function loadHeatmap(shelfId) {
  const r = await Api.get('/heatmap', { shelf_id: shelfId });
  const data = r?.data || [];
  const rows = r?.rows || 6;
  const cols = r?.cols || 8;
  AppState.renderer.setShelf(shelfId, rows, cols, data);
}

async function loadOverview() {
  const r = await Api.get('/overview/stats');
  const s = r || {
    total_books: 30000, total_shelves: 7, total_env_sensors: 50, total_ph_sensors: 20,
    alerts_24h: { red: 0, orange: 2, yellow: 5, unacknowledged: 3 },
    realtime_avg: { temperature_c: 21.5, humidity_percent: 48.0, ph: 6.6, mold_spores_cfu: 280 },
  };
  const box = document.getElementById('overviewStats');
  const setStat = (i, v, extra = '') => {
    box.children[i].querySelector('.v').innerHTML = v + extra;
  };
  setStat(0, s.total_books?.toLocaleString() || '—');
  setStat(1, s.realtime_avg?.temperature_c?.toFixed(1) || '—', '<span class="u" style="font-size:10px;color:var(--sub);">℃</span>');
  setStat(2, s.realtime_avg?.humidity_percent?.toFixed(1) || '—', '<span class="u" style="font-size:10px;color:var(--sub);">%</span>');
  setStat(3, s.realtime_avg?.ph?.toFixed(2) || '—');
  setStat(4, Math.round(s.realtime_avg?.mold_spores_cfu || 0).toLocaleString(), '<span class="u" style="font-size:10px;color:var(--sub);">CFU</span>');
  const a = s.alerts_24h || {};
  box.children[5].querySelector('.v').innerHTML =
    `<em class="r">${a.red || 0}</em><em class="o">${a.orange || 0}</em><em class="y">${a.yellow || 0}</em>`;
}

async function loadAlerts() {
  const r = await Api.get('/alerts', { hours: 24, limit: 8 });
  const rows = r?.data || [];
  const box = document.getElementById('alertsList');
  if (!rows.length) {
    box.innerHTML = '<div class="empty">暂无告警</div>';
    return;
  }
  box.innerHTML = '';
  rows.slice(0, 8).forEach(a => {
    const lv = (a.alert_level || '').toLowerCase();
    const el = document.createElement('div');
    el.className = `alert-item ${lv}`;
    const ts = a.timestamp ? new Date(a.timestamp).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '';
    el.innerHTML = `
      <div class="top">
        <span class="lv">${a.alert_level || ''}</span>
        <span class="tm">${ts}</span>
      </div>
      <div class="msg">${a.message || a.alert_type || ''}</div>
      ${a.slot_id ? `<div class="slot">📍 ${a.shelf_id || ''} / ${a.slot_id || ''}</div>` : ''}
    `;
    el.style.cursor = 'pointer';
    el.onclick = () => {
      if (a.shelf_id) {
        const idx = AppState.shelves.findIndex(s => s.shelf_id === a.shelf_id);
        if (idx >= 0) selectShelf(a.shelf_id, idx);
      }
    };
    box.appendChild(el);
  });
}

async function onSlotClick(slotBook) {
  const slot = slotBook.slot || slotBook.data;
  const b = slotBook;
  if (!slot || !slot.slot_id) return;
  AppState.currentSlot = slot;
  showSlotDetail(slot, b.data);
  await loadSlotTrends(slot);
}

function showSlotDetail(slot, fullData) {
  const shelf = AppState.shelves.find(s => s.shelf_id === AppState.currentShelfId) || {};
  document.getElementById('emptyDetail').classList.add('hidden');
  document.getElementById('detailContent').classList.remove('hidden');

  const sid = slot.slot_id;
  const title = slot.book_title || fullData?.book_title || '—';
  const dyn = slot.book_dynasty || fullData?.book_dynasty || '';
  const btype = slot.book_type || fullData?.book_type || '';
  const bcnt = slot.book_count || fullData?.book_count || '?';
  const senv = slot.sensor_env_id || fullData?.sensor_env_id || '—';
  const sph = slot.sensor_ph_id || fullData?.sensor_ph_id || '—';

  document.getElementById('slotId').textContent = `📖 ${sid} · ${title}`;
  document.getElementById('slotMeta').innerHTML =
    `[${dyn || '?'}代] ${btype || '?'} · 藏 ${bcnt} 册 · 传感器:${senv}/${sph}<br/>位置:${shelf.location || shelf.shelf_id || ''}`;

  const m = fullData?.metrics || slot.metrics || {};
  const s = fullData?.scores || slot.scores || {};
  const p = fullData?.prediction || slot.prediction || {};

  document.getElementById('mTemp').innerHTML = `${(m.temperature ?? '—')}<span class="u">℃</span>`;
  document.getElementById('mHumi').innerHTML = `${(m.humidity ?? '—')}<span class="u">%</span>`;
  const ph = m.ph ?? p.ph_30d ?? '—';
  document.getElementById('mPh').innerHTML = `${ph}`;
  const phTr = document.getElementById('mPhTr');
  if (p.aging_rate !== undefined) {
    phTr.innerHTML = `年下降速率: <b style="color:#fdba74;">${p.aging_rate.toFixed?.(3) ?? p.aging_rate} pH/年</b>`;
  } else phTr.textContent = '';
  document.getElementById('mMold').innerHTML = `${Math.round(m.mold_spores ?? 0).toLocaleString()}<span class="u">CFU/m³</span>`;
  document.getElementById('mLight').innerHTML = `${(m.light_lux ?? '—')}<span class="u">lux</span>`;
  const life = p.life_expectancy;
  const lifeTxt = (life === undefined || life === null) ? '—' :
    (life >= 999 ? '>999' : life.toFixed?.(0) ?? life);
  document.getElementById('mLife').innerHTML = `${lifeTxt}<span class="u">年</span>`;

  const rp = document.getElementById('riskPill');
  rp.className = 'risk-pill ' + (s.level || 'SAFE');
  const lvlText = { SAFE: '✅ 安全', LOW: '⚠ 轻微风险', MEDIUM: '⚡ 中等风险', HIGH: '🔥 严重风险', CRITICAL: '💥 危急' };
  rp.textContent = `${lvlText[s.level] || s.level || '—'}  综合 ${(s.overall ?? 0).toFixed?.(2) ?? s.overall}`;

  renderKpiRow(s, p, m);
}

function renderKpiRow(scores, pred, metrics) {
  const container = document.getElementById('kpiRow');
  const cards = [
    { k: '酸化风险', v: (scores.acidosis ?? 0).toFixed(2), col: 'var(--acid)', sub: '阈值 ≥0.4需干预' },
    { k: '霉变风险', v: (scores.mold ?? 0).toFixed(2), col: 'var(--mold)', sub: pred.mold_species?.length ? `易感:${pred.mold_species.join('/')}` : '' },
    { k: '虫蛀风险', v: (scores.insect ?? 0).toFixed(2), col: 'var(--insect)', sub: '温湿适宜时上升' },
    { k: '30天pH预测', v: pred.ph_30d?.toFixed?.(2) ?? '—', col: 'var(--ph)', sub: `活化能:${pred.activation_energy_kj ?? '?'} kJ/mol` },
    { k: '90天pH预测', v: pred.ph_90d?.toFixed?.(2) ?? '—', col: 'var(--ph)', sub: 'Arrhenius动力学估计' },
    { k: '1年pH预测', v: pred.ph_365d !== undefined ? pred.ph_365d.toFixed(2) : '—', col: 'var(--ph)', sub: `纸型:${pred.paper_type || 'default'}` },
  ];
  container.innerHTML = cards.map(c => `
    <div class="kpi-card" style="border-left:3px solid ${c.col};">
      <div class="k">${c.k}</div>
      <div class="v" style="color:${c.col};">${c.v}</div>
      <div class="sub">${c.sub || ''}</div>
    </div>
  `).join('');
}

async function loadSlotTrends(slot) {
  const sid = slot.slot_id;
  const shid = AppState.currentShelfId;
  const [envTr, phTr] = await Promise.all([
    Api.get('/env/trend', { shelf_id: shid, slot_id: sid, hours: 24 * 90 }),
    Api.get('/ph/trend', { shelf_id: shid, slot_id: sid, days: 90 }),
  ]);
  const envData = envTr?.data || [];
  const phData = phTr?.data || [];

  TrendCharts.renderTrend('#chartTemp', envData, 'temp');
  TrendCharts.renderTrend('#chartHumi', envData, 'humi');
  TrendCharts.renderTrend('#chartMold', envData, 'mold');
  TrendCharts.renderTrend('#chartLight', envData, 'light');

  TrendCharts.renderMiniPh('#chartPhHistory', phData);

  const currentSlot = AppState.currentSlot;
  const m = currentSlot?.metrics || slot.metrics || {};
  const p = currentSlot?.prediction || slot.prediction || {};
  const phNow = m.ph ?? p.ph_30d ?? 6.8;
  const ph30 = p.ph_30d ?? (phNow - 0.08);
  const ph90 = p.ph_90d ?? (phNow - 0.25);
  const ph180 = p.ph_180d ?? (phNow - 0.5);
  const ph365 = p.ph_365d ?? (phNow - 1.0);
  TrendCharts.renderPhPrediction('#chartPhAge', phNow, ph30, ph90, ph180, ph365, phData);

  await loadHerbs(slot, currentSlot);
}

async function loadHerbs(slot, fullData) {
  const s = fullData?.scores || slot.scores || {};
  const m = fullData?.metrics || slot.metrics || {};
  const p = fullData?.prediction || slot.prediction || {};
  const dyn = fullData?.book_dynasty || slot.book_dynasty || '';
  const diseases = [];
  if (s.acidosis > 0.2) diseases.push('酸化');
  if (s.mold > 0.2) diseases.push('霉变');
  if (s.insect > 0.2) diseases.push('虫蛀');

  const req = {
    disease_types: diseases,
    mold_risk: s.mold ?? 0,
    insect_risk: s.insect ?? 0,
    ph_value: m.ph ?? p.ph_30d ?? null,
    top_k: 4,
    book_dynasty: dyn,
  };
  const r = await Api.post('/herbs/recommend', req);
  const data = r || buildMockHerbs(diseases, req);
  renderPrescription(data);
  renderHerbList(data);
}

function buildMockHerbs(diseases, req) {
  const all = [
    { id: 'herb_yuncao', name: '芸香草', latin: 'Cymbopogon distans', bencao_ref: '《本草纲目·草部》', dynasty: '明',
      efficacy: ['驱虫', '防霉', '抑菌'], target_diseases: ['虫蛀', '霉变'],
      usage: '阴干研末，撒于书叶之间；或缝制香囊置于书架四角。每册3-5g，每季度更换一次。',
      contraindications: '气虚血燥者慎用；远离火源，挥发油易燃。',
      source_books: ['本草纲目', '遵生八笺'], efficacy_score: 0.88, safety_score: 0.92 },
    { id: 'herb_huangbai', name: '黄柏', latin: 'Phellodendron chinense', bencao_ref: '《本草纲目·木部·黄柏》', dynasty: '明',
      efficacy: ['防虫', '抑菌', '脱酸辅助'], target_diseases: ['酸化', '虫蛀', '霉变'],
      usage: '黄柏煎汁（1:10）涂布纸张或书匣内壁；亦可浸制防蠹纸夹入书中。',
      contraindications: '直接接触明黄绫封面可能导致轻微褪色。',
      source_books: ['本草纲目', '齐民要术'], efficacy_score: 0.91, safety_score: 0.80 },
  ];
  return {
    detected_diseases: diseases,
    risk_profile: { ph_value: req.ph_value, mold_risk: req.mold_risk, insect_risk: req.insect_risk, acidification_level: '正常' },
    recommendations: all.map(h => ({ herb: h, match_score: 1.5, confidence: 0.75, match_reasons: diseases, historical_cases: [] })),
    treatment_protocol: {
      urgency: 'ROUTINE', steps: [
        { step: 1, action: '长期藏护', description: '每格放置芸草香囊，书架四角置苍术块。严格控制库温18-22℃、湿度45%-55%、光照<50lux。', herbs_used: ['芸香草', '苍术'], priority: 'MEDIUM' },
      ],
      expected_outcome: '可降低霉菌萌发率约85%、抑制虫害约90%、延缓pH下降约60%。',
      follow_up: '每季度一次微环境评估，每年一次深度检视。',
    },
  };
}

function renderPrescription(data) {
  const p = data.treatment_protocol || {};
  const urg = p.urgency || 'ROUTINE';
  const urgText = { CRITICAL: '🚨 危急处置', HIGH: '🟠 紧急处理', MEDIUM: '🟡 标准干预', ROUTINE: '🟢 常规养护' };
  const steps = (p.steps || []).map(s => `
    <div class="step ${s.priority}">
      <div class="sh">Step ${s.step} · ${s.action}<span class="prio">${s.priority === 'HIGH' ? '高优' : s.priority === 'MEDIUM' ? '中优' : '常规'}</span></div>
      <div class="sd">${s.description}</div>
      ${s.herbs_used?.length ? `<div class="hu">🌿 用药：${s.herbs_used.join(' · ')}</div>` : ''}
    </div>
  `).join('');
  document.getElementById('prescriptionCard').innerHTML = `
    <span class="urg ${urg}">${urgText[urg] || urg}</span>
    <div style="font-size:11px;color:var(--sub);margin-top:8px;">
      <b style="color:var(--text);">检测病害：</b>${(data.detected_diseases?.length ? data.detected_diseases.join('、') : '无明显病害') || '无明显病害'}
    </div>
    <h4>📋 防治方案（基于古籍记载 + 现代文物保护研究）</h4>
    ${steps}
    ${p.expected_outcome ? `<div class="outcome">🎯 预期效果：${p.expected_outcome}</div>` : ''}
    ${p.follow_up ? `<div class="follow">📝 随访计划：${p.follow_up}</div>` : ''}
  `;
}

function renderHerbList(data) {
  const list = document.getElementById('herbList');
  const recs = data.recommendations || [];
  if (!recs.length) { list.innerHTML = '<div class="empty" style="color:var(--sub);padding:30px;text-align:center;">暂无匹配药方</div>'; return; }
  list.innerHTML = recs.map(r => {
    const h = r.herb || {};
    const eff = (h.efficacy || []).map(e => `<span>${e}</span>`).join('');
    const conf = Math.round((r.confidence || 0) * 100);
    const reasons = (r.match_reasons || []).map(x => `#${x}`).join(' ');
    const hist = (r.historical_cases || []).map(c => `<div>📜 ${c}</div>`).join('');
    return `
      <div class="herb-card">
        <div class="herb-head">
          <div>
            <div class="herb-name">🌿 ${h.name || ''}</div>
            <div class="herb-latin">${h.latin || ''}</div>
            <div class="herb-ref">${h.bencao_ref || ''} · ${h.dynasty || ''}代</div>
          </div>
          <div class="herb-score">
            <div class="conf">匹配度 ${conf}%</div>
            <div style="font-size:9px;color:var(--sub);margin-top:3px;">
              效${Math.round((h.efficacy_score || 0) * 100)} · 安${Math.round((h.safety_score || 0) * 100)}
            </div>
          </div>
        </div>
        <div class="herb-efficacy">${eff}</div>
        <div class="herb-meta">
          <div class="blk"><div class="bk">来源医籍</div><div class="bv">${(h.source_books || []).join('、') || '—'}</div></div>
          <div class="blk"><div class="bk">主治病害</div><div class="bv">${(h.target_diseases || []).join('、') || '—'}</div></div>
        </div>
        <div class="herb-usage">💡 <b>古法使用</b>：${h.usage || ''}</div>
        ${h.contraindications ? `<div class="herb-contra">⚠ 注意：${h.contraindications}</div>` : ''}
        ${reasons ? `<div class="herb-match">🔗 匹配依据：${reasons}</div>` : ''}
        ${hist ? `<div class="herb-historical">${hist}</div>` : ''}
      </div>
    `;
  }).join('');
}

function initRenderer() {
  const canvas = document.getElementById('shelfCanvas');
  const r = new Shelf3DRenderer(canvas);
  AppState.renderer = r;
  r.on('slotClick', onSlotClick);
  r.on('zoom', z => { /* showToast(`缩放 ${(z * 100).toFixed(0)}%`, 1200); */ });
  document.getElementById('resetViewBtn').onclick = () => r.resetView();
  document.getElementById('zoomInBtn').onclick = () => r.zoomBy(1.15);
  document.getElementById('zoomOutBtn').onclick = () => r.zoomBy(1 / 1.15);
  document.querySelectorAll('.layer-toggles input').forEach(inp => {
    inp.onchange = () => {
      const layers = {};
      document.querySelectorAll('.layer-toggles input').forEach(i => layers[i.dataset.layer] = i.checked);
      r.setLayers(layers);
    };
  });
  window.addEventListener('resize', () => { r.resize(); r.requestRender(); });
}

function initTabs() {
  const tabs = document.querySelectorAll('#tabBar .tab');
  tabs.forEach(t => {
    t.onclick = () => {
      tabs.forEach(x => x.classList.remove('active'));
      t.classList.add('active');
      const key = t.dataset.tab;
      ['env', 'age', 'herb'].forEach(k => {
        document.getElementById(`tab-${k}`).classList.toggle('hidden', k !== key);
      });
      if (key === 'env' && AppState.currentSlot) {
        setTimeout(() => {
          const slot = AppState.currentSlot;
          loadSlotTrends(slot);
        }, 30);
      }
    };
  });
}

function initTopbar() {
  document.getElementById('refreshBtn').onclick = async () => {
    showToast('🔄 刷新中...', 900);
    await Promise.all([loadOverview(), loadAlerts()]);
    if (AppState.currentShelfId) await loadHeatmap(AppState.currentShelfId);
  };
  const autoBtn = document.getElementById('autoRefreshBtn');
  autoBtn.onclick = () => {
    AppState.autoRefresh = !AppState.autoRefresh;
    autoBtn.classList.toggle('active', AppState.autoRefresh);
    autoBtn.textContent = AppState.autoRefresh ? '⏱ 自动刷新' : '⏸ 已暂停';
  };
  setInterval(() => {
    if (!AppState.autoRefresh) return;
    Promise.all([loadOverview(), loadAlerts()]).then(() => {
      if (AppState.currentShelfId && Math.random() < 0.5) loadHeatmap(AppState.currentShelfId);
    });
  }, 30000);
}

async function boot() {
  initRenderer();
  initTabs();
  initTopbar();
  await loadShelves();
  await Promise.all([loadOverview(), loadAlerts()]);
  showToast('✅ 系统初始化完成，选择书架开始监测', 2200);
}

document.addEventListener('DOMContentLoaded', boot);
