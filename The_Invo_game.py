# app.py
import json
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Shalaby Inventory — Game Mode", layout="wide")

if "game_running" not in st.session_state:
    st.session_state.game_running = False
if "game_reset_token" not in st.session_state:
    st.session_state.game_reset_token = 0

SCENARIO_OPTIONS = ["Accurate forecast", "Biased forecast"]
SPEED_OPTIONS = ["minute", "second"]

st.markdown(
    """
    <style>
    .game-panel {
        background: linear-gradient(135deg, rgba(13,71,161,0.08), rgba(83,109,254,0.15));
        border: 1px solid rgba(13,71,161,0.25);
        border-radius: 18px;
        padding: 16px 22px 10px;
        margin-top: 6px;
        margin-bottom: 22px;
        box-shadow: 0 14px 32px rgba(13,71,161,0.14);
    }
    .game-panel h3 {
        font-family: 'Segoe UI', sans-serif;
        font-weight: 700;
        color: #0b4f8c;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .game-panel p {
        color: #2c405c;
        margin-top: 0;
        margin-bottom: 18px;
        font-size: 0.88rem;
    }
    .game-panel [data-testid="stColumn"] > div {
        background: rgba(255,255,255,0.82);
        border-radius: 14px;
        padding: 12px 14px 6px;
        border: 1px solid rgba(11,79,140,0.18);
        box-shadow: inset 0 0 0 1px rgba(255,255,255,0.35);
    }
    .game-panel [data-testid="stSelectbox"] label {
        font-weight: 600;
        color: #0b4f8c;
        letter-spacing: 0.06em;
        font-size: 0.74rem;
        text-transform: uppercase;
    }
    .game-panel [data-baseweb="select"] {
        border-radius: 10px;
        border: 1px solid rgba(11,79,140,0.28);
        background: rgba(247,249,255,0.95);
    }
    .game-panel [data-baseweb="select"]:hover {
        border: 1px solid rgba(41,121,255,0.55);
        box-shadow: 0 0 0 3px rgba(41,121,255,0.2);
    }
    .game-panel [data-baseweb="select"] input {
        font-weight: 600;
        color: #1a237e;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar controls (Python -> passed to embedded JS as initial params)
st.sidebar.header("إعدادات المحاكاة (Game Mode)")
lead_time = st.sidebar.slider("Lead Time (days)", 1.0, 14.0, 6.0, 0.5)
moq = st.sidebar.slider("MOQ (units)", 40, 400, 160, 10)
production_rate = st.sidebar.slider("Production Requirement (units/day)", 20, 360, 200, 5)
market_demand = st.sidebar.slider("Market Demand (units/day)", 20, 360, 180, 5)
safety_stock = st.sidebar.slider("Safety Stock (units)", 60, 360, 180, 10)
fg_safety_stock = st.sidebar.slider("FG Safety Stock (units)", 40, 400, 160, 10)
initial_fg_stock = st.sidebar.slider("Initial Finished Goods (units)", 40, 500, 200, 10)
factory_batch = st.sidebar.slider("Factory Batch (units)", 20, 120, 40, 5)

scenario_default = st.session_state.get("scenario", SCENARIO_OPTIONS[0])
if scenario_default not in SCENARIO_OPTIONS:
    scenario_default = SCENARIO_OPTIONS[0]
speed_default = st.session_state.get("speed_unit", SPEED_OPTIONS[0])
if speed_default not in SPEED_OPTIONS:
    speed_default = SPEED_OPTIONS[0]

with st.container():
    st.markdown(
        """
        <div class="game-panel">
            <h3>Simulation Console</h3>
            <p>🎛️ اضبط سيناريو التشغيل وسرعة اللعبة بينما تراقب الحركة حيّة.</p>
        """,
        unsafe_allow_html=True,
    )
    mode_col1, mode_col2 = st.columns([1, 1])
    with mode_col1:
        scenario_selection = st.selectbox(
            "Scenario",
            SCENARIO_OPTIONS,
            index=SCENARIO_OPTIONS.index(scenario_default),
        )
    with mode_col2:
        speed_selection = st.selectbox(
            "Sim Speed",
            SPEED_OPTIONS,
            index=SPEED_OPTIONS.index(speed_default),
        )
    st.markdown("</div>", unsafe_allow_html=True)

if "scenario" not in st.session_state or st.session_state.scenario != scenario_selection:
    st.session_state.scenario = scenario_selection

if "speed_unit" not in st.session_state or st.session_state.speed_unit != speed_selection:
    st.session_state.speed_unit = speed_selection

scenario = st.session_state.scenario
speed_unit = st.session_state.speed_unit

# Package parameters to pass into JS
params = {
    "lead_time": lead_time,
    "moq": moq,
    "production_rate": production_rate,
    "market_demand": market_demand,
    "safety_stock": safety_stock,
    "fg_safety_stock": fg_safety_stock,
    "initial_fg_stock": initial_fg_stock,
    "factory_batch": factory_batch,
    "scenario": scenario,
    "speed_unit": speed_unit,
    "is_running": bool(st.session_state.game_running),
    "reset_token": int(st.session_state.game_reset_token),
}

# The HTML + JS game. It's self-contained and uses the params object for initial settings.
params_json = json.dumps(params)
html_template = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { box-sizing:border-box; }
  body { margin:0; min-height:100vh; display:flex; justify-content:center; align-items:flex-start; background:radial-gradient(120% 140% at 50% -10%, #142c56 0%, #081223 58%, #030811 100%); font-family:'Rajdhani', 'Segoe UI', sans-serif; color:#e4ecff; padding:28px 12px; }
  .game-shell { width:min(920px, 100%); background:linear-gradient(150deg, rgba(12,32,62,0.95), rgba(19,46,92,0.78)); border:1px solid rgba(130,201,255,0.32); border-radius:26px; padding:24px 28px 26px; box-shadow:0 26px 70px rgba(2,12,28,0.65); position:relative; overflow:hidden; isolation:isolate; }
  .game-shell::before { content:""; position:absolute; inset:-120px -140px auto auto; width:320px; height:320px; background:radial-gradient(circle at center, rgba(123,201,255,0.42) 0%, rgba(123,201,255,0.08) 70%, transparent 100%); z-index:-1; filter:blur(2px); }
  #hud { display:flex; flex-direction:column; gap:16px; margin-bottom:18px; }
  .hud-header { display:flex; justify-content:space-between; align-items:center; gap:12px; padding-bottom:4px; border-bottom:1px solid rgba(123,201,255,0.18); }
  .hud-title { font-size:1.05rem; letter-spacing:0.18em; text-transform:uppercase; font-weight:700; color:#9fd2ff; text-shadow:0 0 18px rgba(144,202,249,0.45); }
  .hud-live-badge { padding:5px 14px; border-radius:999px; border:1px solid rgba(144,202,249,0.5); background:rgba(28,63,122,0.55); font-size:0.72rem; letter-spacing:0.24em; font-weight:600; color:#e3f2fd; box-shadow:0 0 14px rgba(79,195,247,0.45); }
  .hud-metrics { display:grid; gap:12px; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); }
  .metric-card { display:flex; align-items:center; gap:12px; padding:12px 16px; border-radius:16px; border:1px solid rgba(123,201,255,0.24); background:linear-gradient(140deg, rgba(23,54,108,0.78), rgba(26,62,120,0.58)); box-shadow:inset 0 0 0 1px rgba(174,221,255,0.12), 0 14px 24px rgba(4,12,26,0.45); transition:transform 0.2s ease, box-shadow 0.2s ease; position:relative; overflow:hidden; }
  .metric-card::after { content:""; position:absolute; inset:4px 18px auto auto; width:38px; height:38px; border-radius:50%; background:radial-gradient(circle at 30% 30%, rgba(255,255,255,0.55), rgba(79,195,247,0)); opacity:0.18; pointer-events:none; }
  .metric-card .icon { font-size:1.2rem; filter:drop-shadow(0 4px 8px rgba(79,195,247,0.35)); }
  .metric-card .metric-info { display:flex; flex-direction:row; align-items:center; gap:8px; line-height:1.15; }
  .metric-card .value { font-size:1.08rem; font-weight:700; color:#f7fbff; letter-spacing:0.01em; text-shadow:0 0 16px rgba(144,202,249,0.35); }
  .metric-card[data-level="good"] { border-color:rgba(129,199,132,0.45); background:linear-gradient(150deg, rgba(46,125,50,0.65), rgba(67,160,71,0.42)); box-shadow:0 18px 28px rgba(46,125,50,0.35); }
  .metric-card[data-level="warning"] { border-color:rgba(255,193,7,0.6); background:linear-gradient(150deg, rgba(255,179,0,0.68), rgba(255,213,79,0.38)); box-shadow:0 18px 32px rgba(255,179,0,0.32); }
  .metric-card[data-level="alert"] { border-color:rgba(229,57,53,0.55); background:linear-gradient(150deg, rgba(211,47,47,0.72), rgba(239,83,80,0.42)); box-shadow:0 20px 36px rgba(198,55,52,0.42); }
  .metric-card.alerts-card { grid-column:1 / -1; align-items:flex-start; min-height:76px; background:linear-gradient(145deg, rgba(26,62,120,0.92), rgba(13,36,76,0.78)); border-color:rgba(123,201,255,0.28); box-shadow:0 12px 28px rgba(6,16,34,0.52); }
  .metric-card.alerts-card .value { font-size:0.98rem; white-space:pre-line; opacity:0.92; }
  .canvas-wrap { position:relative; border-radius:22px; padding:18px; background:linear-gradient(150deg, rgba(10,26,52,0.65), rgba(7,18,36,0.52)); border:1px solid rgba(123,201,255,0.18); box-shadow:inset 0 0 0 1px rgba(144,202,249,0.12), 0 26px 46px rgba(2,10,24,0.65); }
  .canvas-wrap::before { content:""; position:absolute; inset:auto auto -60px -60px; width:320px; height:320px; background:radial-gradient(circle at center, rgba(41,121,255,0.2), transparent 70%); filter:blur(6px); z-index:-1; }
  .canvas-controls { position:absolute; top:18px; right:22px; display:flex; gap:10px; z-index:6; }
  .game-button { appearance:none; border:none; border-radius:999px; padding:9px 20px; font-family:'Rajdhani', 'Segoe UI', sans-serif; font-weight:700; letter-spacing:0.12em; text-transform:uppercase; font-size:0.7rem; cursor:pointer; color:#e3f2fd; background:rgba(12,32,62,0.78); border:1px solid rgba(123,201,255,0.4); box-shadow:0 16px 28px rgba(5,16,34,0.45); transition:transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease, border-color 0.18s ease; }
  .game-button:hover { transform:translateY(-2px); box-shadow:0 20px 32px rgba(5,16,34,0.55); border-color:rgba(144,202,249,0.6); }
  .game-button.primary { background:linear-gradient(135deg, rgba(0,172,193,0.85), rgba(0,151,167,0.7)); border-color:rgba(79,195,247,0.65); }
  .game-button.primary[data-state="pause"] { background:linear-gradient(135deg, rgba(211,47,47,0.85), rgba(229,57,53,0.68)); border-color:rgba(255,138,128,0.7); }
  .game-button:focus-visible { outline:2px solid rgba(144,202,249,0.8); outline-offset:2px; }
  canvas { width:100%; height:auto; display:block; background:linear-gradient(160deg, #051024, #0b1c36); border-radius:18px; box-shadow:inset 0 0 24px rgba(2,12,28,0.55); }
</style>

</head>
<body>
<div class="game-shell">
  <div id="hud">
    <div class="hud-header">
      <span class="hud-title">Operations HUD</span>
      <span class="hud-live-badge">LIVE</span>
    </div>
    <div class="hud-metrics">
      <div class="metric-card" id="metric-score" data-level="good">
        <span class="icon">🏆</span>
        <div class="metric-info">
          <span class="value" id="score">Score: 0</span>
        </div>
      </div>
      <div class="metric-card" id="metric-factory" data-level="good">
        <span class="icon">🏭</span>
        <div class="metric-info">
          <span class="value" id="factory">Factory Raw: 240</span>
        </div>
      </div>
      <div class="metric-card" id="metric-fg" data-level="good">
        <span class="icon">📦</span>
        <div class="metric-info">
          <span class="value" id="finished_goods">Finished Goods: __FG_INIT__</span>
        </div>
      </div>
      <div class="metric-card" id="metric-warehouse" data-level="good">
        <span class="icon">🏬</span>
        <div class="metric-info">
          <span class="value" id="warehouse">Warehouse: 520</span>
        </div>
      </div>
      <div class="metric-card" id="metric-backlog" data-level="good">
        <span class="icon">📉</span>
        <div class="metric-info">
          <span class="value" id="backlog">Backlog: 0</span>
        </div>
      </div>
    </div>
    <div class="metric-card alerts-card" id="metric-alerts" data-level="good">
      <span class="icon">⚠️</span>
      <div class="metric-info">
        <span class="value" id="alerts">Alerts: All systems nominal.</span>
      </div>
    </div>
  </div>

  <div class="canvas-wrap">
    <div class="canvas-controls">
      <button class="game-button primary" id="control-start" data-state="start">▶ Start</button>
      <button class="game-button" id="control-reset">🔄 Reset</button>
    </div>
    <canvas id="game" width="980" height="520"></canvas>
  </div>
</div>

<script>

// --- params from Streamlit ---
const params = __PARAMS__;
// --- end params ---

// Convert flags from Streamlit session state
let started = Boolean(params.is_running);

// Simulation constants
const SIM_MINUTES_PER_DAY = 1.0; // 1 simulated day per minute baseline in original
const TRUCK_LOADING_PORTION = 0.25;

const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');
const startButton = document.getElementById('control-start');
const resetButton = document.getElementById('control-reset');

function updateControlButtons(){
  if(startButton){
    if(started){
      startButton.textContent = '⏸ Pause';
      startButton.setAttribute('data-state', 'pause');
    } else {
      startButton.textContent = '▶ Start';
      startButton.setAttribute('data-state', 'start');
    }
  }
}

if(startButton){
  startButton.addEventListener('click', () => {
    started = !started;
    updateControlButtons();
  });
}

if(resetButton){
  resetButton.addEventListener('click', () => {
    started = false;
    state = createInitialState();
    syncParamDrivenState();
    persistState();
    draw();
    updateControlButtons();
  });
}

updateControlButtons();

function clamp(v,a,b){ return Math.max(a, Math.min(b, v)); }

const numberFormatter = new Intl.NumberFormat('en-US');

function scoreLevel(score){
  if(score >= 0) return 'good';
  if(score >= -500) return 'warning';
  return 'alert';
}

function inventoryLevel(stock, safety=null, high=null){
  if(stock <= 0) return 'alert';
  if(safety != null){
    if(stock <= Math.max(5, safety * 0.25)) return 'alert';
    if(stock <= safety) return 'warning';
  }
  if(high != null && stock >= high) return 'warning';
  return 'good';
}

function backlogLevel(backlog){
  if(backlog <= 0) return 'good';
  const warningThreshold = Math.max(40, (params.market_demand || 0) * 1.5);
  const alertThreshold = Math.max(80, (params.market_demand || 0) * 3.0);
  if(backlog >= alertThreshold) return 'alert';
  if(backlog >= warningThreshold) return 'warning';
  return 'warning';
}

function setMetric(cardId, valueId, label, value, level='good', unitSuffix=''){
  const card = document.getElementById(cardId);
  if(card) card.setAttribute('data-level', level);
  const el = document.getElementById(valueId);
  if(!el) return;
  let text;
  if(typeof value === 'number' && isFinite(value)){
    const rounded = Math.round(value);
    const formatted = numberFormatter.format(rounded);
    text = `${label}: ${formatted}${unitSuffix}`;
  } else {
    const hasValue = value !== undefined && value !== null && String(value).length > 0;
    const body = hasValue ? String(value) : '0';
    text = `${label}: ${body}`;
  }
  el.textContent = text;
}

const STATE_WRAPPER_KEY = 'shalabyInventoryGame';

function createInitialState(){
  return {
    factory_stock: 240.0,
    warehouse_stock: 520.0,
    safety_stock: params.safety_stock,
    fg_safety_stock: params.fg_safety_stock,
    high_stock_threshold: 800.0,
    fg_high_stock_threshold: 600.0,
    worker_capacity: Math.max(1, params.factory_batch),
    worker_progress: 0.0,
    worker_direction: 1,
    worker_load: 0.0,
    finished_goods_stock: Math.max(0, params.initial_fg_stock || 0),
    backlog: 0.0,
    truck_en_route: false,
    truck_progress: 0.0,
    truck_delivery: 0.0,
    truck_wait_timer: 0.0,
    truck_travel_minutes_total: 0.0,
    truck_travel_minutes_remaining: 0.0,
    production_shutdown: false,
    score: 0,
    time_acc: 0,
  };
}

function loadState(){
  try {
    if(!window.name) return null;
    const wrapper = JSON.parse(window.name);
    if(!wrapper || wrapper.key !== STATE_WRAPPER_KEY) return null;
    if(wrapper.reset_token !== params.reset_token) return null;
    if(!wrapper.state) return null;
    return { ...createInitialState(), ...wrapper.state };
  } catch (err) {
    console.warn('Unable to load saved state', err);
    return null;
  }
}

let state = loadState() || createInitialState();

function persistState(){
  try {
    const wrapper = {
      key: STATE_WRAPPER_KEY,
      reset_token: params.reset_token,
      state: state,
    };
    window.name = JSON.stringify(wrapper);
  } catch (err) {
    console.warn('Unable to persist state', err);
  }
}

function syncParamDrivenState(){
  state.safety_stock = params.safety_stock;
  state.fg_safety_stock = params.fg_safety_stock;
  state.worker_capacity = Math.max(1, params.factory_batch);
  state.fg_high_stock_threshold = Math.max(
    state.fg_safety_stock * 2.0,
    (params.initial_fg_stock || 0) + Math.max(0, params.market_demand) * 2.0
  );
}

// State (client-side)

// Time scaling
let base_interval_ms = 120;
let time_factor = (params.speed_unit === "second") ? 60.0 : 1.0;
let minutes_per_step = (base_interval_ms / 60000.0) * time_factor;

// Utility calculations (mirror python logic)
function production_requirement_per_minute(){
  let daily = Math.max(0, params.production_rate);
  let per_min = daily / Math.max(1.0, SIM_MINUTES_PER_DAY);
  if (params.scenario === "Biased forecast") per_min *= 1.2;
  return per_min;
}

function market_demand_per_minute(){
  let daily = Math.max(0, params.market_demand);
  let per_min = daily / Math.max(1.0, SIM_MINUTES_PER_DAY);
  if (params.scenario === "Biased forecast") per_min *= 1.3;
  return per_min;
}

function compute_reorder_point(){
  const lead_days = Math.max(0.0, params.lead_time);
  const per_min = production_requirement_per_minute();
  const lead_minutes = lead_days * SIM_MINUTES_PER_DAY;
  const lead_demand = per_min * lead_minutes;
  return Math.max(0.0, state.safety_stock + lead_demand);
}

// Simulation steps
function apply_production(){
  if(state.production_shutdown) return;
  const per_min = production_requirement_per_minute();
  const per_step = per_min * minutes_per_step;
  if(per_step <= 0) return;
  const available_raw = Math.max(0, state.factory_stock);
  const actual = Math.min(per_step, available_raw);
  if(actual <= 0) return;
  state.factory_stock = Math.max(0, state.factory_stock - actual);
  state.finished_goods_stock += actual;
  if(state.backlog > 0 && state.finished_goods_stock > 0){
    const fulfill = Math.min(state.finished_goods_stock, state.backlog);
    state.finished_goods_stock -= fulfill;
    state.backlog -= fulfill;
  }
}

function apply_market_demand(){
  const prevBacklog = state.backlog;
  const per_min = market_demand_per_minute();
  const per_step = per_min * minutes_per_step;
  if(per_step <= 0) return;
  if(state.finished_goods_stock >= per_step){
    state.finished_goods_stock -= per_step;
  } else {
    const shortfall = per_step - state.finished_goods_stock;
    state.finished_goods_stock = 0.0;
    state.backlog += shortfall;
    if(audioEnabled && state.backlog > prevBacklog){
      playEventSound('backlog');
    }
  }
}

function compute_worker_speed(){
  const per_min = production_requirement_per_minute();
  const capacity = Math.max(0, state.worker_capacity);
  if(capacity <= 0) return 0;

  let half_trip_minutes = null;
  if(per_min > 0){
    const trips_per_minute = per_min / capacity;
    if(trips_per_minute > 0){
      const cycle_minutes = 1.0 / trips_per_minute;
      half_trip_minutes = Math.max(minutes_per_step, cycle_minutes / 2.0);
    }
  } else {
    if(state.worker_direction === -1 && state.worker_progress > 0) half_trip_minutes = 0.5;
    else if(state.worker_direction === 1 && state.worker_progress < 1) half_trip_minutes = 0.5;
  }

  if(half_trip_minutes === null || !isFinite(half_trip_minutes) || half_trip_minutes <= 0) return 0;
  const progress = minutes_per_step / half_trip_minutes;
  return clamp(progress, 0, 1);
}

function move_worker(){
  const speed = compute_worker_speed();
  if(state.worker_direction===1){
    if(state.worker_progress < 1.0) state.worker_progress = Math.min(1.0, state.worker_progress + speed);

    if(Math.abs(state.worker_progress-1.0) < 1e-3){
      if(state.warehouse_stock>0){
        const take = Math.min(state.worker_capacity, state.warehouse_stock);
        state.worker_load = take;
        state.warehouse_stock -= take;
        state.worker_direction = -1;
      }else{
        state.worker_progress = 1.0;
      }
    }
  } else {
    if(state.worker_progress > 0.0) state.worker_progress = Math.max(0.0, state.worker_progress - speed);
    if(Math.abs(state.worker_progress-0.0) < 1e-3){
      if(state.worker_load>0){
        state.factory_stock += state.worker_load;
        state.worker_load = 0.0;
      }
      state.worker_direction = 1;
    }
  }
}

function handle_replenishment(){
  if(state.truck_en_route || state.production_shutdown) return;
  const reorder_point = compute_reorder_point();
  if(state.warehouse_stock <= reorder_point){
    state.truck_en_route = true;
    state.truck_progress = 0.0;
    const lead_time_days = Math.max(0.1, params.lead_time);
    const lead_time_minutes = lead_time_days * SIM_MINUTES_PER_DAY;
    const loading_minutes = lead_time_minutes * TRUCK_LOADING_PORTION;
    const travel_minutes = Math.max(minutes_per_step, lead_time_minutes - loading_minutes);
    state.truck_wait_timer = loading_minutes;
    state.truck_travel_minutes_total = travel_minutes;
    state.truck_travel_minutes_remaining = travel_minutes;
    state.truck_delivery = Math.max(20.0, params.moq);
  }
}

function move_truck(){
  if(!state.truck_en_route) return;
  if(state.truck_wait_timer > 0){
    state.truck_wait_timer = Math.max(0.0, state.truck_wait_timer - minutes_per_step);
    if(state.truck_wait_timer > 0) return;
  }
  if(state.truck_travel_minutes_total <= 0){
    complete_truck();
    return;
  }
  state.truck_travel_minutes_remaining = Math.max(0.0, state.truck_travel_minutes_remaining - minutes_per_step);
  const prog = minutes_per_step / Math.max(1e-6, state.truck_travel_minutes_total);
  state.truck_progress = Math.min(1.0, state.truck_progress + prog);
  if(state.truck_travel_minutes_remaining <= 0.0 || Math.abs(state.truck_progress-1.0)<1e-3){
    complete_truck();
  }
}

function complete_truck(){
  if(state.truck_delivery > 0) state.warehouse_stock += state.truck_delivery;
  state.truck_en_route = false; state.truck_progress = 0.0; state.truck_delivery = 0.0;
  state.truck_wait_timer = 0.0; state.truck_travel_minutes_total = 0.0; state.truck_travel_minutes_remaining = 0.0;
  playEventSound('delivery');
}

function apply_scenario_effects(){
  if(params.scenario === "Biased forecast"){
    if(state.factory_stock < Math.max(40.0, state.safety_stock*0.5)) state.production_shutdown = true;
    if(state.production_shutdown && state.factory_stock > state.safety_stock + 60) state.production_shutdown = false;
  } else {
    state.production_shutdown = false;
  }
}

function update_score(){
  let step = 0;
  if(!state.production_shutdown) step += 1;
  if(state.factory_stock <= 0) step -=1;
  else if(state.factory_stock < state.safety_stock) step -=1;
  if(state.warehouse_stock <= 0) step -=1;
  else if(state.warehouse_stock < state.safety_stock) step -=1;
  if(state.warehouse_stock >= compute_reorder_point()) step +=1;
  state.score += step;
}

// Alerts text
function generate_alerts(){
  let alerts = [];
  if(state.factory_stock < state.safety_stock) alerts.push("Factory below safety!");
  if(state.warehouse_stock < state.safety_stock) alerts.push("Warehouse critically low!");
  if(state.warehouse_stock > state.high_stock_threshold) alerts.push("Warehouse too high!");
  if(state.production_shutdown) alerts.push("Production shutdown!");
  if(params.scenario === "Biased forecast" && !state.production_shutdown && state.factory_stock < state.safety_stock)
    alerts.push("Biased forecast — factory dropping!");
  return alerts.join("\\n");
}

// --- Drawing (gamey visuals) ---
function draw(){
  ctx.clearRect(0,0,canvas.width,canvas.height);
  // background gradient
  const g = ctx.createLinearGradient(0,0,0,canvas.height);
  g.addColorStop(0,'#f7fbff'); g.addColorStop(1,'#eaf4ff');
  ctx.fillStyle = g; ctx.fillRect(0,0,canvas.width,canvas.height);

  // Title
  ctx.fillStyle = "#0b4f8c"; ctx.font = "28px Montserrat, sans-serif";
  ctx.fillText("Shalaby — Inventory Playground (Game Mode)", 18, 36);
  ctx.font = "12px Segoe UI";
  ctx.fillStyle = "#4b5968";
  ctx.fillText("Move resources, watch the truck and keep stock healthy!", 18, 56);

  // facility rectangles
  const factory = {x:80,y:180,w:140,h:130, color:'#c8e6c9', stroke:'#81c784', label:'Factory'};
  const warehouse = {x:340,y:150,w:160,h:170, color:'#ffe0b2', stroke:'#ffb74d', label:'Warehouse'};
  const supplier = {x:660,y:180,w:180,h:130, color:'#bbdefb', stroke:'#64b5f6', label:'Supplier'};
  const fg_coords = {x:80,y:340,w:140,h:110};

  [factory, warehouse, supplier].forEach(f =>{
    ctx.fillStyle = f.color; ctx.strokeStyle = f.stroke; ctx.lineWidth = 2;
    roundRect(ctx, f.x, f.y, f.w, f.h, 8, true, true);
    ctx.fillStyle = '#333'; ctx.font='bold 12px Segoe UI';
    ctx.fillText(f.label, f.x + f.w/2 - ctx.measureText(f.label).width/2, f.y + f.h + 18);
  });

  // draw dotted paths
  ctx.strokeStyle = '#b0bec5'; ctx.setLineDash([8,6]); ctx.lineWidth = 6;
  ctx.beginPath(); ctx.moveTo(factory.x+factory.w, factory.y+70); ctx.lineTo(warehouse.x, warehouse.y+70); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(warehouse.x+warehouse.w, warehouse.y+40); ctx.lineTo(supplier.x, supplier.y+40); ctx.stroke();
  ctx.setLineDash([]);

  // draw stock blocks in each facility
  ctx.fillStyle = '#e3f2fd'; ctx.strokeStyle = "#42a5f5";
  roundRect(ctx, fg_coords.x, fg_coords.y, fg_coords.w, fg_coords.h, 10, true, true);
  draw_stock_blocks(factory, state.factory_stock, state.high_stock_threshold, '#66bb6a');
  draw_stock_blocks(warehouse, state.warehouse_stock, state.high_stock_threshold, '#ffa726', state.safety_stock, compute_reorder_point());
  draw_stock_blocks(fg_coords, state.finished_goods_stock, state.fg_high_stock_threshold, '#42a5f5', state.fg_safety_stock);
  draw_flag(fg_coords, determine_flag(state.finished_goods_stock, state.fg_safety_stock, null, state.fg_high_stock_threshold), 'center');
  ctx.fillStyle = '#1e88e5'; ctx.font = 'bold 13px Segoe UI';
  ctx.fillText('FG: ' + Math.round(state.finished_goods_stock) + ' u', fg_coords.x + 16, fg_coords.y - 10);

  // flags
  draw_flag(factory, determine_flag(state.factory_stock, state.safety_stock, null, null), 'left');
  draw_flag(warehouse, determine_flag(state.warehouse_stock, state.safety_stock, compute_reorder_point(), state.high_stock_threshold), 'right');

  // numeric labels
  ctx.fillStyle = '#2e7d32'; ctx.font = 'bold 13px Segoe UI';
  ctx.fillText(Math.round(state.factory_stock) + ' u', factory.x + factory.w/2 - 30, factory.y - 12);
  ctx.fillStyle = '#ef6c00';
  ctx.fillText(Math.round(state.warehouse_stock) + ' u', warehouse.x + warehouse.w/2 - 40, warehouse.y - 12);

  // worker (between factory and warehouse)
  const factoryCenter = {x: factory.x + factory.w/2, y: factory.y + factory.h/2};
  const warehouseCenter = {x: warehouse.x + warehouse.w/2, y: warehouse.y + warehouse.h/2};
  const workerX = factoryCenter.x + (warehouseCenter.x - factoryCenter.x) * state.worker_progress;
  const workerY = factoryCenter.y + 40;
  draw_worker(workerX, workerY, state.worker_load);

  // truck (between supplier and warehouse)
  let truckProgress = state.truck_en_route && state.truck_wait_timer <= 0 ? state.truck_progress : 0.0;
  const supplierCenter = {x: supplier.x + supplier.w/2, y: supplier.y + supplier.h/2};
  const truckX = supplierCenter.x + (warehouseCenter.x - supplierCenter.x) * truckProgress;
  const truckY = supplierCenter.y - 10;
  draw_truck(truckX, truckY, state.truck_en_route, state.truck_wait_timer, state.truck_delivery, state.truck_travel_minutes_remaining);

  // HUD update
  setMetric('metric-score', 'score', 'Score', state.score, scoreLevel(state.score));
  setMetric(
    'metric-factory',
    'factory',
    'Factory Raw',
    state.factory_stock,
    inventoryLevel(state.factory_stock, state.safety_stock, null),
    ' u'
  );
  setMetric(
    'metric-fg',
    'finished_goods',
    'Finished Goods',
    state.finished_goods_stock,
    inventoryLevel(state.finished_goods_stock, state.fg_safety_stock, state.fg_high_stock_threshold),
    ' u'
  );
  setMetric(
    'metric-warehouse',
    'warehouse',
    'Warehouse',
    state.warehouse_stock,
    inventoryLevel(state.warehouse_stock, state.safety_stock, state.high_stock_threshold),
    ' u'
  );
  setMetric(
    'metric-backlog',
    'backlog',
    'Backlog',
    state.backlog,
    backlogLevel(state.backlog),
    ' u'
  );

  const alertsText = generate_alerts();
  const alertsLevel = alertsText && alertsText.trim().length > 0 ? 'alert' : 'good';
  setMetric(
    'metric-alerts',
    'alerts',
    'Alerts',
    alertsText ? alertsText : 'All systems nominal.',
    alertsLevel
  );
  if(audioEnabled){
    const isAlerting = alertsLevel === 'alert';
    if(isAlerting && !lastAlertsNonNominal){
      playEventSound('alert');
    }
    lastAlertsNonNominal = isAlerting;
  }
}

// small helpers
function roundRect(ctx, x, y, w, h, r, fill, stroke){
  if (typeof r === 'number') r = {tl:r,tr:r,br:r,bl:r};
  ctx.beginPath();
  ctx.moveTo(x + r.tl, y);
  ctx.lineTo(x + w - r.tr, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r.tr);
  ctx.lineTo(x + w, y + h - r.br);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r.br, y + h);
  ctx.lineTo(x + r.bl, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r.bl);
  ctx.lineTo(x, y + r.tl);
  ctx.quadraticCurveTo(x, y, x + r.tl, y);
  ctx.closePath();
  if(fill) ctx.fill();
  if(stroke) ctx.stroke();
}

function draw_stock_blocks(coords, stock, max_stock, fill, safety_stock=null, reorder_point=null){
  const x0 = coords.x, y0 = coords.y, x1 = coords.x + coords.w, y1 = coords.y + coords.h;
  const width = coords.w, height = coords.h;
  const capacity = Math.max(1, max_stock);
  const units_per_block = capacity / 30;
  const block_count = Math.min(30, Math.floor(stock / units_per_block));
  let safety_blocks = 0, reorder_blocks = 0;
  if(safety_stock!=null) safety_blocks = Math.min(30, Math.max(0, Math.ceil(safety_stock / units_per_block)));
  if(reorder_point!=null) reorder_blocks = Math.min(30, Math.max(0, Math.ceil(reorder_point / units_per_block)));
  const cols = 5;
  const block_size = Math.min(26, Math.floor(width/cols - 4));
  for(let idx=0; idx<block_count; idx++){
    const row = Math.floor(idx / cols);
    const col = idx % cols;
    const bx0 = x0 + 12 + col * (block_size + 4);
    const by1 = y1 - 12 - row * (block_size + 4);
    const by0 = by1 - block_size;
    if(by0 < y0 + 8) break;
    let block_color = fill;
    if(safety_stock!=null && idx < safety_blocks) block_color = "#e53935";
    else if(reorder_point!=null && idx < reorder_blocks) block_color = "#43a047";
    ctx.fillStyle = block_color; ctx.strokeStyle = "#ffffff";
    ctx.fillRect(bx0, by0, block_size, block_size);
    ctx.strokeRect(bx0, by0, block_size, block_size);
  }
}

function determine_flag(stock, safety_stock=null, reorder_point=null, high_threshold=null){
  if(safety_stock!=null && stock <= safety_stock) return "red";
  if(high_threshold!=null && stock >= high_threshold) return "yellow";
  if(reorder_point!=null && stock <= reorder_point) return "yellow";
  return "green";
}

function draw_flag(coords, color, align='center'){
  if(!color) return;
  const color_map = { red:'#d32f2f', yellow:'#fbc02d', green:'#388e3c' };
  const fill = color_map[color];
  let pole_x;
  if(align==='left') pole_x = coords.x - 18;
  else if(align==='right') pole_x = coords.x + coords.w + 18;
  else pole_x = coords.x + coords.w/2;
  const pole_base_y = coords.y - 4;
  const pole_top_y = pole_base_y - 36;
  ctx.beginPath(); ctx.moveTo(pole_x, pole_base_y); ctx.lineTo(pole_x, pole_top_y); ctx.strokeStyle = '#546e7a'; ctx.lineWidth = 3; ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(pole_x, pole_top_y);
  ctx.lineTo(pole_x + 22, pole_top_y + 8);
  ctx.lineTo(pole_x, pole_top_y + 16);
  ctx.closePath();
  ctx.fillStyle = fill; ctx.fill();
  ctx.strokeStyle = '#eeeeee'; ctx.stroke();
}

function draw_worker(x,y,load){
  const radius = 14;
  const body_color = load>0 ? '#ff7043' : '#8d6e63';
  ctx.beginPath(); ctx.fillStyle = body_color; ctx.strokeStyle = 'white'; ctx.lineWidth = 2;
  ctx.arc(x, y, radius, 0, Math.PI*2); ctx.fill(); ctx.stroke();
  ctx.fillStyle = '#455a64'; ctx.fillRect(x-18, y+radius, 36, 10);
  if(load>0){
    ctx.fillStyle = '#37474f'; ctx.font='bold 11px Segoe UI'; ctx.fillText(Math.round(load), x-8, y-20);
  }
}

function draw_truck(x,y,enroute,wait,delivery,remaining){
  ctx.fillStyle = '#1976d2'; ctx.fillRect(x-40, y-18, 76, 36);
  ctx.fillStyle = '#42a5f5'; ctx.fillRect(x-30, y-28, 60, 20);
  ctx.beginPath(); ctx.fillStyle = '#37474f'; ctx.ellipse(x-20, y+30, 12, 12, 0, 0, Math.PI*2); ctx.fill();
  ctx.beginPath(); ctx.ellipse(x+18, y+30, 12, 12, 0, 0, Math.PI*2); ctx.fill();
  if(enroute){
    let status;
    if(wait > 0) status = `Loading... ${wait.toFixed(1)} d`;
    else if(delivery) {
      let rem = Math.max(0, remaining);
      if(rem >= 1.0) status = `Delivering ${Math.round(delivery)} u (${rem.toFixed(1)} d)`;
      else if(rem > 0) status = `Delivering ${Math.round(delivery)} u (${Math.round(rem*24)} h)`;
      else status = `Delivering ${Math.round(delivery)} u`;
    } else status = 'Returning';
    ctx.fillStyle = '#1565c0'; ctx.font = '11px Segoe UI'; ctx.fillText(status, x-40, y-36);
  }
}

// --- Main tick ---
function tick(){
  syncParamDrivenState();
  apply_production();
  apply_market_demand();
  move_worker();
  handle_replenishment();
  move_truck();
  apply_scenario_effects();
  update_score();
  draw();
}

// Simple external signals handling (Streamlit buttons cause rerun which re-embeds params)
function handleExternalActions(){
  syncParamDrivenState();
}

// update minutes_per_step whenever speed_unit changes
minutes_per_step = (base_interval_ms / 60000.0) * (params.speed_unit === 'second' ? 60.0 : 1.0);

// animation loop
let intervalId = null;
function startLoop(){
  if(intervalId) clearInterval(intervalId);
  intervalId = setInterval(()=> {
    handleExternalActions();
    if(started){
      tick();
    } else {
      draw();
    }
    persistState();
  }, base_interval_ms);
}
startLoop();
syncParamDrivenState();
draw();
persistState();

</script>
</body>
</html>
"""

# embed HTML
components.html(html_template.replace("__PARAMS__", params_json).replace("__FG_INIT__", str(int(initial_fg_stock))), height=780, scrolling=False)