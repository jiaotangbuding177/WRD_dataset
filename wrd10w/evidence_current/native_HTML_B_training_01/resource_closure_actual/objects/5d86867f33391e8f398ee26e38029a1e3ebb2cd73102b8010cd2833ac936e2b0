/* 落球弹跳 —— 技能自带的合成示例题材模块(演示用法,非真实业务源)。
 * 竖直一维运动: 重力持续作用; 触地后进入压缩阶段,以简化冲击力使速度反弹(能量损耗 restitution)。
 */
window.TopicSim = {
  create(cfg, ctx, WRD) {
    const P = cfg.physics;
    const W = cfg.canvas.width, H = cfg.canvas.height;
    const groundY = Math.round(H * 0.85);
    const pxPerM = P.pxPerM || 90;
    const r = 18;
    const scale = cfg.arrowScale || 0.2;
    const MIN_ARROW = 10;

    let s;
    function reset() {
      s = { t: 0, y: P.dropHeight, v: 0, compress: 0 };
    }
    reset();

    function step(dt) {
      s.t += dt;
      if (s.compress > 0) {
        // 触地压缩阶段(0.08s): 以地面冲击力把速度反弹为 -v*restitution
        s.compress -= dt;
        if (s.compress <= 0) s.v = -s.v * P.restitution;
        return;
      }
      s.v += P.g * dt; // 向下为正
      s.y += s.v * dt;
      if (s.y >= 0) {
        s.y = 0;
        s.compress = 0.08;
      }
    }

    function draw(c) {
      c.clearRect(0, 0, W, H);
      c.fillStyle = '#16263f';
      c.fillRect(0, 0, W, H);
      c.fillStyle = '#51708f';
      c.fillRect(0, groundY, W, H - groundY);
      const bx = Math.round(W * 0.4);
      const by = groundY - r + s.y * pxPerM;
      // 高度刻度(每米)
      c.strokeStyle = 'rgba(150,180,210,0.35)';
      c.font = '12px "Noto Sans CJK SC", sans-serif';
      c.fillStyle = '#8fa9c4';
      c.textAlign = 'left';
      for (let m = 0; m <= P.dropHeight + 1; m++) {
        const gy = groundY - m * pxPerM;
        c.beginPath(); c.moveTo(bx - 160, gy); c.lineTo(bx + 160, gy); c.stroke();
        c.fillText(m + ' m', bx + 166, gy + 4);
      }
      // 球
      c.fillStyle = '#f2b134';
      c.beginPath(); c.arc(bx, by, r, 0, Math.PI * 2); c.fill();
      // 力箭头
      const G = P.mass * P.g;
      WRD.drawArrow(c, bx - 8, by, bx - 8, by + Math.max(MIN_ARROW, G * scale),
        { color: '#9aa7bd', label: 'G' });
      if (s.compress > 0) {
        WRD.drawArrow(c, bx + 8, by, bx + 8, by - 70,
          { color: '#2a9d8f', label: 'N冲击' });
      }
      // 速度数值
      c.fillStyle = '#c6d4e8';
      c.font = '14px "Noto Sans CJK SC", sans-serif';
      c.fillText('v = ' + s.v.toFixed(2) + ' m/s（向下为正）', 16, 24);
    }

    function hudValues() {
      const impact = s.compress > 0;
      return [
        { label: '时间', value: s.t.toFixed(1) + ' s' },
        { label: '高度', value: Math.max(0, s.y).toFixed(2) + ' m' },
        { label: '速度', value: s.v.toFixed(2) + ' m/s' },
        { label: '重力', value: (P.mass * P.g).toFixed(1) + ' N' },
        { label: '地面冲击力', value: impact ? '作用中' : '0 N' }
      ];
    }

    return { step, draw, hudValues, reset };
  }
};
