"""Opt-in localhost API and phone view for the desktop's StashWatch store."""
from __future__ import annotations

import csv
import hmac
import io
from urllib.parse import urlsplit

from flask import Flask, Response, jsonify, request

from poe2trade.app.stash_watch import WatchConflict, WatchSpec
from poe2trade.app.stash_watch_trade import catalog as default_catalog


CSV_COLUMNS = ("listing_id", "item", "category", "price", "currency", "stash_name", "stash_x", "stash_y", "last_seen_at")


def listings_csv(rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return "\ufeff" + buffer.getvalue()


def create_app(manager, token: str, *, catalog=default_catalog):
    if not isinstance(token, str) or not token.strip():
        raise ValueError("A StashWatch API token is required")
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024

    @app.before_request
    def authenticate():
        if request.path == "/" and request.method == "GET":
            return None
        supplied = request.headers.get("X-API-Key", "")
        authorization = request.headers.get("Authorization", "")
        if authorization.lower().startswith("bearer "):
            supplied = authorization[7:]
        if not hmac.compare_digest(supplied.encode(), token.encode()):
            return jsonify(error="A valid StashWatch API token is required"), 401
        origin = request.headers.get("Origin")
        if origin and urlsplit(origin).netloc != request.host:
            return jsonify(error="Cross-origin requests are not allowed"), 403

    @app.after_request
    def no_cache(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; frame-ancestors 'none'"
        return response

    @app.errorhandler(ValueError)
    def invalid(exc):
        return jsonify(error=str(exc)), 409 if isinstance(exc, WatchConflict) or "running" in str(exc) else 400

    @app.errorhandler(KeyError)
    def missing(exc):
        return jsonify(error=str(exc.args[0])), 404

    def settings(previous=None):
        payload = request.get_json(silent=True)
        fields = set(WatchSpec.__dataclass_fields__)
        if not isinstance(payload, dict) or set(payload) - fields:
            raise ValueError("Send a settings object with account, league, listing_type, categories and interval_minutes")
        merged = (previous or {}) | payload
        if not {"account", "league"} <= merged.keys():
            raise ValueError("account and league are required")
        spec = WatchSpec(**merged)
        allowed = catalog()["categories"]
        if any(name not in allowed for name in spec.categories):
            raise ValueError("Unknown category selection")
        return spec

    @app.get("/")
    def index():
        return Response(PHONE_PAGE, mimetype="text/html")

    @app.get("/stash/catalog")
    def selections():
        return jsonify(catalog())

    @app.get("/stash/watches")
    def watches():
        return jsonify(watches=manager.store.watches())

    @app.post("/stash/watches")
    def create():
        return jsonify(manager.save(settings())), 201

    @app.patch("/stash/watches/<watch_id>")
    def update(watch_id):
        previous = manager.store.get(watch_id)["settings"]
        version = request.headers.get("If-Match")
        if version is not None and (not version.isdigit() or int(version) < 1):
            raise ValueError("If-Match must be a positive settings version")
        return jsonify(manager.save(settings(previous), watch_id=watch_id,
                                    expected_version=int(version) if version else None))

    @app.post("/stash/watches/<watch_id>/start")
    def start(watch_id):
        return jsonify(manager.start(watch_id))

    @app.post("/stash/watches/<watch_id>/pause")
    def pause(watch_id):
        return jsonify(manager.pause(watch_id))

    @app.post("/stash/watches/<watch_id>/check")
    def check(watch_id):
        return jsonify(manager.check_now(watch_id, request_id=request.headers.get("X-Request-ID"))), 202

    @app.get("/stash/runs/<run_id>")
    def run(run_id):
        return jsonify(manager.store.run(run_id))

    @app.get("/stash/watches/<watch_id>/listings")
    def listings(watch_id):
        rows = manager.store.listings(watch_id)
        if request.args.get("format") == "csv":
            return Response(listings_csv(rows), mimetype="text/csv",
                            headers={"Content-Disposition": 'attachment; filename="stashwatch.csv"'})
        return jsonify(listings=rows)

    @app.get("/stash/watches/<watch_id>/events")
    def events(watch_id):
        try:
            after = int(request.args.get("after", "0"))
            limit = int(request.args.get("limit", "500"))
        except ValueError as exc:
            raise ValueError("after and limit must be integers") from exc
        if after < 0 or not 1 <= limit <= 1000:
            raise ValueError("after must be nonnegative; limit must be from 1 to 1000")
        rows = manager.store.events(watch_id, after=after, limit=limit)
        return jsonify(events=rows, next_cursor=rows[-1]["id"] if rows else after,
                       **manager.store.history_identity(watch_id))

    return app


PHONE_PAGE = """<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>StashWatch · StashSage</title>
<style>
:root{color-scheme:dark;font-family:system-ui;background:#111a23;color:#e0e9f0}body{max-width:960px;margin:auto;padding:20px}
h1{margin-bottom:4px}p{color:#acbdcc}section{background:#1a2835;border-radius:12px;padding:18px;margin:16px 0}
label{display:block;margin-top:12px}input,select,button{font:inherit;padding:10px;border:1px solid #43596b;border-radius:7px;background:#14212c;color:inherit;box-sizing:border-box}
input,select{width:100%;margin-top:5px}button{cursor:pointer;margin:10px 8px 0 0;background:#245777}button:disabled{opacity:.5}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}.table{overflow:auto}table{width:100%;border-collapse:collapse;font-size:14px}
td,th{text-align:left;padding:9px;border-bottom:1px solid #314657;white-space:nowrap}#message{color:#f1c77b;white-space:pre-wrap}.muted{color:#a6bbcc;font-size:14px}li{margin-bottom:12px}
</style>
<h1>StashWatch</h1><p>This page controls StashSage on your PC. Keep the app running and the PC awake.</p>
<section id="login"><label>Desktop access token<input id="token" type="password" autocomplete="off"></label><button id="connect">Connect</button>
<p class="muted">On your PC, open StashWatch and press Copy access token (Copy API token in v0.5.24). Paste it above, then press Connect. This is your StashSage access password, not a Tailscale key. It stays only in this page's memory and is forgotten when the page closes.</p>
<p class="muted">For phone access, connect <a href="https://tailscale.com/download">Tailscale</a> on both devices and use the HTTPS phone link from the desktop setup guide. The Android app can also run checks independently in This phone mode.</p></section>
<p id="message" role="status"></p>
<main id="main" hidden><section><label>Saved watch<select id="watch"><option value="">New watch</option></select></label>
<div class="grid"><label>Account<input id="account" placeholder="Player#1234"></label><label>League<input id="league" list="leagues"><datalist id="leagues"></datalist></label>
<label>Listings to watch<select id="scope"><option value="merchant">Merchant</option><option value="all">All public listings</option></select></label>
<label>Check every<select id="interval"><option value="15">15 minutes</option><option value="30" selected>30 minutes</option><option value="60">1 hour</option><option value="120">2 hours</option><option value="custom">Custom</option></select></label></div>
<label id="customLabel" hidden>Custom interval (minutes)<input id="custom" type="number" min="1" max="10080" value="30"></label>
<details><summary>Categories (all when none selected)</summary><select id="categories" multiple size="6" aria-label="Categories"></select><button id="clear">All categories</button></details>
<button id="save">Save settings</button><button id="start">Start watching</button><button id="pause">Pause</button><button id="check">Check now</button>
<p id="status"></p><p class="muted">Checks continue on your desktop when this page disconnects. The desktop must remain running. Missing listings may have sold or been delisted.</p></section>
<section><h2>Current Listings</h2><button id="csv">Download CSV</button><div class="table"><table><thead><tr><th>Item</th><th>Price</th><th>Stash</th><th>Last seen</th></tr></thead><tbody id="rows"></tbody></table></div></section>
<section><h2>Activity</h2><ol id="events"></ol></section></main>
<script>
let token='', watches=[], cursor=0, activity=[], busy=false;
const el=id=>document.getElementById(id), selected=()=>el('watch').value;
const date=t=>t?new Date(t*1000).toLocaleString():'—';
async function api(path,method='GET',body){const r=await fetch(path,{method,headers:{'Authorization':'Bearer '+token,'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});if(!r.ok){let e=await r.json();throw Error(e.error||r.status)}return r}
async function guard(fn){try{el('message').textContent='';await fn()}catch(e){el('message').textContent=e.message}}
function fill(w){cursor=0;activity=[];const s=w?.settings;if(!s)return;el('account').value=s.account;el('league').value=s.league;el('scope').value=s.listing_type;el('interval').value=[15,30,60,120].includes(s.interval_minutes)?String(s.interval_minutes):'custom';el('custom').value=s.interval_minutes;el('customLabel').hidden=el('interval').value!=='custom';for(const o of el('categories').options)o.selected=s.categories.includes(o.value)}
async function load(){const keep=selected();watches=(await(await api('/stash/watches')).json()).watches;el('watch').replaceChildren(new Option('New watch',''));for(const w of watches)el('watch').add(new Option(w.settings.account+' · '+w.settings.league+' · '+w.settings.listing_type,w.id));el('watch').value=keep}
async function refresh(){if(busy||!selected())return;busy=true;try{await load();const w=watches.find(w=>w.id===selected());if(!w)return;el('status').textContent=(w.last_run?.status==='running'?'Checking':w.enabled?'Watching':'Paused')+' · Last checked: '+date(w.last_check)+' · Next check: '+date(w.next_check)+' · '+(w.last_complete===null?'No baseline yet':w.last_complete?'Complete':'Incomplete');if(w.last_error)el('message').textContent=w.last_error+' Previously seen listings are retained.';const data=await(await api('/stash/watches/'+w.id+'/listings')).json();el('rows').replaceChildren();for(const r of data.listings){const tr=document.createElement('tr');for(const text of [r.item,r.price===null?'Unpriced':r.price+' '+r.currency,r.stash_name||'',date(r.last_seen_at)]){const td=document.createElement('td');td.textContent=text;tr.append(td)}el('rows').append(tr)}
let page;do{page=await(await api('/stash/watches/'+w.id+'/events?after='+cursor)).json();cursor=page.next_cursor;activity=activity.concat(page.events).slice(-100)}while(page.events.length===500);el('events').replaceChildren();for(const e of [...activity].reverse()){const li=document.createElement('li'),r=e.after||e.before;let text=e.type==='price_changed'?'Price changed: '+e.before.price+' '+e.before.currency+' → '+e.after.price+' '+e.after.currency:e.type==='listing_added'?'Listed':e.type==='listing_reappeared'?'Appeared again':'No longer observed (sale or delisting unknown)';li.textContent=date(e.observed_at)+' · '+r.item+' · '+text;el('events').append(li)}}finally{busy=false}}
el('connect').onclick=()=>guard(async()=>{token=el('token').value;const c=await(await api('/stash/catalog')).json();el('categories').replaceChildren();for(const n of c.categories)el('categories').add(new Option(n.replaceAll('_',' '),n));for(const n of c.leagues)el('leagues').append(new Option(n,n));await load();el('login').hidden=true;el('main').hidden=false;el('token').value='';if(watches.length){el('watch').value=watches[0].id;fill(watches[0]);await refresh()}});
el('watch').onchange=()=>guard(async()=>{fill(watches.find(w=>w.id===selected()));el('rows').replaceChildren();el('events').replaceChildren();el('status').textContent='';await refresh()});
el('interval').onchange=()=>{el('customLabel').hidden=el('interval').value!=='custom'};el('clear').onclick=()=>{for(const o of el('categories').options)o.selected=false};
el('save').onclick=()=>guard(async()=>{const s={account:el('account').value,league:el('league').value,listing_type:el('scope').value,interval_minutes:Number(el('interval').value==='custom'?el('custom').value:el('interval').value),categories:[...el('categories').selectedOptions].map(o=>o.value)};const id=selected();const w=await(await api('/stash/watches'+(id?'/'+id:''),id?'PATCH':'POST',s)).json();await load();el('watch').value=w.id;fill(w);await refresh()});
for(const action of ['start','pause','check'])el(action).onclick=()=>guard(async()=>{if(!selected())throw Error('Save a watch first');await api('/stash/watches/'+selected()+'/'+action,'POST');await refresh()});
el('csv').onclick=()=>guard(async()=>{if(!selected())throw Error('Select a watch first');const blob=await(await api('/stash/watches/'+selected()+'/listings?format=csv')).blob(),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='stashwatch.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});
setInterval(()=>{if(token&&selected())guard(refresh)},3000);
</script></html>"""
