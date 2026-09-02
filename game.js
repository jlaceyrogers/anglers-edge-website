/* Anglers Edge — "Out-fish the model" hero.
 * A procedurally generated lake basin rendered in the app's chart-paper
 * style, a lure that follows the pointer, three casts scored by a small
 * version of the app's model, then the model's own top spots revealed. */
(function () {
  'use strict';
  var host = document.getElementById('lake');
  if (!host || !window.THREE) return;
  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------------- procedural bathymetry ---------------- */
  var N = 128, SIZE = 120;
  function hash(x, y) { var s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453; return s - Math.floor(s); }
  function vnoise(x, y) {
    var xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
    var u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
    var a = hash(xi, yi), b = hash(xi + 1, yi), c = hash(xi, yi + 1), d = hash(xi + 1, yi + 1);
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
  }
  function fbm(x, y) { var f = 0, a = 0.5, s = 1; for (var i = 0; i < 4; i++) { f += a * vnoise(x * s, y * s); a *= 0.5; s *= 2.1; } return f; }
  var HUMPS = [[0.36, 0.42, 0.09, 7], [0.62, 0.58, 0.07, 6], [0.55, 0.30, 0.06, 5]];
  var depth = new Float32Array(N * N);
  var shoreR = function (ang) { return 0.36 + 0.09 * Math.sin(ang * 2 + 0.6) + 0.05 * Math.sin(ang * 5 + 2.0) + 0.03 * Math.sin(ang * 3 - 1.0); };
  for (var j = 0; j < N; j++) for (var i = 0; i < N; i++) {
    var u = i / (N - 1), v = j / (N - 1), dx = u - 0.5, dy = v - 0.52;
    var r = Math.sqrt(dx * dx + dy * dy), ang = Math.atan2(dy, dx);
    var edge = shoreR(ang);
    var t = 1 - r / edge;                      // 1 centre, 0 shoreline
    var d = -1;
    if (t > 0) {
      d = Math.pow(t, 0.75) * (14 + 10 * fbm(u * 3.1 + 5, v * 3.1 + 9));
      HUMPS.forEach(function (h) {
        var hx = u - h[0], hy = v - h[1];
        d -= h[3] * Math.exp(-(hx * hx + hy * hy) / (h[2] * h[2] * 0.5));
      });
      d = Math.max(d, 0.4);
    }
    depth[j * N + i] = d;
  }
  function depthAt(i, j) { i = Math.max(0, Math.min(N - 1, i)); j = Math.max(0, Math.min(N - 1, j)); return depth[j * N + i]; }
  function slopeAt(i, j) {
    var a = depthAt(i + 1, j), b = depthAt(i - 1, j), c = depthAt(i, j + 1), e = depthAt(i, j - 1);
    if (a < 0 || b < 0 || c < 0 || e < 0) return 0;
    return Math.sqrt((a - b) * (a - b) + (c - e) * (c - e)) / 2;
  }
  /* the model: smallmouth, summer — depth band, break proximity, hump */
  function trap(x, a, b, c, d) { if (x <= a || x >= d) return 0; if (x < b) return (x - a) / (b - a); if (x <= c) return 1; return (d - x) / (d - c); }
  function scoreAt(i, j) {
    var d = depthAt(i, j); if (d < 0) return null;
    var band = trap(d, 2, 4, 12, 15);
    var sl = Math.min(1, slopeAt(i, j) / 1.6);
    var hump = 0; HUMPS.forEach(function (h) { var hx = i / (N - 1) - h[0], hy = j / (N - 1) - h[1]; hump = Math.max(hump, Math.exp(-(hx * hx + hy * hy) / (h[2] * h[2] * 1.2))); });
    var s = 0.45 * band + 0.30 * sl + 0.25 * hump;
    return { score: s, depth: d, band: band, slope: sl, hump: hump };
  }
  var top = [];
  for (var jj = 4; jj < N - 4; jj += 2) for (var ii = 4; ii < N - 4; ii += 2) {
    var sc = scoreAt(ii, jj); if (!sc) continue;
    var best = true;
    for (var b2 = -4; b2 <= 4 && best; b2 += 2) for (var a2 = -4; a2 <= 4; a2 += 2) { var o = scoreAt(ii + a2, jj + b2); if (o && o.score > sc.score) { best = false; break; } }
    if (best) top.push({ i: ii, j: jj, s: sc.score, d: sc.depth });
  }
  top.sort(function (a, b) { return b.s - a.s; });
  var picks = [];
  top.forEach(function (t) { if (picks.length >= 5) return; if (picks.every(function (p) { return Math.hypot(p.i - t.i, p.j - t.j) > 14; })) picks.push(t); });

  /* ---------------- three.js scene ---------------- */
  var scene = new THREE.Scene();
  var cam = new THREE.PerspectiveCamera(38, 1, 1, 500);
  var renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  host.appendChild(renderer.domElement);

  var tex = new THREE.DataTexture(depth, N, N, THREE.RedFormat, THREE.FloatType);
  tex.needsUpdate = true; tex.minFilter = THREE.LinearFilter; tex.magFilter = THREE.LinearFilter;

  var basinMat = new THREE.ShaderMaterial({
    uniforms: { uDepth: { value: tex }, uTime: { value: 0 } },
    vertexShader: [
      'uniform sampler2D uDepth; varying float vD; varying vec2 vUv;',
      'void main(){ vUv = uv; float d = texture2D(uDepth, uv).r; vD = d;',
      '  vec3 p = position; p.z = d > 0.0 ? -d * 0.9 : 0.6;',
      '  gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0); }'].join('\n'),
    fragmentShader: [
      'varying float vD; varying vec2 vUv;',
      'void main(){',
      '  vec3 paper = vec3(0.969,0.949,0.902); vec3 ink = vec3(0.133,0.188,0.122);',
      '  if (vD < 0.0) {',
      '    float h = step(0.5, fract((vUv.x + vUv.y) * 90.0));',
      '    gl_FragColor = vec4(mix(paper, paper * 0.94, h * 0.5), 1.0); return; }',
      '  vec3 shallow = vec3(0.82,0.88,0.92); vec3 mid = vec3(0.42,0.62,0.78); vec3 deep = vec3(0.09,0.33,0.52);',
      '  float t = clamp(vD / 24.0, 0.0, 1.0);',
      '  vec3 col = t < 0.4 ? mix(shallow, mid, t / 0.4) : mix(mid, deep, (t - 0.4) / 0.6);',
      '  float f = fract(vD * 0.5); float l = 1.0 - smoothstep(0.0, 0.10, min(f, 1.0 - f));',
      '  col = mix(col, ink, l * 0.22);',
      '  float shore = 1.0 - smoothstep(0.0, 1.2, vD); col = mix(col, paper, shore * 0.5);',
      '  gl_FragColor = vec4(col, 1.0); }'].join('\n')
  });
  var basin = new THREE.Mesh(new THREE.PlaneGeometry(SIZE, SIZE, N - 1, N - 1), basinMat);
  basin.rotation.x = -Math.PI / 2; scene.add(basin);

  var waterMat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false,
    uniforms: { uTime: { value: 0 } },
    vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
    fragmentShader: [
      'uniform float uTime; varying vec2 vUv;',
      'void main(){ float w = sin(vUv.x*40.0 + uTime*0.6) * sin(vUv.y*34.0 - uTime*0.5);',
      '  float g = smoothstep(0.75, 1.0, w);',
      '  gl_FragColor = vec4(1.0, 1.0, 0.98, 0.05 + g * 0.10); }'].join('\n')
  });
  var water = new THREE.Mesh(new THREE.PlaneGeometry(SIZE, SIZE), waterMat);
  water.rotation.x = -Math.PI / 2; water.position.y = 0.15; scene.add(water);

  function toWorld(i, j) { return new THREE.Vector3((i / (N - 1) - 0.5) * SIZE, 0, (j / (N - 1) - 0.5) * SIZE); }
  function toCell(p) { return { i: Math.round((p.x / SIZE + 0.5) * (N - 1)), j: Math.round((p.z / SIZE + 0.5) * (N - 1)) }; }

  /* sprites drawn on canvas */
  function canvasSprite(draw, size, scale) {
    var c = document.createElement('canvas'); c.width = c.height = size;
    draw(c.getContext('2d'), size);
    var t = new THREE.CanvasTexture(c); t.minFilter = THREE.LinearFilter;
    var sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, transparent: true, depthTest: false }));
    sp.scale.set(scale, scale, 1); return sp;
  }
  function coin(n, colour) {
    return canvasSprite(function (g, s) {
      g.translate(s / 2, s / 2 - s * 0.06);
      g.beginPath(); g.arc(0, 0, s * 0.3, 0, Math.PI * 2); g.fillStyle = colour; g.fill();
      g.lineWidth = s * 0.05; g.strokeStyle = '#F7F2E6'; g.stroke();
      g.beginPath(); g.moveTo(-s * 0.2, s * 0.22); g.lineTo(s * 0.02, s * 0.44); g.lineTo(s * 0.2, s * 0.22); g.closePath();
      g.fillStyle = colour; g.fill();
      g.fillStyle = '#FDF9EE'; g.font = 'bold ' + (s * 0.3) + 'px Georgia, serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText(String(n), 0, s * 0.02);
    }, 128, 7);
  }
  var coins = picks.map(function (p, k) {
    var sp = coin(k + 1, k < 2 ? '#217A4B' : '#C08A12');
    var w = toWorld(p.i, p.j); sp.position.set(w.x, 3.2, w.z); sp.visible = false; scene.add(sp); return sp;
  });
  var fish = canvasSprite(function (g, s) {
    g.fillStyle = '#F7F2E6'; g.beginPath();
    g.moveTo(s * 0.1, s * 0.5); g.quadraticCurveTo(s * 0.35, s * 0.2, s * 0.62, s * 0.4);
    g.lineTo(s * 0.88, s * 0.28); g.lineTo(s * 0.82, s * 0.5); g.lineTo(s * 0.88, s * 0.72);
    g.lineTo(s * 0.62, s * 0.6); g.quadraticCurveTo(s * 0.35, s * 0.8, s * 0.1, s * 0.5); g.fill();
    g.fillStyle = '#D9480F'; g.beginPath(); g.arc(s * 0.24, s * 0.46, s * 0.035, 0, Math.PI * 2); g.fill();
  }, 128, 9);
  fish.visible = false; scene.add(fish);

  var lure = new THREE.Mesh(new THREE.SphereGeometry(0.9, 16, 16), new THREE.MeshBasicMaterial({ color: 0xD9480F }));
  lure.position.set(0, 0.6, 0); scene.add(lure);
  var lineGeo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 60, 0), new THREE.Vector3(0, 0.6, 0)]);
  var line = new THREE.Line(lineGeo, new THREE.LineBasicMaterial({ color: 0x22301F, transparent: true, opacity: 0.35 }));
  scene.add(line);
  var ring = new THREE.Mesh(new THREE.RingGeometry(0.9, 1.1, 48), new THREE.MeshBasicMaterial({ color: 0xF7F2E6, transparent: true, opacity: 0, side: THREE.DoubleSide, depthTest: false }));
  ring.rotation.x = -Math.PI / 2; ring.position.y = 0.3; scene.add(ring);

  /* ---------------- game state ---------------- */
  var card = document.getElementById('cast-card'), castsEl = document.getElementById('casts-left'),
      totalEl = document.getElementById('your-score'), reveal = document.getElementById('reveal'),
      resetBtn = document.getElementById('reset-game');
  var casts = 3, total = 0, ringT = -1, fishT = -1, fishFrom = new THREE.Vector3(), fishTo = new THREE.Vector3();
  var modelBest = picks.slice(0, 3).reduce(function (a, p) { return a + p.s; }, 0);

  function rating(s) { return s >= 0.70 ? 'Excellent' : s >= 0.58 ? 'Good' : s >= 0.35 ? 'Fair' : 'Poor'; }
  function reason(sc) {
    var bits = [];
    bits.push(sc.depth.toFixed(1) + ' m');
    if (sc.hump > 0.55) bits.push('on a hump'); else if (sc.hump > 0.25) bits.push('near a hump');
    if (sc.slope > 0.6) bits.push('right on a break'); else if (sc.slope > 0.3) bits.push('near a break');
    if (sc.band < 0.3) bits.push(sc.depth < 4 ? 'too shallow for summer smallmouth' : 'deeper than they hold in summer');
    else if (sc.band === 1) bits.push('in the depth band');
    return bits.join(' · ');
  }
  function cast(p) {
    if (casts <= 0) return;
    var c = toCell(p), sc = scoreAt(c.i, c.j);
    if (!sc) { showCard('That\'s dry land. Try the water.', '', 'poor'); return; }
    casts--; total += sc.score;
    castsEl.textContent = casts; totalEl.textContent = total.toFixed(2);
    ring.position.set(p.x, 0.3, p.z); ring.scale.set(1, 1, 1); ringT = 0;
    var r = rating(sc.score);
    showCard(sc.score.toFixed(2) + ' · ' + r, reason(sc), r.toLowerCase());
    if (sc.score >= 0.5) {
      var w = picks[Math.floor(Math.random() * picks.length)];
      fishFrom.copy(toWorld(w.i, w.j)); fishFrom.y = -6;
      fishTo.set(p.x, -0.5, p.z); fishT = 0; fish.visible = true;
    }
    if (casts === 0) setTimeout(revealModel, 1400);
  }
  function showCard(title, sub, cls) {
    card.className = 'cast-card show ' + cls;
    card.querySelector('.cc-title').textContent = title;
    card.querySelector('.cc-sub').textContent = sub;
  }
  function revealModel() {
    coins.forEach(function (c) { c.visible = true; });
    reveal.querySelector('.rv-you b').textContent = total.toFixed(2);
    reveal.querySelector('.rv-model b').textContent = modelBest.toFixed(2);
    reveal.querySelector('.rv-verdict').textContent = total >= modelBest * 0.9
      ? 'You read this lake like a pro. Most people don\'t — that\'s the point of the app.'
      : 'The model found ' + (modelBest - total).toFixed(2) + ' more score in three casts — and it can tell you why for every one of them.';
    reveal.classList.add('show');
  }
  resetBtn.addEventListener('click', function () {
    casts = 3; total = 0; castsEl.textContent = 3; totalEl.textContent = '0.00';
    coins.forEach(function (c) { c.visible = false; }); reveal.classList.remove('show');
    card.className = 'cast-card';
  });

  /* ---------------- pointer ---------------- */
  var ray = new THREE.Raycaster(), ndc = new THREE.Vector2(), plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0), hit = new THREE.Vector3();
  var down = null;
  function toNDC(e) { var r = host.getBoundingClientRect(); ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1); }
  function project() { ray.setFromCamera(ndc, cam); return ray.ray.intersectPlane(plane, hit) ? hit : null; }
  host.addEventListener('pointermove', function (e) {
    toNDC(e); var p = project(); if (!p) return;
    var lim = SIZE * 0.49; p.x = Math.max(-lim, Math.min(lim, p.x)); p.z = Math.max(-lim, Math.min(lim, p.z));
    lure.position.set(p.x, 0.6, p.z);
    var pos = lineGeo.attributes.position; pos.setXYZ(0, p.x, 60, p.z); pos.setXYZ(1, p.x, 0.6, p.z); pos.needsUpdate = true;
  });
  host.addEventListener('pointerdown', function (e) { down = [e.clientX, e.clientY]; });
  host.addEventListener('pointerup', function (e) {
    if (!down) return; var moved = Math.hypot(e.clientX - down[0], e.clientY - down[1]); down = null;
    if (moved > 8) return;                     // a scroll or drag, not a cast
    toNDC(e); var p = project(); if (p) cast(p.clone());
  });

  /* ---------------- loop ---------------- */
  function resize() {
    var w = host.clientWidth, h = host.clientHeight;
    renderer.setSize(w, h, false); cam.aspect = w / h; cam.updateProjectionMatrix();
    var portrait = h > w;
    cam.position.set(0, portrait ? 118 : 78, portrait ? 92 : 74);
    cam.lookAt(0, -4, 0);
  }
  window.addEventListener('resize', resize); resize();
  var t0 = performance.now();
  function frame(now) {
    var t = (now - t0) / 1000;
    basinMat.uniforms.uTime.value = t; waterMat.uniforms.uTime.value = t;
    if (!reduced) { var a = Math.sin(t * 0.12) * 0.06; cam.position.x = Math.sin(a) * 78; cam.lookAt(0, -4, 0); }
    if (ringT >= 0) { ringT += 0.016; var s = 1 + ringT * 10; ring.scale.set(s, s, 1); ring.material.opacity = Math.max(0, 0.8 - ringT * 0.7); if (ringT > 1.2) ringT = -1; }
    if (fishT >= 0) {
      fishT += 0.012; var k = Math.min(1, fishT), e = k * k * (3 - 2 * k);
      fish.position.lerpVectors(fishFrom, fishTo, e); fish.position.y = -6 + e * 6.4 + Math.sin(k * 12) * 0.4;
      fish.material.rotation = Math.sin(k * 14) * 0.25;
      if (fishT > 1.9) { fishT = -1; fish.visible = false; ring.position.copy(fishTo); ring.position.y = 0.3; ringT = 0; }
    }
    coins.forEach(function (c, i) { if (c.visible) c.position.y = 3.2 + Math.sin(t * 2 + i) * 0.3; });
    renderer.render(scene, cam);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
  host.classList.add('ready');
})();
