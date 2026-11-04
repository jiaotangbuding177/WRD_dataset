#!/usr/bin/env python3
"""gen_animation.py —— 把 config(JSON 数据) + topic.js(题材代码) + scaffold.js
组装成一个自包含的可运行解释性 HTML 动画。

用法:
  python gen_animation.py --config CONFIG.json --topic TOPIC.js --out OUT.html

config 必需字段: canvas{width,height}(正整数), title(str)
config 可选字段: lang, subtitle, physics(任意对象,交给topic), arrowScale, legend[{color,label,desc}]
退出码: 0 成功; 2 配置文件缺失/非法JSON/缺必需字段; 3 topic模块缺少 TopicSim
"""
import argparse
import json
import sys
from pathlib import Path


def fail(code: int, msg: str) -> None:
    print(f"gen_animation: 错误: {msg}", file=sys.stderr)
    sys.exit(code)


def validate(cfg: dict) -> None:
    canvas = cfg.get("canvas")
    if not isinstance(canvas, dict):
        fail(2, "config 缺少必需字段 canvas(对象)")
    for key in ("width", "height"):
        v = canvas.get(key)
        if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
            fail(2, f"config canvas.{key} 必须是正整数, 实际: {v!r}")
    if not isinstance(cfg.get("title"), str) or not cfg["title"].strip():
        fail(2, 'config 缺少必需字段 title(非空字符串)')
    legend = cfg.get("legend", [])
    if not isinstance(legend, list):
        fail(2, "config.legend 必须是数组")
    for i, item in enumerate(legend):
        if not isinstance(item, dict) or not all(
            isinstance(item.get(k), str) for k in ("color", "label", "desc")
        ):
            fail(2, f"config.legend[{i}] 需要 {{color,label,desc}} 三个字符串字段")


def js_str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


STYLE = """
body{font-family:"Noto Sans CJK SC","Noto Sans SC",sans-serif;background:#0f1b2d;color:#e8eef7;margin:0;padding:24px}
h1{font-size:22px;margin:0 0 6px}
.wrd-subtitle{margin:0 0 16px;color:#a9bcd6;font-size:14px}
.wrd-stage{position:relative;display:inline-block}
.wrd-hud{position:absolute;top:12px;left:12px;background:rgba(8,15,28,.75);border-radius:8px;padding:10px 14px;font-size:14px;line-height:1.7;pointer-events:none}
.wrd-hud-row{display:flex;gap:14px;justify-content:space-between;min-width:190px}
.wrd-hud-label{color:#a9bcd6}
.wrd-hud-value{font-variant-numeric:tabular-nums}
.wrd-controls{margin-top:12px;display:flex;gap:10px}
.wrd-controls button{font:inherit;padding:6px 18px;border-radius:6px;border:1px solid #3b537a;background:#1b2c49;color:#e8eef7;cursor:pointer}
.wrd-controls button:hover{background:#274067}
.wrd-legend{margin-top:14px;display:flex;flex-wrap:wrap;gap:8px 24px;font-size:13px;color:#c6d4e8;max-width:960px}
.wrd-legend .chip{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.wrd-error{color:#ff9c9c;font-size:15px;white-space:pre-wrap;margin-top:16px}
"""

BOOT = """
(function boot() {
  function showError(msg) {
    var d = document.createElement('div');
    d.className = 'wrd-error';
    d.textContent = '启动失败: ' + msg;
    document.body.appendChild(d);
  }
  try {
    var cfg = __WRD_CONFIG__;
    var canvas = document.getElementById('wrd-canvas');
    var stage = document.getElementById('wrd-stage');
    if (!window.TopicSim || typeof window.TopicSim.create !== 'function') {
      throw new Error('topic 模块未定义 window.TopicSim.create(config, ctx, WRD)');
    }
    var ctx = WRD.setupCanvas(canvas, cfg.canvas.width, cfg.canvas.height);
    var sim = window.TopicSim.create(cfg, ctx, WRD);
    var loop = new WRD.Loop({
      step: function (dt) { sim.step(dt); },
      draw: function () { sim.draw(ctx); },
      hud: function () { hud.set(sim.hudValues()); }
    });
    var hud = WRD.makeHUD(stage);
    loop.onReset = function () { sim.reset(); };
    WRD.makeControls(stage, loop, { onReset: function () {} });
    hud.set(sim.hudValues());
    loop.start();
  } catch (err) {
    showError(err && err.message ? err.message : String(err));
  }
})();
"""


def main() -> None:
    ap = argparse.ArgumentParser(description="组装自包含的解释性HTML动画")
    ap.add_argument("--config", required=True)
    ap.add_argument("--topic", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--scaffold", required=True, help="scaffold.js 路径")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.is_file():
        fail(2, f"config 文件不存在: {cfg_path}")
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(2, f"config 不是合法JSON: {e}")
    if not isinstance(cfg, dict):
        fail(2, "config 顶层必须是JSON对象")
    validate(cfg)

    topic_path = Path(args.topic)
    if not topic_path.is_file():
        fail(3, f"topic 文件不存在: {topic_path}")
    topic_src = topic_path.read_text(encoding="utf-8")
    if "TopicSim" not in topic_src:
        fail(3, "topic 模块必须定义 window.TopicSim.create(...)")
    scaffold_path = Path(args.scaffold)
    if not scaffold_path.is_file():
        fail(3, f"scaffold 文件不存在: {scaffold_path}")
    scaffold_src = scaffold_path.read_text(encoding="utf-8")

    legend_html = "".join(
        f'<span><span class="chip" style="background:{item["color"]}"></span>'
        f'<b>{item["label"]}</b>：{item["desc"]}</span>'
        for item in cfg.get("legend", [])
    )
    cfg_json = json.dumps(cfg, ensure_ascii=False).replace("</", "<\\/")

    html = (
        "<!DOCTYPE html>\n<html lang=\"" + cfg.get("lang", "zh") + "\">\n<head>\n"
        '<meta charset="utf-8">\n'
        "<title>" + cfg["title"] + "</title>\n"
        "<style>" + STYLE + "</style>\n</head>\n<body>\n"
        "<h1>" + cfg["title"] + "</h1>\n"
        '<p class="wrd-subtitle">' + cfg.get("subtitle", "") + "</p>\n"
        '<div class="wrd-stage" id="wrd-stage">\n'
        '  <canvas id="wrd-canvas"></canvas>\n'
        "</div>\n"
        '<div class="wrd-legend">' + legend_html + "</div>\n"
        "<script>\n" + scaffold_src + "\n</script>\n"
        "<script>\n" + topic_src + "\n</script>\n"
        "<script>\n" + BOOT.replace("__WRD_CONFIG__", cfg_json) + "\n</script>\n"
        "</body>\n</html>\n"
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"gen_animation: 已生成 {out_path} ({len(html)} 字节)")


if __name__ == "__main__":
    main()
