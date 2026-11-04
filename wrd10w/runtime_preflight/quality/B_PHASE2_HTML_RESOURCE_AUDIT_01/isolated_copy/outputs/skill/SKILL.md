---
name: html-anim-builder
description: 生成或验证解释性HTML动画时使用（物理/示意演示、题材与骨架分离）。产出自包含HTML并经Playwright实测。
---

# HTML 解释性动画制作

把「一个教学概念 → 一个可运行、经实测的解释性 HTML 动画」做成可复现流程。骨架（时序/控制/绘制基元）与题材代码（物理/数据/文案）严格分离；个案内容永远只进 config + topic 模块，不进骨架。

## 步骤

1. **分离题材与骨架。** 从真实任务中提取题材数据：参数（质量/系数等）、实体行为、中文文案、图例条目。判断哪些量随时间变化、哪些是常数。完成标准：能列出「题材数据表」，且表中没有任何一项属于通用动画机制。

2. **写 config.json + topic.js。** 放在技能目录之外（个案内容）。config 必需字段 `canvas:{width,height}`（正整数）、`title`（非空字符串）；可选 `lang`、`subtitle`、`physics`（任意对象，题材自定）、`arrowScale`、`legend:[{color,label,desc}]`。topic.js 必须定义：
   ```js
   window.TopicSim = { create(config, ctx, WRD) {
     // 返回 { step(dt), draw(ctx), hudValues():[{label,value}], reset() }
   }};
   ```
   可用骨架基元见 `assets/scaffold.js`：`WRD.setupCanvas`、`WRD.Loop`（rAF+固定步长，暂停/继续/重置）、`WRD.drawArrow`（带箭头与标签的力箭头）、`WRD.makeHUD`、`WRD.makeControls`（按钮+Space/R）。写法参考 `examples/ball_bounce/`（合成示例）。

3. **生成自包含 HTML。**
   ```
   python3 scripts/gen_animation.py --config CONFIG.json --topic TOPIC.js \
     --scaffold assets/scaffold.js --out OUT.html
   ```
   退出码：0 成功；2 config 缺失/非法/缺字段；3 topic 或 scaffold 缺失/无 TopicSim。完成标准：命令 exit 0 且打印生成路径。坏输入会明确报错且不产生输出文件。

4. **Playwright 实测（必须，不能只看文件存在）。**
   ```
   node scripts/verify_animation.mjs OUT.html --screenshot SHOT.png --out RESULT.json
   ```
   环境需有 playwright 且 `/usr/bin/chromium` 存在（launch args `--no-sandbox`）。全部检查为 true（无 console/页面错误、播放中画面内容变化、暂停后画面/时间冻结、继续恢复、重置后 HUD 时间归零且仍在播放）才算完成；`result.json` 为 false 时修题材或骨架后重跑，保留失败版本与修复版。可另加时间序列采样探针确认物理量有界/收敛、力与 HUD 数值一致。

5. **如实交付。** 生成结果与测试记录放技能目录外；报告写明模型为简化示意（如箭头最小可见长度、缩放假设），不声称精确仿真。

## 边界

- 骨架不含任何题材知识；发现自己在 `assets/scaffold.js` 里写物理名词即违背分离原则。
- 不虚构外部服务；验证只用本机 Chromium。
- 不因一次绿灯就宣称业务收益；`verify` 只证明「可运行、可交互、画面相关且无错」。
