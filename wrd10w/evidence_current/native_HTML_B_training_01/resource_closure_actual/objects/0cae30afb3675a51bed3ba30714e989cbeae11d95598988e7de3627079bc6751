/* wrd-anim scaffold v1 —— 可复用的时序/状态/绘制基元。
 * 只关心:画布尺寸、帧循环(暂停/继续/重置)、力箭头、HUD、控制条。
 * 不含任何具体题材(物理/领域)知识;题材代码在 topic 模块中。
 * 契约: window.TopicSim.create(config, ctx, WRD) -> {step(dt), draw(ctx), hudValues(), reset()}
 */
(function (global) {
  'use strict';

  const WRD = { frames: 0 };

  WRD.setupCanvas = function (canvas, width, height) {
    if (!canvas || !(width > 0) || !(height > 0)) {
      throw new Error('WRD.setupCanvas: 需要canvas元素与正的width/height');
    }
    const dpr = global.devicePixelRatio || 1;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    canvas.style.width = width + 'px';
    canvas.style.height = height + 'px';
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return ctx;
  };

  class Loop {
    constructor({ stepDt, step, draw, hud } = {}) {
      if (typeof step !== 'function' || typeof draw !== 'function') {
        throw new Error('WRD.Loop 需要 step(dt) 与 draw() 两个回调');
      }
      this.stepDt = stepDt || 1 / 120;
      this.step = step;
      this.draw = draw;
      this.hud = hud || null;
      this.onReset = null;
      this.playing = false;
      this._acc = 0;
      this._last = null;
      this._raf = null;
      this._tick = this._tick.bind(this);
    }
    start() {
      this.playing = true;
      if (!this._raf) this._raf = global.requestAnimationFrame(this._tick);
    }
    pause() { this.playing = false; }
    toggle() { if (this.playing) { this.pause(); } else { this.start(); } }
    reset() {
      this._acc = 0;
      if (this.onReset) this.onReset();
      if (!this._raf) this._raf = global.requestAnimationFrame(this._tick);
    }
    _tick(now) {
      this._raf = global.requestAnimationFrame(this._tick);
      if (this.playing) {
        if (this._last === null) this._last = now;
        this._acc += Math.min((now - this._last) / 1000, 0.25);
        this._last = now;
        while (this._acc >= this.stepDt) {
          this.step(this.stepDt);
          this._acc -= this.stepDt;
        }
      } else {
        this._last = now;
      }
      this.draw();
      if (this.hud) this.hud();
      WRD.frames++;
    }
  }
  WRD.Loop = Loop;

  /* 从(x1,y1)到(x2,y2)画带箭头线,可带文字标签;opts: color,width,headLen,label,labelFont */
  WRD.drawArrow = function (ctx, x1, y1, x2, y2, opts = {}) {
    const color = opts.color || '#e63946';
    const width = opts.width || 3;
    const dx = x2 - x1, dy = y2 - y1;
    const len = Math.hypot(dx, dy);
    if (!(len >= 1)) return;
    const ux = dx / len, uy = dy / len;
    const head = Math.min(opts.headLen || 10, len * 0.5);
    ctx.save();
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = width;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2 - ux * head, y2 - uy * head);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x2, y2);
    ctx.lineTo(x2 - ux * head - uy * head * 0.45, y2 - uy * head + ux * head * 0.45);
    ctx.lineTo(x2 - ux * head + uy * head * 0.45, y2 - uy * head - ux * head * 0.45);
    ctx.closePath();
    ctx.fill();
    if (opts.label) {
      ctx.font = opts.labelFont || '14px "Noto Sans CJK SC", sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      const pad = 13;
      ctx.fillText(opts.label, x2 + ux * pad, y2 + uy * pad);
    }
    ctx.restore();
  };

  /* HUD:返回 {set(items)};items=[{label,value}] 仅显示已出现过的行 */
  WRD.makeHUD = function (container) {
    const el = global.document.createElement('div');
    el.className = 'wrd-hud';
    container.appendChild(el);
    const valueEls = new Map();
    return {
      set(items) {
        if (!Array.isArray(items)) return;
        for (const it of items) {
          let v = valueEls.get(it.label);
          if (!v) {
            const row = global.document.createElement('div');
            row.className = 'wrd-hud-row';
            const l = global.document.createElement('span');
            l.className = 'wrd-hud-label';
            l.textContent = it.label;
            v = global.document.createElement('span');
            v.className = 'wrd-hud-value';
            row.appendChild(l);
            row.appendChild(v);
            el.appendChild(row);
            valueEls.set(it.label, v);
          }
          v.textContent = String(it.value);
        }
      }
    };
  };

  /* 控制条:暂停/继续 + 重置,并绑定 Space/R 键 */
  WRD.makeControls = function (container, loop, opts = {}) {
    if (!loop || typeof loop.toggle !== 'function') {
      throw new Error('WRD.makeControls 需要一个 WRD.Loop 实例');
    }
    const labels = Object.assign(
      { pause: '暂停', resume: '继续', reset: '重置' }, opts.labels || {});
    const bar = global.document.createElement('div');
    bar.className = 'wrd-controls';
    const toggleBtn = global.document.createElement('button');
    toggleBtn.className = 'wrd-btn-toggle';
    const resetBtn = global.document.createElement('button');
    resetBtn.className = 'wrd-btn-reset';
    const syncToggle = () => {
      toggleBtn.textContent = loop.playing ? labels.pause : labels.resume;
    };
    toggleBtn.addEventListener('click', () => { loop.toggle(); syncToggle(); });
    resetBtn.textContent = labels.reset;
    resetBtn.addEventListener('click', () => { loop.reset(); syncToggle(); });
    bar.appendChild(toggleBtn);
    bar.appendChild(resetBtn);
    container.appendChild(bar);
    global.document.addEventListener('keydown', (ev) => {
      if (ev.code === 'Space') { ev.preventDefault(); loop.toggle(); syncToggle(); }
      else if (ev.code === 'KeyR') { loop.reset(); syncToggle(); }
    });
    return { toggleBtn, resetBtn };
  };

  global.WRD = WRD;
})(window);
