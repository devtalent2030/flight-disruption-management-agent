/* ===== API + DOM helpers ===== */
const apiBase = window.__API_BASE__ || ""; // e.g., "https://8wxme4f0a8.execute-api.ca-central-1.amazonaws.com/prod"
const $ = (id) => document.getElementById(id);

/* ===== Page state ===== */
const url = new URL(location.href);
const state = {
  // token is in path in the API, but in your link it’s in the query too; we’ll accept either.
  token: url.searchParams.get("token"),
  offerId: url.searchParams.get("offerId"),
  sig: url.searchParams.get("sig"),
  exp: url.searchParams.get("exp"),
  timer: null,
  expiry: null,
  lastOffer: null,      // keep the current offer payload so we can render ACCEPT state nicely
};

function setBusy(b) { $("card").setAttribute("aria-busy", b ? "true" : "false"); }
function show(el, on=true){ on ? el.classList.remove("hidden") : el.classList.add("hidden"); }
function disableActions(b){ ["btn-accept","btn-next","btn-decline"].forEach(id => $(id).disabled = b); }
function toast(msg){ $("notice").textContent = msg; }

/* ===== Renderers ===== */
function renderOfferView(normalized){
  const o = normalized.option || {};
  $("title").textContent = "We found an alternative";
  $("summary").innerHTML = `
    <div class="kicker">Offer: <span class="badge">${normalized.offerId}</span></div>
    <h2 style="margin:.5rem 0 0.25rem">${o.flightNo || "—"} ${o.origin ? ` ${o.origin} → ${o.destination}` : ""}</h2>
    <div class="row">
      ${o.dep ? `<span class="badge">Dep ${o.dep}</span>` : ""}
      ${o.arr ? `<span class="badge">Arr ${o.arr}</span>` : ""}
      ${o.price != null ? `<span class="badge">$${o.price}</span>` : ""}
      <span class="badge">${Number.isFinite(o.arrivalDelta) ? `${o.arrivalDelta>=0?"+":""}${o.arrivalDelta} min vs original` : "Alternative"}</span>
    </div>
  `;
  $("notice").textContent = Number.isFinite(normalized.remaining) && normalized.remaining > 0
    ? `${normalized.remaining} option(s) left`
    : "";
  show($("actions"), true);
}

function renderAccepted(confirmLike){
  $("title").textContent = "You're rebooked!";
  $("summary").innerHTML = `
    <div class="success">✅ Confirmed</div>
    <div class="row">
      ${confirmLike.flightNo ? `<span class="badge">${confirmLike.flightNo}</span>` : ""}
      ${confirmLike.origin ? `<span class="badge">${confirmLike.origin} → ${confirmLike.destination}</span>` : ""}
      ${confirmLike.dep ? `<span class="badge">Dep ${confirmLike.dep}</span>` : ""}
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
// We must include offerId/sig/exp on every call
function q() {
  const qp = new URLSearchParams({ offerId: state.offerId, sig: state.sig, exp: state.exp });
  return `?${qp.toString()}`;
}
async function api(path, opts){
  const res = await fetch(`${apiBase}${path}${q()}`, {
    ...opts,
    headers: { "Content-Type":"application/json" }
  });
  if(!res.ok){
    const text = await res.text().catch(()=>String(res.status));
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

/* ===== Normalizer (backend → UI) ===== */
function normalizeOffer(offer){
  // backend GET returns:
  // { offerId, status, selectedIndex, options:[{flightNo,departAt,arriveAt,price}], expiresAt }
  const idx = (offer.selectedIndex ?? 0);
  const opt = offer.options?.[idx] || {};
  const option = {
    flightNo: opt.flightNo,
    dep: opt.departAt,
    arr: opt.arriveAt,
    price: (typeof opt.price === "number" ? opt.price : undefined),
    // origin/destination not available in backend sample; keep undefined (UI handles it)
    origin: undefined,
    destination: undefined,
    arrivalDelta: undefined
  };
  const expiresMs = Number.isFinite(Number(offer.expiresAt))
    ? Number(offer.expiresAt) * 1000   // backend uses epoch seconds; convert to ms
    : Date.parse(offer.expiresAt);

  const remaining = Math.max(0, (offer.options?.length || 0) - idx - 1);

  return {
    offerId: offer.offerId,
    status: offer.status,
    option,
    remaining,
    expiresAt: expiresMs
  };
}

/* ===== Boot (live API) ===== */
async function loadOffer(){
  setBusy(true);
  try{
    if(!(state.token && state.offerId && state.sig && state.exp)){
      throw new Error("Missing token/offerId/sig/exp in URL.");
    }

    const raw = await api(`/offer/${encodeURIComponent(state.token)}`, { method:"GET" });
    state.lastOffer = raw;

    const data = normalizeOffer(raw);
    state.expiry = data.expiresAt;
    clearInterval(state.timer); state.timer = setInterval(tick, 1000); tick();

    // expired?
    if (Date.now() >= state.expiry) return renderExpired();
    renderOfferView(data);
  }catch(e){
    $("title").textContent = "Unable to load offer";
    $("summary").innerHTML = `<p class="error">Please try again. ${e?.message || ""}</p>`;
    show($("actions"), false);
  }finally{
    setBusy(false);
  }
}

/* ===== Actions (live) ===== */
async function accept(){
  disableActions(true);
  try{
    const res = await api(`/offer/${encodeURIComponent(state.token)}/accept`, { method:"POST" });
    // Backend returns { offerId, status:"ACCEPTED" } — use current option as “confirmation”
    const current = normalizeOffer(state.lastOffer || {}).option || {};
    renderAccepted(current);
  }catch(e){ toast("Could not accept. Try again."); }
  disableActions(false);
}

async function nextOption(){
  disableActions(true);
  try{
    // Backend returns { offerId, selectedIndex } → then we re-GET to show the new option
    await api(`/offer/${encodeURIComponent(state.token)}/next`, { method:"POST" });
    const raw = await api(`/offer/${encodeURIComponent(state.token)}`, { method:"GET" });
    state.lastOffer = raw;
    const data = normalizeOffer(raw);
    renderOfferView(data);
  }catch(e){ toast("Could not fetch next option."); }
  disableActions(false);
}

async function decline(){
  disableActions(true);
  try{
    // Backend returns { offerId, status:"DECLINED" } — if you later issue vouchers, call another endpoint
    renderVoucher({ code:"TBD", amount:0, expiry:"—" });
  }catch(e){ toast("Could not decline."); }
  disableActions(false);
}

/* ===== Wire up buttons ===== */
$("btn-accept").onclick = accept;
$("btn-next").onclick = nextOption;
$("btn-decline").onclick = decline;

/* ===== Boot page ===== */
loadOffer();

/* ===== Footer slideshow (unchanged) ===== */
(function initSlideshow(){
  const root = document.getElementById('filmstack');
  if (!root) return;

  const DURATION = 20_000;
  const base = 'assets/planes/';
  const files = Array.from({length: 9}, (_,i) => `${base}plane${String(i+1).padStart(2,'0')}.png`);

  const frames = files.map(src => {
    const f = document.createElement('div');
    f.className = 'frame';
    f.style.backgroundImage = `url("${src}")`;
    root.appendChild(f);
    return f;
  });

  Promise.all(files.map(src => new Promise(resolve => {
    const img = new Image();
    img.onload = () => resolve(true);
    img.onerror = () => resolve(false);
    img.src = src;
  }))).then(() => start());

  function start(){
    const active = frames.filter(f => getComputedStyle(f).backgroundImage !== 'none');
    if (!active.length) return;
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) { active[0].classList.add('show'); return; }

    const perFrame = Math.max(120, Math.floor(DURATION / active.length));
    let i = 0;
    active[0].classList.add('show');

    const tick = () => {
      active[i]?.classList.remove('show');
      i = (i + 1) % active.length;
      active[i]?.classList.add('show');
      setTimeout(tick, perFrame);
    };
    setTimeout(tick, perFrame);
  }
})();
