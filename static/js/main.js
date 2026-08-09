// ---------- theme ----------
(function () {
  const root = document.documentElement;
  const saved = localStorage.getItem("kraken-theme");
  if (saved) root.setAttribute("data-theme", saved);

  const btn = document.getElementById("theme-toggle");
  btn.addEventListener("click", () => {
    const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    localStorage.setItem("kraken-theme", next);
  });
})();

// ---------- 3D tilt ----------
function attachTilt(el, strength = 10) {
  el.addEventListener("mousemove", (e) => {
    const r = el.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - 0.5;
    const y = (e.clientY - r.top) / r.height - 0.5;
    el.style.transform = `rotateY(${x * strength}deg) rotateX(${-y * strength}deg) translateZ(0)`;
  });
  el.addEventListener("mouseleave", () => {
    el.style.transform = "rotateY(0deg) rotateX(0deg)";
  });
}
document.querySelectorAll(".tilt-card").forEach((el) => attachTilt(el, 6));

const emblem = document.getElementById("tilt-emblem");
if (emblem) attachTilt(emblem, 16);

// ---------- ambient abyss particles ----------
(function () {
  const canvas = document.getElementById("abyss");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  let w, h, particles;

  function resize() {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
  }
  window.addEventListener("resize", resize);
  resize();

  function isLight() {
    return document.documentElement.getAttribute("data-theme") === "light";
  }

  const COUNT = Math.min(70, Math.floor((window.innerWidth * window.innerHeight) / 22000));
  particles = Array.from({ length: COUNT }, () => ({
    x: Math.random() * w,
    y: Math.random() * h,
    r: Math.random() * 1.6 + 0.4,
    vy: Math.random() * 0.25 + 0.05,
    vx: (Math.random() - 0.5) * 0.15,
    a: Math.random() * 0.5 + 0.15,
  }));

  function tick() {
    ctx.clearRect(0, 0, w, h);
    const color = isLight() ? "13,13,15" : "155,92,255";
    for (const p of particles) {
      p.y -= p.vy;
      p.x += p.vx;
      if (p.y < -10) p.y = h + 10;
      if (p.x < -10) p.x = w + 10;
      if (p.x > w + 10) p.x = -10;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${color},${p.a})`;
      ctx.fill();
    }
    requestAnimationFrame(tick);
  }
  tick();
})();
