/* 溜冰作用力 —— 题材模块(个案数据/物理,非复用资源)。
 * 契约: TopicSim.create(config, ctx, WRD) -> {step, draw, hudValues, reset}
 * 简化模型: 一维水平运动; 蹬冰推力周期性作用并随速度接近上限衰减;
 * 冰面摩擦(mu*mg)与空气阻力(dragK*v^2)始终与运动方向相反。
 */
window.TopicSim = {
  create(cfg, ctx, WRD) {
    const P = cfg.physics;
    const W = cfg.canvas.width;
    const H = cfg.canvas.height;
    const groundY = Math.round(H * 0.62);
    const pxPerM = 26;
    const skaterScreenX = Math.round(W * 0.3);
    const scale = cfg.arrowScale || 0.15;
    const MIN_ARROW = 10; // 过小的力放大到最小可见长度(像素)

    let s;
    function reset() {
      s = { t: 0, x: 0, v: 0, pushT: 0, pushing: true }; // 开局即处于蹬冰段
    }
    reset();

    function forces(v) {
      const push = s.pushing ? P.thrust * Math.max(0, 1 - v / P.vCap) : 0;
      const moving = Math.abs(v) > 1e-4;
      const fr = moving ? P.mu * P.mass * P.g : 0;
      const drag = P.dragK * v * v;
      return { push, fr, drag };
    }

    function step(dt) {
      s.t += dt;
      s.pushT += dt;
      if (s.pushT >= P.strokeInterval) {
        s.pushT = 0;
        s.pushing = true;
      }
      if (s.pushing && s.pushT >= P.strokeDuration) s.pushing = false;
      const f = forces(s.v);
      const dir = s.v >= 0 ? 1 : -1;
      const net = f.push - dir * f.fr - dir * f.drag;
      s.v += (net / P.mass) * dt;
      if (Math.abs(s.v) < 2e-3 && f.push === 0) s.v = 0;
      s.x += s.v * dt;
    }

    function skater(c, sx, sy, pushing) {
      // 简笔画滑冰者: 头/躯干/双腿呈蹬冰-滑行姿态
      const lean = pushing ? 0.22 : 0.08; // 前倾弧度
      const hipY = sy - 46;
      const headY = sy - 78;
      c.save();
      c.strokeStyle = '#eaf2ff';
      c.fillStyle = '#eaf2ff';
      c.lineWidth = 4;
      c.lineCap = 'round';
      // 双腿: 前腿伸向运动方向, 后腿蹬冰时向后伸展
      const legSpread = pushing ? 30 : 16;
      c.beginPath();
      c.moveTo(sx, hipY); c.lineTo(sx + legSpread, sy - 4); c.lineTo(sx + legSpread + 8, sy); // 前腿+冰刀
      c.moveTo(sx, hipY); c.lineTo(sx - legSpread * 0.7, sy - 4); c.lineTo(sx - legSpread * 0.7 + 8, sy); // 后腿
      c.stroke();
      // 躯干
      c.beginPath();
      c.moveTo(sx, hipY);
      c.lineTo(sx + Math.sin(lean) * 34, headY + 8);
      c.stroke();
      // 手臂
      c.beginPath();
      c.moveTo(sx + Math.sin(lean) * 18, hipY - 16);
      c.lineTo(sx + Math.sin(lean) * 18 + 22, hipY - 2);
      c.stroke();
      // 头
      c.beginPath();
      c.arc(sx + Math.sin(lean) * 36, headY, 9, 0, Math.PI * 2);
      c.fill();
      c.restore();
    }

    function draw(c) {
      const f = forces(s.v);
      const camX = s.x * pxPerM - skaterScreenX;
      // 天空与冰面
      const sky = c.createLinearGradient(0, 0, 0, groundY);
      sky.addColorStop(0, '#12233f');
      sky.addColorStop(1, '#24466f');
      c.fillStyle = sky;
      c.fillRect(0, 0, W, groundY);
      c.fillStyle = '#bfe3f5';
      c.fillRect(0, groundY, W, H - groundY);
      c.fillStyle = '#e9f7fd';
      c.fillRect(0, groundY, W, 6);
      // 滚动的冰面刻痕(每2米)
      c.strokeStyle = 'rgba(90,140,170,0.5)';
      c.lineWidth = 2;
      const first = Math.floor(camX / (2 * pxPerM));
      for (let k = first; k <= first + W / (2 * pxPerM) + 1; k++) {
        const sx = k * 2 * pxPerM - camX;
        c.beginPath();
        c.moveTo(sx, groundY + 14);
        c.lineTo(sx - 8, groundY + 30);
        c.stroke();
      }
      const sx = skaterScreenX;
      const sy = groundY - 4;
      skater(c, sx, sy, s.pushing);
      // 受力箭头(从躯干中心发出)
      const bx = sx + 6, by = sy - 58;
      const G = P.mass * P.g;
      // 重力(向下) 与 支持力(向上), 稍错开避免完全重叠
      WRD.drawArrow(c, bx - 8, by, bx - 8, by + Math.max(MIN_ARROW, G * scale),
        { color: '#9aa7bd', label: 'G' });
      WRD.drawArrow(c, bx + 8, by, bx + 8, by - Math.max(MIN_ARROW, G * scale),
        { color: '#2a9d8f', label: 'N' });
      if (f.push > 0) {
        WRD.drawArrow(c, bx + 14, by, bx + 14 + Math.max(MIN_ARROW, f.push * scale), by,
          { color: '#e63946', label: 'F蹬' });
      }
      if (Math.abs(s.v) > 1e-3) {
        const dir = s.v >= 0 ? -1 : 1;
        WRD.drawArrow(c, bx - 14, by, bx - 14 + dir * Math.max(MIN_ARROW, f.fr * scale), by,
          { color: '#f4a261', label: 'f' });
        WRD.drawArrow(c, bx - 2, by + 26, bx - 2 + dir * Math.max(MIN_ARROW, f.drag * scale), by + 26,
          { color: '#8d99ae', label: '风阻' });
      }
      // 速度计: 底部横条
      const vMax = P.vCap * 1.2;
      const barW = 240, barX = W - barW - 28, barY = H - 34;
      c.fillStyle = 'rgba(8,15,28,0.55)';
      c.fillRect(barX, barY, barW, 12);
      c.fillStyle = '#6ec1ff';
      c.fillRect(barX, barY, barW * Math.min(1, Math.abs(s.v) / vMax), 12);
      c.fillStyle = '#c6d4e8';
      c.font = '13px "Noto Sans CJK SC", sans-serif';
      c.textAlign = 'right';
      c.fillText('速度 ' + Math.abs(s.v).toFixed(1) + ' m/s', barX + barW, barY - 6);
    }

    function hudValues() {
      const f = forces(s.v);
      return [
        { label: '时间', value: s.t.toFixed(1) + ' s' },
        { label: '速度', value: s.v.toFixed(2) + ' m/s' },
        { label: '滑行距离', value: s.x.toFixed(1) + ' m' },
        { label: '蹬冰推力', value: f.push.toFixed(0) + ' N' },
        { label: '摩擦力', value: f.fr.toFixed(1) + ' N' },
        { label: '空气阻力', value: f.drag.toFixed(1) + ' N' },
        { label: '状态', value: s.pushing ? '蹬冰' : '滑行' }
      ];
    }

    return { step, draw, hudValues, reset };
  }
};
