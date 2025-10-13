/* ===== API + DOM helpers ===== */
const apiBase = window.__API_BASE__ || ""; // e.g., "https://api.demo.com"
const $ = (id) => document.getElementById(id);

/* ===== Page state ===== */
const state = {
  token: new URLSearchParams(location.search).get("token"),
  timer: null,
  expiry: null
};

function setBusy(b) { $("card").setAttribute("aria-busy", b ? "true" : "false"); }
function show(el, on=true){ on ? el.classList.remove("hidden") : el.classList.add("hidden"); }

/* ===== Renderers ===== */
function renderOffer(o){
  $("title").textContent = "We found an alternative";
  $("summary").innerHTML = `
    <div class="kicker">Disruption: Flight <span class="badge">${o.disruption?.flight || "N/A"}</span></div>
    <h2 style="margin: .5rem 0 0.25rem">${o.flightNo}  ${o.origin} → ${o.destination}</h2>
    <div class="row">
      <span class="badge">Dep ${o.dep}</span>
      <span class="badge">Arr ${o.arr}</span>
      <span class="badge">${o.stops === 0 ? "Direct" : `${o.stops}-stop`}</span>
      <span class="badge">${o.cabin}</span>
      <span class="badge">${o.arrivalDelta >= 0 ? "+"+o.arrivalDelta : o.arrivalDelta} min vs original</span>
    </div>
  `;
  show($("actions"), true);
}

function renderAccepted(c){
  $("title").textContent = "You're rebooked!";
  $("summary").innerHTML = `
    <div class="success">✅ Confirmed</div>
    <div class="row">
      <span class="badge">${c.flightNo}</span>
      <span class="badge">${c.origin} → ${c.destination}</span>
      <span class="badge">Dep ${c.dep}</span>
    </div>`;
  show($("actions"), false);
  $("notice").textContent = "We've emailed your itinerary.";
}

function renderVoucher(v){
  $("title").textContent = "Voucher issued";
  $("summary").innerHTML = `
    <div class="row">
      <span class="badge">Code ${v.code}</span>
      <span class="badge">$${v.amount}</span>
      <span class="badge">Exp ${v.expiry}</span>
    </div>`;
  show($("actions"), false);
  $("notice").textContent = "We’ve also sent this to your email.";
}

function renderExpired(){
  $("title").textContent = "This link has expired";
  $("summary").innerHTML = `<p class="warn">Please contact support or request assistance at the airport desk.</p>`;
  show($("actions"), false);
}

/* ===== Countdown ===== */
function tick(){
  if(!state.expiry) return;
  const s = Math.max(0, Math.floor((state.expiry - Date.now())/1000));
  const mm = String(Math.floor(s/60)).padStart(2,"0"), ss = String(s%60).padStart(2,"0");
  $("countdown").textContent = `Expires in ${mm}:${ss}`;
  if(s===0){ clearInterval(state.timer); renderExpired(); }
}

/* ===== API helper ===== */
async function api(path, opts){
  const res = await fetch(`${apiBase}${path}`, { ...opts, headers: { "Content-Type":"application/json" }});
  if(!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

/* ===== Boot with mock data if no API yet ===== */
const MOCK = true;

async function loadOffer(){
  setBusy(true);
  try{
    let data;
    if(MOCK){
      data = {
        option: { flightNo:"AB456", origin:"YYZ", destination:"YVR", dep:"10:05", arr:"12:25", stops:0, cabin:"Economy", arrivalDelta:45, disruption:{flight:"AB123"} },
        expiresAt: Date.now() + 30*60*1000, remaining: 2, status:"pending"
      };
    }else{
      data = await api(`/offer/${encodeURIComponent(state.token)}`, { method:"GET" });
    }
    state.expiry = typeof data.expiresAt === "number" ? data.expiresAt : Date.parse(data.expiresAt);
    clearInterval(state.timer); state.timer = setInterval(tick, 1000); tick();
    if(data.status === "expired") return renderExpired();
    renderOffer(data.option);
  }catch(e){
    $("title").textContent = "Unable to load offer";
    $("summary").innerHTML = `<p class="error">Please try again.</p>`;
  }finally{
    setBusy(false);
  }
}

/* ===== Actions ===== */
async function accept(){
  disableActions(true);
  try{
    const res = MOCK ? { confirmation:{ flightNo:"AB456", origin:"YYZ", destination:"YVR", dep:"10:05" } }
                     : await api(`/offer/${state.token}/accept`, { method:"POST" });
    renderAccepted(res.confirmation);
  }catch(e){ toast("Could not accept. Try again."); }
  disableActions(false);
}

async function nextOption(){
  disableActions(true);
  try{
    const res = MOCK ? { option:{ flightNo:"AB789", origin:"YYZ", destination:"YVR", dep:"12:30", arr:"14:50", stops:1, cabin:"Economy", arrivalDelta:180, disruption:{flight:"AB123"} }, remaining:0 }
                     : await api(`/offer/${state.token}/next`, { method:"POST" });
    renderOffer(res.option);
    $("notice").textContent = res.remaining ? `${res.remaining} option(s) left` : "No more options.";
  }catch(e){ toast("Could not fetch next option."); }
  disableActions(false);
}

async function decline(){
  disableActions(true);
  try{
    const res = MOCK ? { voucher:{ code:"X9FJ-4K2Q", amount:150, expiry:"2025-12-31" } }
                     : await api(`/offer/${state.token}/decline`, { method:"POST" });
    renderVoucher(res.voucher);
  }catch(e){ toast("Could not issue voucher."); }
  disableActions(false);
}

function disableActions(b){ ["btn-accept","btn-next","btn-decline"].forEach(id => $(id).disabled = b); }
function toast(msg){ $("notice").textContent = msg; }

/* ===== Wire up buttons ===== */
$("btn-accept").onclick = accept;
$("btn-next").onclick = nextOption;
$("btn-decline").onclick = decline;

/* ===== Boot page ===== */
loadOffer();

/* ===== Footer slideshow (auto, ~10s total, no controls, no loop) ===== */
/* ===== Footer slideshow (auto, ~10s total, no controls, no loop) ===== */
/* ===== Footer slideshow (auto, ~2min cycle, infinite loop, no controls) ===== */
/* ===== Footer slideshow (auto, ~2min cycle, infinite with reset to first, smooth) ===== */
/* ===== Footer slideshow (auto, ~20s cycle, infinite with reset to first, video-speed) ===== */
(function initSlideshow(){
  const root = document.getElementById('filmstack');
  if (!root) return;

  const DURATION = 20_000;      // total run time per cycle (ms) — ~20 seconds for video feel
  const LOOP = true;            // infinite, but resets to first after each cycle
  const base = 'assets/planes/';
  const files = Array.from({length: 9}, (_,i) => `${base}plane${String(i+1).padStart(2,'0')}.png`);

  // Build frames
  const frames = files.map(src => {
    const f = document.createElement('div');
    f.className = 'frame';
    f.style.backgroundImage = `url("${src}")`;
    root.appendChild(f);
    return f;
  });

  // Preload images to prevent flashes/broken looks
  Promise.all(files.map(src => new Promise(resolve => {
    const img = new Image();
    img.onload = () => { console.log('Loaded:', src); resolve(true); }
    img.onerror = () => { console.warn('Missing image:', src); resolve(false); };
    img.src = src;
  }))).then(loaded => {
    console.log(`Slideshow ready: ${loaded.filter(Boolean).length}/9 images`);
    start();
  });

  function start(){
    const active = frames.filter(f => getComputedStyle(f).backgroundImage !== 'none');
    if (!active.length) {
      console.warn('No valid images for slideshow');
      return;
    }

    // if user prefers reduced motion, just show the first frame and hold (no loop)
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
      active[0].classList.add('show');
      return;
    }

    const perFrame = Math.max(120, Math.floor(DURATION / active.length));
    let i = 0;
    let cycleStart = Date.now();
    active[0].classList.add('show');

    const tick = () => {
      active[i]?.classList.remove('show');
      i = (i + 1) % active.length;
      active[i]?.classList.add('show');

      // After full cycle: Brief pause (1s) then reset to first (smooth fade)
      if (i === 0 && Date.now() - cycleStart >= DURATION) {
        setTimeout(() => {
          // Fade out current (last), then back to first
          active[active.length - 1]?.classList.remove('show');
          setTimeout(() => {
            active[0].classList.add('show');
            cycleStart = Date.now();  // Reset cycle timer
          }, 250);  // Half-transition pause for breath
        }, 1000);  // 1s hold on last before reset
        return;  // Skip next tick until reset
      }

      setTimeout(tick, perFrame);
    };

    setTimeout(tick, perFrame);
  }
})();