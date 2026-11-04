---
name: meeting-minutes-formatting
description: 从录音转写/录音总结或既有纪要材料整理会议纪要并成文时，直接套用既定样式规范，对docx批量排版：中文字体（楷体/宋体）、数字西文Times New Roman、小四12pt、1.5倍行距、首行缩进2字符、可选去*号。适用于用户沿用既往纪要格式或给出明确样式参数的场景。
---

## 最短路线
1. collect_meeting_content：读取录音转写/录音总结或既有纪要材料，取得全部正文内容。
2. apply_format_and_style：确定样式来源——沿用既往格式（楷体系）或用户明确参数（如宋体），直接调用下方程序，不重设样式代码。
3. compose_minutes_document：按模板/样式成文输出docx；材料内容不足时明确说明，不虚构会议事实。

## 直接资源
- 样式规范与成文约定：`references/minutes_style_reference.md`
- 格式化程序（批量排版，一次完成）：

```
python {SKILL}/scripts/apply_minutes_format.py {INPUT}/meeting_minutes.docx --out {OUT}/minutes_formatted.docx --report {OUT}/format_summary.json
```

可选项：`--cn-font 宋体`（默认楷体）、`--western-font "Times New Roman"`、`--body-size 12`、`--line-spacing 1.5`、`--first-line-indent 2`（0禁用）、`--remove-stars`（去行首*号）。

## 适用与关键分岔
- 输入：会议录音转写/录音总结文本或既有纪要docx；样式由用户明确给出或沿用既往格式。
- 分岔：沿用既往格式→默认楷体；用户明确改宋体→`--cn-font 宋体`；来源含*号列表→加`--remove-stars`。
- 不覆盖：录音转写本身、会议内容事实核对与补充；程序不处理表格、不嵌字体、不修损坏docx。

## 输出
排版后的docx + JSON摘要（段落数、去星数、样式参数）。输出docx可直接作为纪要正文接续成文或交付。
