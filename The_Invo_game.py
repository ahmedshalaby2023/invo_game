# app.py
import json
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Shalaby Inventory — Game Mode", layout="wide")
st.title("🎮 Shalaby Inventory — لعبة محاكاة")

# Sidebar controls (Python -> passed to embedded JS as initial params)
st.sidebar.header("إعدادات المحاكاة (Game Mode)")
lead_time = st.sidebar.slider("Lead Time (days)", 1.0, 14.0, 6.0, 0.5)
moq = st.sidebar.slider("MOQ (units)", 40, 400, 160, 10)
consumption_rate = st.sidebar.slider("Consumption (units/day)", 20, 320, 180, 5)
safety_stock = st.sidebar.slider("Safety Stock (units)", 60, 360, 180, 10)
factory_batch = st.sidebar.slider("Factory Batch (units)", 20, 120, 40, 5)
scenario = st.sidebar.selectbox("Scenario", ["Accurate forecast", "Biased forecast"])
speed_unit = st.sidebar.selectbox("Sim Speed", ["minute", "second"])

col1, col2, col3 = st.columns([1,1,1])
with col1:
    start_pause = st.button("▶ Start / Pause")
with col2:
    reset = st.button("🔄 Reset")
with col3:
    # show simple readouts (these values are initial; the canvas runs client-side animation)
    st.write("**Initial values**")
    st.write(f"Factory: 240")
    st.write(f"Warehouse: 520")
    st.write(f"Reorder pt ≈ {int(safety_stock + (consumption_rate/1.0)*(lead_time))}")

# Package parameters to pass into JS
params = {
    "lead_time": lead_time,
    "moq": moq,
    "consumption_rate": consumption_rate,
    "safety_stock": safety_stock,
    "factory_batch": factory_batch,
    "scenario": scenario,
    "speed_unit": speed_unit,
    "action_start_pause": int(start_pause),
    "action_reset": int(reset),
}

# The HTML + JS game. It's self-contained and uses the params object for initial settings.
params_json = json.dumps(params)
html_template = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ margin:0; background:#e8f0ff; font-family:Segoe UI, sans-serif; }}
  #hud {{ position: absolute; left: 16px; top: 12px; z-index:10; }}
  .badge {{ background: white; padding:8px 10px; border-radius:8px; box-shadow:0 2px 6px rgba(0,0,0,0.08); margin-right:8px; display:inline-block; }}
  canvas {{ display:block; margin: 0 auto; background: linear-gradient(#f7f9ff,#eaf2ff); border-radius:8px; box-shadow: 0 6px 20px rgba(30,60,120,0.07); }}
  .controls {{ position:absolute; right:18px; top:12px; }}
  .btn {{ background:#1976d2; color:white; padding:8px 12px; border-radius:6px; cursor:pointer; margin-left:6px; }}
  .btn.secondary {{ background:#ef6c00; }}
</style>
</head>
<body>
<div id="hud">
  <span class="badge" id="score">Score: 0</span>
  <span class="badge" id="factory">Factory: 240</span>
  <span class="badge" id="warehouse">Warehouse: 520</span>
  <span class="badge" id="alerts"></span>
</div>

<canvas id="game" width="980" height="520"></canvas>

<script>
// --- params from Streamlit ---
const params = __PARAMS__;
// --- end params ---

// Convert numeric flags possibly sent as 0/1
let started = false;
let lastResetSignal = params.action_reset || 0;
let lastStartPauseSignal = params.action_start_pause || 0;

// Simulation constants
const SIM_MINUTES_PER_DAY = 1.0; // 1 simulated day per minute baseline in original
const TRUCK_LOADING_PORTION = 0.25;

const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');

function clamp(v,a,b){ return Math.max(a, Math.min(b, v)); }

// State (client-side)
let state = {
  factory_stock: 240.0,
  warehouse_stock: 520.0,
  safety_stock: params.safety_stock,
  high_stock_threshold: 800.0,
  worker_capacity: Math.max(1, params.factory_batch),
  worker_progress: 0.0,
  worker_direction: 1,
  worker_load: 0.0,
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

// Time scaling
let base_interval_ms = 120;
let time_factor = (params.speed_unit === "second") ? 60.0 : 1.0;
let minutes_per_step = (base_interval_ms / 60000.0) * time_factor;

// Utility calculations (mirror python logic)
function consumption_per_minute(){
  let daily = Math.max(0, params.consumption_rate);
  let per_min = daily / Math.max(1.0, SIM_MINUTES_PER_DAY);
  if (params.scenario === "Biased forecast") per_min *= 1.6;
  return per_min;
}

function compute_reorder_point(){
  const lead_days = Math.max(0.0, params.lead_time);
  const per_min = consumption_per_minute();
  const lead_minutes = lead_days * SIM_MINUTES_PER_DAY;
  const lead_demand = per_min * lead_minutes;
  return Math.max(0.0, state.safety_stock + lead_demand);
}

// Simulation steps
function apply_consumption(){
  if(state.production_shutdown) return;
  const per_min = consumption_per_minute();
  const per_step = per_min * minutes_per_step;
  state.factory_stock = Math.max(0, state.factory_stock - per_step);
}

function compute_worker_speed(){
  const per_min = consumption_per_minute();
  const capacity = Math.max(0, state.worker_capacity);
  if (capacity<=0) return 0;
  let half_trip_minutes = null;
  if(per_min>0){
    const trips_per_minute = per_min / capacity;
    if(trips_per_minute>0){
      const cycle_minutes = 1.0 / trips_per_minute;
      half_trip_minutes = Math.max(minutes_per_step, cycle_minutes / 2.0);
    }
  }else{
    if(state.worker_direction===-1 && state.worker_progress>0) half_trip_minutes = 0.5;
    else if(state.worker_direction===1 && state.worker_progress<1) half_trip_minutes = 0.5;
  }
  if (!half_trip_minutes || !isFinite(half_trip_minutes) || half_trip_minutes<=0) return 0;
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

  [factory, warehouse, supplier].forEach(f =>{
    ctx.fillStyle = f.color; ctx.strokeStyle = f.stroke; ctx.lineWidth = 2;
    roundRect(ctx, f.x, f.y, f.w, f.h, 8, true, true);
    ctx.fillStyle = '#333'; ctx.font = 'bold 12px Segoe UI';
    ctx.fillText(f.label, f.x + f.w/2 - ctx.measureText(f.label).width/2, f.y + f.h + 18);
  });

  // draw dotted paths
  ctx.strokeStyle = '#b0bec5'; ctx.setLineDash([8,6]); ctx.lineWidth = 6;
  ctx.beginPath(); ctx.moveTo(factory.x+factory.w, factory.y+70); ctx.lineTo(warehouse.x, warehouse.y+70); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(warehouse.x+warehouse.w, warehouse.y+40); ctx.lineTo(supplier.x, supplier.y+40); ctx.stroke();
  ctx.setLineDash([]);

  // draw stock blocks in each facility
  draw_stock_blocks(factory, state.factory_stock, state.high_stock_threshold, '#66bb6a');
  draw_stock_blocks(warehouse, state.warehouse_stock, state.high_stock_threshold, '#ffa726', state.safety_stock, compute_reorder_point());

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
  document.getElementById('score').innerText = 'Score: ' + Math.round(state.score);
  document.getElementById('factory').innerText = 'Factory: ' + Math.round(state.factory_stock);
  document.getElementById('warehouse').innerText = 'Warehouse: ' + Math.round(state.warehouse_stock);
  document.getElementById('alerts').innerText = generate_alerts();
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
  apply_consumption();
  move_worker();
  handle_replenishment();
  move_truck();
  apply_scenario_effects();
  update_score();
  draw();
}

// Simple external signals handling (Streamlit buttons cause rerun which re-embeds params)
function handleExternalActions(){
  // If reset signal changed on embedding, reinitialize
  if(params.action_reset && params.action_reset !== lastResetSignal){
    lastResetSignal = params.action_reset;
    // reset state
    state.factory_stock = 240.0;
    state.warehouse_stock = 520.0;
    state.production_shutdown = false;
    state.truck_en_route = false;
    state.truck_progress = 0;
    state.truck_delivery = 0;
    state.truck_wait_timer = 0;
    state.truck_travel_minutes_total = 0;
    state.truck_travel_minutes_remaining = 0;
    state.worker_progress = 0;
    state.worker_direction = 1;
    state.worker_load = 0;
    state.score = 0;
  }
  // Start/pause toggle (embedding with changed flag flips)
  if(params.action_start_pause && params.action_start_pause !== lastStartPauseSignal){
    lastStartPauseSignal = params.action_start_pause;
    started = !started;
  }
}

// On first embed, if Start/Pause was pressed we toggle accordingly
if(params.action_start_pause) {
  started = !started;
}

// update minutes_per_step whenever speed_unit changes
minutes_per_step = (base_interval_ms / 60000.0) * (params.speed_unit === 'second' ? 60.0 : 1.0);

// animation loop
let intervalId = null;
function startLoop(){
  if(intervalId) clearInterval(intervalId);
  intervalId = setInterval(()=> {
    if(started){
      tick();
    }
    handleExternalActions();
  }, base_interval_ms);
}
startLoop();
draw();

</script>
</body>
</html>
"""

# embed HTML
components.html(html_template.replace("__PARAMS__", params_json), height=560, scrolling=True)
