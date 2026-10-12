(function () {
  "use strict";
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  var root = document.documentElement;

  /* ---------- Language: Swedish / English, switchable ---------- */
  var LKEY = "me-motion-lang";
  function lang() { return root.getAttribute("data-lang") === "en" ? "en" : "sv"; }
  function L(sv, en) { return lang() === "en" ? en : sv; }
  var langListeners = [];
  function applyLang(l) {
    root.setAttribute("data-lang", l); root.lang = l;
    document.querySelectorAll("[data-sv-placeholder]").forEach(function (el) { el.placeholder = el.getAttribute("data-" + l + "-placeholder"); });
    document.querySelectorAll("option[data-sv]").forEach(function (el) { el.textContent = el.getAttribute("data-" + l); });
    var t = document.getElementById("page-title"); if (t) document.title = t.getAttribute("data-" + l);
    document.querySelectorAll(".lang-switch button").forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-set-lang") === l ? "true" : "false"); });
    langListeners.forEach(function (fn) { fn(); });
  }
  document.querySelectorAll(".lang-switch button").forEach(function (b) {
    b.addEventListener("click", function () { var l = b.getAttribute("data-set-lang"); try { localStorage.setItem(LKEY, l); } catch (e) {} applyLang(l); });
  });

  /* ---------- Theme: follows the device; the sun / moon buttons override it ----------
     Choosing the mode the device already uses removes the override, so the site goes back to following the device. */
  var KEY = "me-motion-theme";
  var mq = window.matchMedia ? window.matchMedia("(prefers-color-scheme: light)") : null;
  var themeBtns = document.querySelectorAll(".theme-seg button");
  function stored() { try { var v = localStorage.getItem(KEY); return v === "light" || v === "dark" ? v : "auto"; } catch (e) { return "auto"; } }
  function deviceTheme() {
    var host = root.getAttribute("data-host-theme");
    if (host === "light" || host === "dark") return host;
    return mq && mq.matches ? "light" : "dark";
  }
  function effectiveTheme() { var s = stored(); return s === "auto" ? deviceTheme() : s; }
  function setTheme(mode) {
    if (mode !== "auto" && mode === deviceTheme()) mode = "auto";
    try { if (mode === "auto") localStorage.removeItem(KEY); else localStorage.setItem(KEY, mode); } catch (e) {}
    if (mode === "auto") {
      var host = root.getAttribute("data-host-theme");
      if (host === "light" || host === "dark") root.setAttribute("data-theme", host); else root.removeAttribute("data-theme");
    } else root.setAttribute("data-theme", mode);
    syncTheme();
  }
  function syncTheme() {
    var now = effectiveTheme();
    themeBtns.forEach(function (b) {
      var m = b.getAttribute("data-set-theme");
      b.setAttribute("aria-pressed", m === now ? "true" : "false");
      var t = m === "light" ? L("Ljust läge", "Light mode") : L("Mörkt läge", "Dark mode");
      b.title = t; b.setAttribute("aria-label", t);
    });
  }
  themeBtns.forEach(function (b) { b.addEventListener("click", function () { setTheme(b.getAttribute("data-set-theme")); }); });
  if (mq) { var onMq = function () { syncTheme(); }; if (mq.addEventListener) mq.addEventListener("change", onMq); else if (mq.addListener) mq.addListener(onMq); }
  langListeners.push(syncTheme);
  applyLang(lang());

  /* ---------- Generated "footage" frames ---------- */
  function rng(seed) { var s = seed % 2147483647; if (s <= 0) s += 2147483646; return function () { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; }; }
  function lin(ctx, x0, y0, x1, y1, stops) { var g = ctx.createLinearGradient(x0, y0, x1, y1); stops.forEach(function (s) { g.addColorStop(s[0], s[1]); }); return g; }
  function rad(ctx, x, y, r, stops) { var g = ctx.createRadialGradient(x, y, 0, x, y, r); stops.forEach(function (s) { g.addColorStop(s[0], s[1]); }); return g; }

  var scenes = {
    archipelago: function (c, w, h, r) {
      var hz = h * 0.58;
      c.fillStyle = lin(c, 0, 0, 0, hz, [[0, "#14213d"], [0.55, "#3c3f63"], [0.82, "#b8664c"], [1, "#f1b36c"]]); c.fillRect(0, 0, w, hz);
      c.fillStyle = rad(c, w * 0.66, hz, h * 0.5, [[0, "rgba(255,214,150,.85)"], [0.15, "rgba(255,180,110,.35)"], [1, "rgba(255,150,90,0)"]]); c.fillRect(0, 0, w, hz);
      c.fillStyle = "#ffe2b0"; c.beginPath(); c.arc(w * 0.66, hz, h * 0.035, Math.PI, 0); c.fill();
      c.fillStyle = lin(c, 0, hz, 0, h, [[0, "#5b4652"], [0.3, "#22263b"], [1, "#0b0f1a"]]); c.fillRect(0, hz, w, h - hz);
      for (var i = 0; i < 70; i++) { var y = hz + Math.pow(r(), 1.6) * (h - hz); var ww = (8 + r() * 60) * (1 - (y - hz) / (h - hz) * 0.5); c.fillStyle = "rgba(255,200,140," + (0.08 + r() * 0.35) * (1 - (y - hz) / (h - hz)) + ")"; c.fillRect(w * 0.66 - ww / 2 + (r() - 0.5) * w * 0.12, y, ww, 1.5); }
      function island(x0, x1, base, hgt, col) {
        c.fillStyle = col; c.beginPath(); c.moveTo(x0, base);
        for (var x = x0; x <= x1; x += 4) { var t = (x - x0) / (x1 - x0); c.lineTo(x, base - Math.sin(t * Math.PI) * hgt * (0.7 + r() * 0.06)); }
        c.lineTo(x1, base); c.fill();
        for (var k = 0; k < (x1 - x0) / 7; k++) { var tx = x0 + r() * (x1 - x0); var tt = (tx - x0) / (x1 - x0); var tb = base - Math.sin(tt * Math.PI) * hgt * 0.68; var th = hgt * (0.4 + r() * 0.55) * Math.sin(tt * Math.PI); c.beginPath(); c.moveTo(tx - th * 0.22, tb + 2); c.lineTo(tx, tb - th); c.lineTo(tx + th * 0.22, tb + 2); c.fill(); }
      }
      island(-w * 0.05, w * 0.42, hz + 1, h * 0.09, "#121726");
      island(w * 0.78, w * 1.08, hz + 1, h * 0.06, "#161b2b");
      island(w * 0.48, w * 0.58, hz + 1, h * 0.025, "#1d2133");
    },
    city: function (c, w, h, r) {
      c.fillStyle = lin(c, 0, 0, 0, h, [[0, "#0f1a33"], [0.6, "#2a3a63"], [1, "#d08a5c"]]); c.fillRect(0, 0, w, h);
      var x = 0;
      while (x < w) {
        var bw = w * (0.04 + r() * 0.07), bh = h * (0.25 + r() * 0.55);
        c.fillStyle = r() > 0.5 ? "#0c1222" : "#101830"; c.fillRect(x, h - bh, bw, bh);
        for (var wy = h - bh + 8; wy < h - 6; wy += 9) for (var wx = x + 4; wx < x + bw - 5; wx += 7) if (r() > 0.62) { c.fillStyle = r() > 0.25 ? "rgba(255,196,120,.85)" : "rgba(180,210,255,.7)"; c.fillRect(wx, wy, 3, 4); }
        x += bw + 2;
      }
      c.fillStyle = "rgba(255,170,100,.15)"; c.fillRect(0, h * 0.85, w, h * 0.15);
    },
    wedding: function (c, w, h, r) {
      c.fillStyle = lin(c, 0, 0, w, h, [[0, "#2b1a14"], [1, "#120c0a"]]); c.fillRect(0, 0, w, h);
      c.globalCompositeOperation = "lighter";
      for (var i = 0; i < 46; i++) { var x = r() * w, y = r() * h * 0.8, rr = h * (0.03 + r() * 0.12); var a = 0.06 + r() * 0.18; var col = r() > 0.4 ? "255,190,120" : "255,150,140"; c.fillStyle = rad(c, x, y, rr, [[0, "rgba(" + col + "," + a + ")"], [0.8, "rgba(" + col + "," + a * 0.8 + ")"], [1, "rgba(" + col + ",0)"]]); c.beginPath(); c.arc(x, y, rr, 0, 7); c.fill(); }
      c.globalCompositeOperation = "source-over";
      c.fillStyle = "#0a0706";
      function person(cx, sc) { c.beginPath(); c.arc(cx, h * 0.52, h * 0.06 * sc, 0, 7); c.fill(); c.beginPath(); c.moveTo(cx - h * 0.16 * sc, h); c.quadraticCurveTo(cx - h * 0.14 * sc, h * 0.6, cx, h * 0.6); c.quadraticCurveTo(cx + h * 0.14 * sc, h * 0.6, cx + h * 0.16 * sc, h); c.fill(); }
      person(w * 0.44, 1.05); person(w * 0.56, 0.95);
    },
    studio: function (c, w, h, r) {
      var bgs = [["#3a4458", "#59647a", "#2a3140"], ["#5a4a3e", "#8a7462", "#3b3029"], ["#3f5249", "#6b8276", "#2a362f"], ["#6b5f57", "#a39282", "#4a403a"]];
      var bg = bgs[Math.floor(r() * bgs.length)];
      c.fillStyle = lin(c, 0, 0, 0, h, [[0, bg[0]], [0.65, bg[1]], [1, bg[2]]]); c.fillRect(0, 0, w, h);
      c.fillStyle = rad(c, w * (0.35 + r() * 0.3), h * 0.4, Math.max(w, h) * 0.5, [[0, "rgba(255,240,220,.35)"], [1, "rgba(255,240,220,0)"]]); c.fillRect(0, 0, w, h);
      var glass = [["#c8935a", "#f2c48b", "#4a3220"], ["#d9d4c8", "#ffffff", "#7d776c"], ["#8fa58c", "#c9dbc4", "#3d4f3b"], ["#b9706a", "#f0b5a8", "#5a2f2b"]];
      var n = r() > 0.6 ? 3 : 1, sc = n === 3 ? 0.8 : 1;
      for (var k = 0; k < n; k++) {
        var gl = glass[Math.floor(r() * glass.length)], bx = w * (n === 3 ? 0.3 + k * 0.2 : 0.5), bw = Math.min(h * 0.16, w * 0.2) * sc * (0.8 + r() * 0.4), top = h * (0.2 + r() * 0.15), base = h * 0.8;
        c.fillStyle = "rgba(0,0,0,.3)"; c.beginPath(); c.ellipse(bx, base, bw * 0.75, h * 0.02, 0, 0, 7); c.fill();
        c.fillStyle = lin(c, bx - bw, 0, bx + bw, 0, [[0, "#1b2230"], [0.35, gl[0]], [0.5, gl[1]], [1, gl[2]]]);
        if (r() > 0.5) { c.beginPath(); c.moveTo(bx - bw * 0.5, base); c.lineTo(bx - bw * 0.5, top + h * 0.12); c.quadraticCurveTo(bx - bw * 0.5, top + h * 0.06, bx - bw * 0.2, top + h * 0.05); c.lineTo(bx - bw * 0.2, top); c.lineTo(bx + bw * 0.2, top); c.lineTo(bx + bw * 0.2, top + h * 0.05); c.quadraticCurveTo(bx + bw * 0.5, top + h * 0.06, bx + bw * 0.5, top + h * 0.12); c.lineTo(bx + bw * 0.5, base); c.fill(); c.fillStyle = "#11151e"; c.fillRect(bx - bw * 0.22, top - h * 0.04, bw * 0.44, h * 0.05); }
        else { var jt = base - h * 0.16; c.fillRect(bx - bw * 0.6, jt, bw * 1.2, base - jt); c.fillStyle = "#e9e3d8"; c.fillRect(bx - bw * 0.64, jt - h * 0.05, bw * 1.28, h * 0.05); }
      }
    },
    event: function (c, w, h, r) {
      c.fillStyle = "#07090f"; c.fillRect(0, 0, w, h);
      c.globalCompositeOperation = "lighter";
      var cols = ["120,140,255", "255,120,180", "255,190,110"];
      for (var i = 0; i < 7; i++) { var x = w * (0.08 + i * 0.14), col = cols[i % 3], ang = (r() - 0.5) * 0.7; c.fillStyle = lin(c, x, 0, x, h, [[0, "rgba(" + col + ",.55)"], [1, "rgba(" + col + ",0)"]]); c.beginPath(); c.moveTo(x - 4, 0); c.lineTo(x + 4, 0); c.lineTo(x + Math.sin(ang) * h + w * 0.08, h); c.lineTo(x + Math.sin(ang) * h - w * 0.08, h); c.fill(); }
      c.globalCompositeOperation = "source-over";
      c.fillStyle = "#05060a";
      for (var j = 0; j < w / 14; j++) { var px = r() * w, py = h * (0.8 + r() * 0.1), s = h * (0.035 + r() * 0.02); c.beginPath(); c.arc(px, py, s, 0, 7); c.fill(); c.fillRect(px - s * 1.6, py + s * 0.6, s * 3.2, h); if (r() > 0.85) { c.fillRect(px + s * 0.6, py - s * 4, s * 0.5, s * 4); } }
    },
    interview: function (c, w, h, r) {
      c.fillStyle = lin(c, 0, 0, w, 0, [[0, "#1a2130"], [1, "#0c1018"]]); c.fillRect(0, 0, w, h);
      c.fillStyle = lin(c, w * 0.1, 0, w * 0.32, 0, [[0, "rgba(200,220,255,.5)"], [1, "rgba(200,220,255,.12)"]]); c.fillRect(w * 0.1, h * 0.12, w * 0.22, h * 0.55);
      c.strokeStyle = "#1a2130"; c.lineWidth = Math.max(3, w * 0.006); c.beginPath(); c.moveTo(w * 0.21, h * 0.12); c.lineTo(w * 0.21, h * 0.67); c.moveTo(w * 0.1, h * 0.38); c.lineTo(w * 0.32, h * 0.38); c.stroke();
      c.fillStyle = rad(c, w * 0.78, h * 0.4, h * 0.25, [[0, "rgba(242,166,73,.3)"], [1, "rgba(242,166,73,0)"]]); c.fillRect(0, 0, w, h);
      var cx = w * (0.52 + r() * 0.16), tones = ["#8a9bb8", "#b89a86", "#9fb3a4", "#c4a98f"];
      c.fillStyle = lin(c, cx - h * 0.2, 0, cx + h * 0.2, 0, [[0, tones[Math.floor(r() * tones.length)]], [0.45, "#2a3143"], [1, "#0b0e15"]]);
      c.beginPath(); c.ellipse(cx, h * 0.42, h * 0.11, h * 0.14, 0, 0, 7); c.fill();
      c.beginPath(); c.moveTo(cx - h * 0.36, h); c.quadraticCurveTo(cx - h * 0.33, h * 0.64, cx, h * 0.62); c.quadraticCurveTo(cx + h * 0.33, h * 0.64, cx + h * 0.36, h); c.fill();
    },
    aerial: function (c, w, h, r) {
      c.fillStyle = lin(c, 0, 0, w, h, [[0, "#1d4a5e"], [1, "#0f2c3d"]]); c.fillRect(0, 0, w, h);
      for (var i = 0; i < 160; i++) { c.fillStyle = "rgba(255,255,255," + r() * 0.06 + ")"; c.fillRect(r() * w, r() * h, 10 + r() * 30, 1); }
      c.fillStyle = "#3d4a3a"; c.beginPath(); c.moveTo(0, 0); c.lineTo(w * 0.55, 0);
      var y = 0; for (var t = 0; t <= 1; t += 0.04) { y = t * h; c.lineTo(w * (0.55 - t * 0.25) + (r() - 0.5) * w * 0.06, y); }
      c.lineTo(0, h); c.fill();
      c.strokeStyle = "rgba(220,235,230,.35)"; c.lineWidth = 3; c.beginPath(); c.moveTo(w * 0.55, 0); for (t = 0; t <= 1; t += 0.04) c.lineTo(w * (0.565 - t * 0.25), t * h); c.stroke();
      c.fillStyle = "#2c3a2c"; for (i = 0; i < 90; i++) { c.beginPath(); c.arc(r() * w * 0.35, r() * h, 3 + r() * 9, 0, 7); c.fill(); }
      c.fillStyle = "#e8e2d6"; c.save(); c.translate(w * 0.72, h * 0.6); c.rotate(-0.5); c.fillRect(-14, -4, 28, 8); c.restore();
      c.strokeStyle = "rgba(255,255,255,.4)"; c.lineWidth = 2; c.beginPath(); c.moveTo(w * 0.72 + 12, h * 0.6 + 7); c.quadraticCurveTo(w * 0.85, h * 0.8, w * 0.95, h * 1.02); c.stroke();
    }
  };

  function paint(frame) {
    var cv = frame.querySelector("canvas");
    if (!cv) { cv = document.createElement("canvas"); cv.setAttribute("aria-hidden", "true"); frame.insertBefore(cv, frame.firstChild); }
    var w = frame.clientWidth, h = frame.clientHeight; if (!w || !h) return;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
    var c = cv.getContext("2d"); c.setTransform(dpr, 0, 0, dpr, 0, 0);
    var fn = scenes[frame.getAttribute("data-scene")] || scenes.archipelago;
    fn(c, w, h, rng(parseInt(frame.getAttribute("data-seed") || "7", 10) * 7919));
  }
  var frames = Array.prototype.slice.call(document.querySelectorAll(".frame[data-scene]"));
  frames.forEach(paint);
  var rt; window.addEventListener("resize", function () { clearTimeout(rt); rt = setTimeout(function () { frames.forEach(paint); }, 150); });

  /* ---------- Running timecode (25 fps) ---------- */
  var tcs = document.querySelectorAll("[data-timecode]");
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function fmt(f) { var fr = f % 25, s = Math.floor(f / 25); return pad(Math.floor(s / 3600)) + ":" + pad(Math.floor(s / 60) % 60) + ":" + pad(s % 60) + ":" + pad(fr); }
  if (tcs.length) {
    var start = performance.now(), base = 25 * 12 + 4;
    if (reduce) tcs.forEach(function (el) { el.textContent = fmt(base); });
    else (function tick(now) { var f = base + Math.floor((now - start) / 40); tcs.forEach(function (el) { el.textContent = fmt(f); }); requestAnimationFrame(tick); })(start);
  }

  /* ---------- Work filters ---------- */
  var chips = document.querySelectorAll(".chip[data-filter]");
  function applyFilter(f) {
    var found = false;
    chips.forEach(function (c) { var on = c.getAttribute("data-filter") === f; if (on) found = true; c.setAttribute("aria-pressed", on ? "true" : "false"); });
    if (!found) { f = "all"; chips.forEach(function (c) { c.setAttribute("aria-pressed", c.getAttribute("data-filter") === "all" ? "true" : "false"); }); }
    document.querySelectorAll("[data-cat]").forEach(function (el) { el.hidden = !(f === "all" || el.getAttribute("data-cat") === f); });
    setTimeout(function () { frames.forEach(paint); }, 0);
  }
  chips.forEach(function (chip) { chip.addEventListener("click", function () { applyFilter(chip.getAttribute("data-filter")); }); });
  if (chips.length && location.hash) applyFilter(location.hash.slice(1));

  /* ---------- Wedding picker ---------- */
  var wedding = document.querySelector(".wedding");
  if (wedding) {
    var pick = { cov: "both", len: "10" };
    wedding.querySelectorAll(".pick-seg").forEach(function (g) {
      var group = g.getAttribute("data-group");
      g.querySelectorAll("button").forEach(function (b) {
        b.addEventListener("click", function () {
          pick[group] = b.getAttribute("data-val");
          g.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
          wedding.querySelectorAll(".w-panel").forEach(function (pn) { pn.hidden = !(pn.getAttribute("data-cov") === pick.cov && pn.getAttribute("data-len") === pick.len); });
        });
      });
    });
  }

  /* ---------- Services: tabs ---------- */
  var tabs = document.querySelectorAll(".svc-tabs [data-tab]");
  function showTab(k) {
    var ok = false;
    tabs.forEach(function (t) { var on = t.getAttribute("data-tab") === k; if (on) ok = true; t.setAttribute("aria-selected", on ? "true" : "false"); t.setAttribute("aria-pressed", on ? "true" : "false"); });
    if (!ok) return;
    document.querySelectorAll("[data-panel]").forEach(function (pn) { pn.hidden = pn.getAttribute("data-panel") !== k; });
    document.querySelectorAll("[data-panel]:not([hidden]) .frame[data-scene]").forEach(paint);
  }
  tabs.forEach(function (t) { t.addEventListener("click", function () { showTab(t.getAttribute("data-tab")); }); });
  if (tabs.length && location.hash) showTab(location.hash.slice(1));

  /* ---------- Contact form: occasion + options ---------- */
  var occ = document.getElementById("occasion");
  function pressed(group) { return Array.prototype.slice.call(document.querySelectorAll('[data-group="' + group + '"] button[aria-pressed="true"]')); }
  if (occ) {
    occ.querySelectorAll("[data-group]").forEach(function (g) {
      var single = g.getAttribute("data-mode") === "single";
      g.querySelectorAll("button").forEach(function (b) {
        b.addEventListener("click", function () {
          if (single) g.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
          else b.setAttribute("aria-pressed", b.getAttribute("aria-pressed") === "true" ? "false" : "true");
          if (g.getAttribute("data-group") === "type") occ.querySelectorAll(".sub").forEach(function (sb) { sb.hidden = sb.getAttribute("data-for") !== b.getAttribute("data-val"); });
        });
      });
    });
  }
  function occasionText() {
    var t = pressed("type")[0]; if (!t) return L("Inte valt", "Not chosen");
    var name = t.getAttribute("data-" + lang()), k = t.getAttribute("data-val"), extra = [];
    var lab = function (b) { return b.getAttribute("data-" + lang()); };
    if (k === "wedding") extra = pressed("wcov").concat(pressed("wlen")).map(lab);
    return name + (extra.length ? " (" + extra.join(", ") + ")" : "");
  }

  /* ---------- Video source: mp4, or webm where mp4 can't play ---------- */
  var probe = document.createElement("video");
  function vsrc(u) { return (!/^https?:/.test(u) && !probe.canPlayType('video/mp4; codecs="avc1.4D401F"') && /\.mp4$/.test(u)) ? u.replace(/\.mp4$/, ".webm") : u; }
  /* A video can list several sources ("a.mp4|b.mp4"): try the next one if a size doesn't exist */
  function srcList(u) { return [].concat(u || []).join("|").split("|").filter(Boolean).map(vsrc); }
  function setSrcs(v, list) {
    v._srcs = list; v._si = 0;
    if (!v._hasErr) {
      v._hasErr = true;
      v.addEventListener("error", function () {
        if (v._si < v._srcs.length - 1) { v._si++; v.src = v._srcs[v._si]; if (v.autoplay || !v.paused) { var pr = v.play(); if (pr && pr.catch) pr.catch(function () {}); } }
      });
    }
    if (list.length) v.src = list[0];
  }
  /* Vimeo films are listed as "vimeo:<number>" or "vimeo:<number>:<private hash>" */
  function isVimeo(u) { return /^vimeo:/.test(srcList(u)[0] || ""); }
  function vimeoURL(u, q) { var p = srcList(u)[0].slice(6).split(":"); return "https://player.vimeo.com/video/" + p[0] + "?" + q + (p[1] ? "&h=" + p[1] : ""); }

  /* ---------- Showreel button: the logo's strokes become pause / play ----------
     The icon starts as the logo mark. The two "M" strokes fall and straighten into the pause bars;
     the "E" stroke and its three blocks fall into a triangle for play. */
  var RT = (function () {
    var mark = [[[342.8, 0], [215.7, 0], [0, 475.6], [130, 475.6]], [[575.1, 0], [448, 0], [232.3, 475.6], [362.3, 475.6]],
      [[795, 0], [667.8, 0], [452.2, 475.6], [582.1, 475.6]], [[840.2, 357.1], [710.9, 357.1], [657.2, 475.6], [787.1, 475.6]],
      [[1000, 0], [872.9, 0], [813.6, 130.7], [941.5, 130.7]], [[919, 181.1], [790.7, 181.1], [733.7, 306.7], [862.8, 306.7]]];
    return {
      logo: mark.map(function (q) { return q.map(function (p) { return [180 + p[0] * 0.64, 348 + p[1] * 0.64]; }); }),
      pause: [[[440, 230], [310, 230], [310, 770], [440, 770]], [[690, 230], [560, 230], [560, 770], [690, 770]]],
      play: [[[590, 374.9], [330, 220], [330, 780], [590, 625.1]], [[746, 467.8], [694, 436.8], [694, 563.2], [746, 532.2]],
        [[800, 500], [768, 480.9], [768, 519.1], [800, 500]], [[672, 423.7], [612, 388], [612, 612], [672, 576.3]]]
    };
  })();
  function rtIcon(svg) {
    if (!svg) return null;
    var polys = [].slice.call(svg.querySelectorAll("polygon")), raf = 0, state = "logo", started = Date.now(), timer = 0;
    var cur = polys.map(function (pl, i) { return { pts: RT.logo[i], op: 1 }; });
    function shift(q, dy) { return q.map(function (p) { return [p[0], p[1] + dy]; }); }
    function target(st, i) {
      if (st === "logo") return RT.logo[i];
      if (st === "pause") return i < 2 ? RT.pause[i] : null;
      return i >= 2 ? RT.play[i - 2] : null;
    }
    function draw() {
      polys.forEach(function (pl, i) {
        pl.setAttribute("points", cur[i].pts.map(function (p) { return p[0].toFixed(1) + "," + p[1].toFixed(1); }).join(" "));
        pl.style.opacity = cur[i].op.toFixed(3);
      });
    }
    function backOut(k) { var c = 1.35; return 1 + (c + 1) * Math.pow(k - 1, 3) + c * Math.pow(k - 1, 2); }
    function go(st) {
      if (st === state) return;
      state = st;
      var from = cur.map(function (c) { return { pts: c.pts, op: c.op }; }), order = 0;
      var to = polys.map(function (pl, i) {
        var t = target(st, i);
        if (t) {
          var entering = from[i].op < 0.05;
          if (entering) from[i] = { pts: shift(RT.logo[i], -360), op: 0 };   /* drops in from above, still slanted */
          return { pts: t, op: 1, enter: entering, delay: entering ? 55 * order++ : 0 };
        }
        return { pts: shift(from[i].pts, 360), op: 0, exit: true, delay: 0 };   /* falls away */
      });
      cancelAnimationFrame(raf);
      if (reduce) { cur = to.map(function (t) { return { pts: t.pts, op: t.op }; }); draw(); return; }
      var t0 = performance.now(), D = 620;
      function tick(now) {
        var done = true;
        cur = to.map(function (t, i) {
          var k = Math.min(1, Math.max(0, (now - t0 - t.delay) / D)); if (k < 1) done = false;
          var e = t.exit ? k * k : backOut(k), f = from[i];
          return {
            pts: f.pts.map(function (p, j) { return [p[0] + (t.pts[j][0] - p[0]) * e, p[1] + (t.pts[j][1] - p[1]) * e]; }),
            op: f.op + (t.op - f.op) * (t.exit ? Math.min(1, k * 1.6) : Math.min(1, k * 2.5))
          };
        });
        draw();
        if (!done) raf = requestAnimationFrame(tick);
      }
      raf = requestAnimationFrame(tick);
    }
    draw();
    return {
      /* the first change waits a moment so the logo is seen before it turns into the icon */
      show: function (st) {
        clearTimeout(timer);
        var wait = state === "logo" && !reduce ? Math.max(0, 900 - (Date.now() - started)) : 0;
        if (wait) timer = setTimeout(function () { go(st); }, wait); else go(st);
      }
    };
  }

  /* ---------- Big pause / play sign in the middle of the showreel ----------
     Same logo-stroke animation as the small button, large and centred. While the film is paused it stays
     as a play sign; when the film starts again it turns into pause and fades away. */
  function reelBig(host) {
    var wrap = host && host.querySelector(".reel-big"), icon = wrap && rtIcon(wrap.querySelector(".rt-icon")), hide = 0, last = null;
    return function (paused, byUser) {
      if (!wrap) return;
      host.classList.toggle("is-paused", paused);
      if (last === null && !paused) { last = paused; return; }   /* film starting on its own: no sign */
      if (byUser || last !== paused) {
        icon.show(paused ? "play" : "pause");
        clearTimeout(hide);
        if (!paused) { wrap.classList.add("flash"); hide = setTimeout(function () { wrap.classList.remove("flash"); }, reduce ? 500 : 1100); }
        else wrap.classList.remove("flash");
      }
      last = paused;
    };
  }

  /* ---------- Silent looping showreel in the opening frame ---------- */
  document.querySelectorAll("video[data-loop-src]").forEach(function (v) {
    setSrcs(v, srcList(v.getAttribute("data-loop-src")));
    v.muted = true;
    var host = v.closest(".frame"), btn = host && host.querySelector(".reel-toggle"), icon = btn && rtIcon(btn.querySelector(".rt-icon")), big = reelBig(host);
    function sync() {
      if (!btn) return;
      var paused = v.paused;
      big(paused, false);
      btn.setAttribute("aria-pressed", paused ? "true" : "false");
      btn.setAttribute("aria-label", paused ? L("Spela showreel", "Play showreel") : L("Pausa showreel", "Pause showreel"));
      btn.classList.toggle("is-paused", paused);
      if (icon) icon.show(paused ? "play" : "pause");
    }
    function toggle() { if (v.paused) { var pr = v.play(); if (pr && pr.catch) pr.catch(function () {}); } else v.pause(); }
    v.addEventListener("play", sync); v.addEventListener("pause", sync);
    if (host && btn) host.addEventListener("click", function (e) { if (e.target.closest("a")) return; toggle(); });
    langListeners.push(sync);
    if (reduce) { v.removeAttribute("autoplay"); v.pause(); sync(); return; }
    var pr = v.play(); if (pr && pr.catch) pr.catch(function () { sync(); });
    sync();
  });

  /* ---------- Showreel from Vimeo (background player): cover the frame, pause/play button ---------- */
  document.querySelectorAll("iframe.vimeo-loop").forEach(function (ifr) {
    var host = ifr.closest(".frame"), btn = host && host.querySelector(".reel-toggle"), paused = false, icon = btn && rtIcon(btn.querySelector(".rt-icon")), big = reelBig(host), byUser = false;
    var ratio = parseFloat(ifr.getAttribute("data-ratio")) || 16 / 9;
    function fit() {
      if (!host) return;
      var w = host.clientWidth, h = host.clientHeight; if (!w || !h) return;
      if (w / h > ratio) { ifr.style.width = w + "px"; ifr.style.height = Math.ceil(w / ratio) + "px"; }
      else { ifr.style.height = h + "px"; ifr.style.width = Math.ceil(h * ratio) + "px"; }
    }
    function send(m) { try { ifr.contentWindow.postMessage(JSON.stringify({ method: m }), "https://player.vimeo.com"); } catch (e) {} }
    function sync() {
      if (!btn) return;
      big(paused, byUser); byUser = false;
      btn.setAttribute("aria-pressed", paused ? "true" : "false");
      btn.setAttribute("aria-label", paused ? L("Spela showreel", "Play showreel") : L("Pausa showreel", "Pause showreel"));
      btn.classList.toggle("is-paused", paused);
      if (icon) icon.show(paused ? "play" : "pause");
    }
    if (host && btn) host.addEventListener("click", function (e) { if (e.target.closest("a")) return; paused = !paused; byUser = true; send(paused ? "pause" : "play"); sync(); });
    ifr.addEventListener("load", function () { if (reduce || paused) { paused = true; send("pause"); sync(); } });
    langListeners.push(sync);
    fit(); window.addEventListener("resize", fit);
    if (window.ResizeObserver && host) new ResizeObserver(fit).observe(host);
    sync();
  });


  /* ---------- "Through the lens" strip: arrows + native swipe, page scroll untouched ---------- */
  document.querySelectorAll(".lens").forEach(function (sec) {
    var track = sec.querySelector(".lens-track"), prev = sec.querySelector(".lens-prev"), next = sec.querySelector(".lens-next");
    if (!track) return;
    function step(d) { track.scrollBy({ left: d * Math.max(260, track.clientWidth * 0.75), behavior: reduce ? "auto" : "smooth" }); }
    function sync() {
      var max = track.scrollWidth - track.clientWidth - 2;
      if (prev) prev.disabled = track.scrollLeft <= 2;
      if (next) next.disabled = track.scrollLeft >= max;
    }
    if (prev) prev.addEventListener("click", function () { step(-1); });
    if (next) next.addEventListener("click", function () { step(1); });
    track.addEventListener("scroll", sync, { passive: true });
    track.addEventListener("keydown", function (e) { if (e.key === "ArrowRight") { e.preventDefault(); step(1); } else if (e.key === "ArrowLeft") { e.preventDefault(); step(-1); } });
    window.addEventListener("resize", sync); sync();
  });
  /* ---------- Inline video (showreel) ---------- */
  document.querySelectorAll("[data-play-src]").forEach(function (b) {
    b.addEventListener("click", function () {
      var host = b.closest(".frame"), v = document.createElement("video");
      v.controls = true; setSrcs(v, srcList(b.getAttribute("data-play-src"))); v.playsInline = true; v.autoplay = true; v.className = "inline-video";
      var bg = host.querySelector(".bg-loop"); if (bg) { bg.pause(); bg.hidden = true; }
      host.appendChild(v); b.hidden = true; var vfx = host.querySelector(".vf"); if (vfx) vfx.hidden = true;
      var pr = v.play(); if (pr && pr.catch) pr.catch(function () {});
    });
  });

  /* ---------- Booking (Cal.com): open as a pop-up on the site, matching light/dark ---------- */
  (function () {
    var calScript = document.querySelector('script[src*="cal.com/embed/embed.js"]'), calReady = false;
    if (calScript) calScript.addEventListener("load", function () { calReady = true; });
    document.addEventListener("click", function (e) {
      var a = e.target.closest && e.target.closest("[data-cal-link]"); if (!a) return;
      var dark = root.getAttribute("data-theme") === "dark" || (root.getAttribute("data-theme") !== "light" && window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches);
      a.setAttribute("data-cal-config", JSON.stringify({ layout: "month_view", theme: dark ? "dark" : "light" }));
      if (calReady) e.preventDefault();   /* the pop-up opens; otherwise the link opens the booking page */
    }, true);
  })();

  /* ---------- Sidebar: open / close ---------- */
  var sideBtn = document.querySelector(".side-toggle");
  function syncSide() {
    if (!sideBtn) return;
    var closed = root.getAttribute("data-nav") === "closed";
    sideBtn.setAttribute("aria-expanded", closed ? "false" : "true");
    sideBtn.setAttribute("aria-label", closed ? L("Öppna meny", "Open menu") : L("Stäng meny", "Close menu"));
    sideBtn.title = sideBtn.getAttribute("aria-label");
  }
  if (sideBtn) sideBtn.addEventListener("click", function () {
    var closed = root.getAttribute("data-nav") !== "closed";
    if (closed) root.setAttribute("data-nav", "closed"); else root.removeAttribute("data-nav");
    try { localStorage.setItem("me-motion-nav", closed ? "closed" : "open"); } catch (e) {}
    syncSide();
    setTimeout(function () { frames.forEach(paint); }, 280);
  });
  langListeners.push(syncSide); syncSide();

  /* ---------- Work: project pop-up ---------- */
  var modal = document.getElementById("project-modal"), dataEl = document.getElementById("projects");
  if (modal && dataEl) {
    var projects = JSON.parse(dataEl.textContent), body = document.getElementById("pm-body"), panel = modal.querySelector(".modal-panel");
    var current = -1, lastFocus = null;
    function esc(s) { return String(s).replace(/[&<>"]/g, function (ch) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]; }); }
    function tx(o) { return esc(o[lang()]); }
    function frameHTML(im, bump) {
      if (im && im.img) return '<div class="frame"><img src="' + esc(im.img) + '" alt="' + esc(im[lang()] || "") + '" loading="lazy" decoding="async"></div>';
      return '<div class="frame" data-scene="' + esc(im.scene || "archipelago") + '" data-seed="' + ((+im.seed || 7) + (bump || 0)) + '"></div>';
    }
    function visible() { return projects.filter(function (p) { var el = document.querySelector('[data-project="' + p.id + '"]'); return el && !el.hidden; }); }
    function render() {
      var p = projects[current]; if (!p) return;
      var isSeries = p.type === "series", html = "";
      var hasFilm = !!(p.films && p.films.length);
      html += '<div class="modal-media">' + frameHTML({ img: p.cover, scene: p.scene, seed: p.seed, sv: p.title.sv, en: p.title.en });
      if (hasFilm) html += '<button type="button" class="watch" data-open-media="0"><i aria-hidden="true"></i>' + L("Spela filmen", "Play the film") + '</button>';
      html += '</div>';
      html += '<div class="modal-info"><div class="stack">';
      html += '<span class="eyebrow">' + tx(p.kind) + '</span><h2 id="pm-title">' + tx(p.title) + '</h2>';
      if (p.summary[lang()]) html += '<p class="lede sub">' + tx(p.summary) + '</p>';
      if (p.process[lang()]) html += '<h3>' + L("Så gick det till", "How it was made") + '</h3><p>' + tx(p.process) + '</p>';
      html += '</div><dl class="dl">';
      if (p.client[lang()]) html += '<div><dt>' + L("Kund", "Client") + '</dt><dd>' + tx(p.client) + '</dd></div>';
      html += '<div><dt>' + L("Typ", "Type") + '</dt><dd>' + tx(p.kind) + '</dd></div>';
      if (p.length) html += '<div><dt>' + (isSeries ? L("Antal", "Images") : L("Längd", "Length")) + '</dt><dd>' + esc(p.length) + (isSeries ? L(" bilder", " images") : "") + '</dd></div>';
      if (p.fmt) html += '<div><dt>Format</dt><dd class="mono">' + esc(p.fmt) + '</dd></div>';
      if (hasFilm || (p.all && p.all.length)) html += '<a class="jump" href="#pm-all">' + (p.films && p.films.length ? L("Se alla filmer och bilder", "See all films and images") : L("Se alla bilder", "See all images")) + ' ↓</a>';
      html += '</dl></div>';
      if (p.story) {
        var fr = function (im, cls) { return '<figure class="' + cls + '">' + frameHTML(im) + (im.img ? '' : '<figcaption>' + esc(im[lang()]) + '</figcaption>') + '</figure>'; };
        html += '<div class="story"><h3>' + L("Berättelsen", "The story") + '</h3>';
        html += p.story.blocks.map(function (b) {
          if (b.type === "text") return '<p class="story-text">' + tx(b) + '</p>';
          if (b.type === "full") return fr(b.img, "story-full");
          return '<div class="story-pair">' + b.imgs.map(function (im) { return fr(im, "story-half"); }).join("") + '</div>';
        }).join("");
        if (p.story.credits && p.story.credits.length) html += '<dl class="dl story-credits">' + p.story.credits.map(function (c) { return '<div><dt>' + tx(c.k) + '</dt><dd>' + tx(c.v) + '</dd></div>'; }).join("") + '</dl>';
        html += '</div>';
      }
      var media = (p.films || []).concat(p.all || []);
      if (media.length) html += '<section class="full-project" id="pm-all"><h3>' + L("Hela projektet", "The full project") + '</h3>';
      if (media.length) html += '<div class="all-grid">' + media.map(function (im, i) {
        var isFilm = !!im.src;
        return '<button type="button" class="all-item' + (isFilm ? ' is-film' : '') + '" data-k="' + i + '" aria-label="' + esc(im[lang()]) + '">' + frameHTML(im, isFilm && !im.img ? 3 * (i + 1) : 0) +
          (isFilm ? '<span class="film-badge"><span class="film-play" aria-hidden="true"></span><span>' + tx(im) + '</span><span class="mono">' + esc(im.length || "") + '</span></span>' : '') + '</button>';
      }).join("") + '</div></section>';
      body.innerHTML = html;
      modal.setAttribute("data-cat", p.cat || "");
      body.querySelectorAll(".frame[data-scene]").forEach(paint);
      var jump = body.querySelector(".jump");
      if (jump) jump.addEventListener("click", function (e) { e.preventDefault(); var t = body.querySelector("#pm-all"); panel.scrollTo({ top: t.offsetTop - 70, behavior: reduce ? "auto" : "smooth" }); });
      body.querySelectorAll(".all-item").forEach(function (b) { b.addEventListener("click", function () { lbOpen(media, +b.getAttribute("data-k"), b); }); });
      var tp = body.querySelector("[data-open-media]"); if (tp) tp.addEventListener("click", function () { lbOpen(media, 0, tp); });
      modal.querySelector(".modal-nav").hidden = visible().length < 2;
    }
    var lb = document.createElement("div"); lb.className = "lightbox"; lb.hidden = true; lb.setAttribute("role", "dialog"); lb.setAttribute("aria-modal", "true");
    lb.innerHTML = '<div class="lb-stage"><div class="frame" data-scene="archipelago" data-seed="1"></div><img class="lb-img" alt="" hidden><video class="lb-video" controls playsinline preload="metadata" hidden></video><iframe class="lb-vimeo" title="Film" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen hidden></iframe></div><div class="lb-bar"><button class="icon-btn" type="button" data-lb="-1" aria-label="Föregående / Previous">←</button><span class="mono lb-cap"></span><span class="mono lb-count"></span><button class="icon-btn" type="button" data-lb="1" aria-label="Nästa / Next">→</button><button class="icon-btn" type="button" data-lb="x" aria-label="Stäng / Close">✕</button></div>';
    document.body.appendChild(lb);
    var lbList = [], lbI = 0, lbFrom = null;
    function lbStopVimeo() {
      var vm = lb.querySelector(".lb-vimeo");
      if (vm.getAttribute("data-key")) { vm.removeAttribute("data-key"); vm.src = "about:blank"; }
      vm.hidden = true;
    }
    function lbShow() {
      var im = lbList[lbI], f = lb.querySelector(".frame"), vid = lb.querySelector(".lb-video"), pic = lb.querySelector(".lb-img");
      vid.pause();
      var onVimeo = !!(im.src && isVimeo(im.src));
      if (!onVimeo) lbStopVimeo();
      if (onVimeo) {
        var vm = lb.querySelector(".lb-vimeo"), url = vimeoURL(im.src, "autoplay=1&dnt=1&title=0&byline=0&portrait=0");
        f.hidden = true; pic.hidden = true; vid.hidden = true; vm.hidden = false;
        if (vm.getAttribute("data-key") !== url) { vm.setAttribute("data-key", url); vm.src = url; }
      }
      else if (im.src) {
        f.hidden = true; pic.hidden = true; vid.hidden = false;
        var key = srcList(im.src).join("|");
        if (vid.getAttribute("data-key") !== key) { vid.setAttribute("data-key", key); vid.poster = im.img || ""; setSrcs(vid, srcList(im.src)); }
        vid.currentTime = 0; var pr = vid.play(); if (pr && pr.catch) pr.catch(function () {});
      }
      else if (im.img) { vid.hidden = true; f.hidden = true; pic.hidden = false; pic.src = im.img; pic.alt = im[lang()] || ""; }
      else { vid.hidden = true; pic.hidden = true; f.hidden = false; f.setAttribute("data-scene", im.scene); f.setAttribute("data-seed", im.seed); paint(f); }
      lb.querySelector(".lb-cap").textContent = im[lang()];
      lb.querySelector(".lb-count").textContent = (lbI + 1) + " / " + lbList.length;
    }
    function lbOpen(list, i, from) { lbList = list; lbI = i; lbFrom = from; lb.hidden = false; lbShow(); lb.querySelector('[data-lb="x"]').focus(); }
    function lbClose() { lb.querySelector(".lb-video").pause(); lbStopVimeo(); lb.hidden = true; if (lbFrom) lbFrom.focus(); }
    lb.addEventListener("click", function (e) {
      var b = e.target.closest("[data-lb]");
      if (!b) { if (e.target === lb || e.target.classList.contains("lb-stage")) lbClose(); return; }
      var v = b.getAttribute("data-lb");
      if (v === "x") lbClose(); else { lbI = (lbI + (+v) + lbList.length) % lbList.length; lbShow(); }
    });
    window.addEventListener("resize", function () { if (!lb.hidden && !lbList[lbI].src && !lbList[lbI].img) lbShow(); });
    function open(id, opener) {
      current = projects.findIndex(function (p) { return p.id === id; }); if (current < 0) return;
      lastFocus = opener || document.activeElement;
      modal.hidden = false; document.body.classList.add("modal-open");
      render(); panel.scrollTop = 0; panel.focus();
    }
    function close() {
      modal.hidden = true; document.body.classList.remove("modal-open");
      if (lastFocus && lastFocus.focus) lastFocus.focus();
    }
    function step(d) {
      var list = visible(), i = list.indexOf(projects[current]); if (i < 0 || !list.length) return;
      var next = list[(i + d + list.length) % list.length];
      current = projects.indexOf(next); render(); panel.scrollTop = 0;
    }
    document.querySelectorAll("[data-project]").forEach(function (el) {
      el.addEventListener("click", function (e) { e.preventDefault(); open(el.getAttribute("data-project"), el); });
    });
    modal.querySelectorAll("[data-close]").forEach(function (el) { el.addEventListener("click", close); });
    modal.querySelectorAll("[data-step]").forEach(function (el) { el.addEventListener("click", function () { step(parseInt(el.getAttribute("data-step"), 10)); }); });
    document.addEventListener("keydown", function (e) {
      if (modal.hidden) return;
      if (!lb.hidden) {
        if (e.key === "Escape") lbClose();
        else if (e.key === "ArrowRight") { lbI = (lbI + 1) % lbList.length; lbShow(); }
        else if (e.key === "ArrowLeft") { lbI = (lbI - 1 + lbList.length) % lbList.length; lbShow(); }
        return;
      }
      if (e.key === "Escape") close();
      else if (e.key === "ArrowRight") step(1);
      else if (e.key === "ArrowLeft") step(-1);
      else if (e.key === "Tab") {
        var f = panel.querySelectorAll('a[href], button:not([hidden])'); f = Array.prototype.filter.call(f, function (x) { return x.offsetParent !== null; });
        if (!f.length) return;
        if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f[f.length - 1].focus(); }
        else if (!e.shiftKey && document.activeElement === f[f.length - 1]) { e.preventDefault(); f[0].focus(); }
      }
    });
    langListeners.push(function () { if (!modal.hidden) render(); });
    if (location.hash && projects.some(function (p) { return p.id === location.hash.slice(1); })) open(location.hash.slice(1));
  }

  /* ---------- Copy helpers ---------- */
  function copy(text, btn, target) {
    function done(ok) { if (!btn.hasAttribute("data-label")) btn.setAttribute("data-label", btn.innerHTML); btn.textContent = ok ? L("Kopierat", "Copied") : L("Markera och kopiera", "Select and copy"); setTimeout(function () { btn.innerHTML = btn.getAttribute("data-label"); }, 1800); }
    function fallback() { if (target) { var range = document.createRange(); range.selectNodeContents(target); var sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(range); } done(false); }
    try { navigator.clipboard.writeText(text).then(function () { done(true); }, fallback); } catch (e) { fallback(); }
  }
  document.querySelectorAll("[data-copy]").forEach(function (btn) {
    btn.addEventListener("click", function () { var t = document.getElementById(btn.getAttribute("data-copy")); copy(t.textContent, btn, t); });
  });

  /* ---------- Enquiry form ---------- */
  var form = document.getElementById("enquiry");
  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var ok = true;
      ["name", "email", "message"].forEach(function (id) {
        var el = document.getElementById(id), err = document.getElementById(id + "-err");
        var bad = !el.value.trim() || (id === "email" && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(el.value.trim()));
        err.hidden = !bad; if (bad && ok) { el.focus(); ok = false; }
      });
      if (!ok) return;
      var v = function (id) { return document.getElementById(id).value.trim(); };
      var tbd = L("Inte bestämt än", "Not set yet");
      var endpoint = form.getAttribute("data-send"), hp = document.getElementById("hp-field");
      var errBox = document.getElementById("enquiry-error"), btn = form.querySelector('button[type="submit"]'), label = btn.innerHTML;
      function failed() {
        errBox.hidden = false; errBox.focus();
        errBox.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "nearest" });
      }
      errBox.hidden = true;
      if (!endpoint || !window.fetch) { failed(); return; }
      btn.disabled = true; btn.setAttribute("aria-busy", "true"); btn.textContent = L("Skickar…", "Sending…");
      fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        body: JSON.stringify({
          _subject: "Ny förfrågan från memotion.se · " + v("name"), _template: "table", _captcha: "false",
          _honey: hp ? hp.value : "", _replyto: v("email"),
          "Namn": v("name"), "email": v("email"), "Telefon": v("phone") || "–", "Gäller": occasionText(),
          "Datum": v("date") || tbd, "Plats": v("location") || tbd, "Meddelande": v("message"), "Språk på sidan": lang().toUpperCase()
        })
      }).then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          if (!r.ok || String(j.success) !== "true") throw new Error(j.message || ("HTTP " + r.status));
        });
      }).then(function () {
        form.hidden = true;
        var done = document.getElementById("enquiry-sent"); done.hidden = false; done.focus();
        done.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "nearest" });
      }).catch(failed).then(function () {
        btn.disabled = false; btn.removeAttribute("aria-busy"); btn.innerHTML = label;
      });
    });
  }
})();
