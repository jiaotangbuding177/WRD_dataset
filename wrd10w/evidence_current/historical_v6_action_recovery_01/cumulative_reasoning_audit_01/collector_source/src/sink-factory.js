/**
 * sink-factory.js — 三条消费路径共用的 sink 装配点。
 *
 * StreamDriver 定义了 sink 接口（九个处理器），但接口的"构造"曾复制三份
 * （首轮流式 / 首轮非流式 / 工具回传续跑，各 ~45 行、共享 70%）。本工厂把
 * 六个完全相同的处理器收敛为一份，路径差异只通过参数注入：
 *
 *   emit        'stream'     → 增量写 SSE chunk（含心跳保活）
 *               'accumulate' → 只累加 state（非流式，无心跳）
 *   onToolCall  工具调用挂起——各路径挂起后的响应形态不同，注入
 *   onTimeout   软超时——流式优雅收尾 / 非流式抛错，注入
 *   onError     统一为"记日志后抛原始消息"，由 _runWithRateLimitRetry
 *               判断频控重试、外层 catch 兜底清理（原先非流式路径在
 *               此处多做一次 pending.delete，与外层 catch 重复，已去重）
 *   onDone      收尾——清理动作 + 最终响应形态，注入
 */

import { sseChunk, resWriter } from './stream-driver.js';

export function createSink({
  emit = 'accumulate',
  state,
  key,
  completionId,
  created,
  model,
  res,
  onToolCall,
  onTimeout,
  onDone
}) {
  const stream = emit === 'stream';
  const write = stream ? resWriter(res) : () => {};
  let lastProgressText = '';

  return {
    // 心跳保活：上下文压缩期间 WorkBuddy 长时间静默，向客户端写 SSE 注释
    // 防止连接被代理/客户端因空闲断开。注释行客户端会自动忽略。
    // 可选 message 参数：排队重试时附带进度信息，让用户看到服务没卡死
    heartbeat: stream ? (message) => write(`${message || ': keep-alive'}\n\n`) : undefined,
    onDelta: (text) => {
      state.content += text;
      if (stream) write(sseChunk(completionId, created, model, { content: text }));
    },
    onReasoning: (text) => {
      state.reasoning += text;
      if (stream) write(sseChunk(completionId, created, model, { reasoning_content: text }));
    },
    onUsage: (usage) => { state.usage = usage; },
    onProgress: (text, phase) => {
      // 阶段/进度信息（含压缩上下文）：流式转发给客户端作为 reasoning_content，
      // 让 UI 显示"正在压缩上下文…"而不是一片空白。不写入 state.reasoning，
      // 避免污染最终答案；去重防刷屏（原先非流式路径无去重，此处统一补齐）。
      if (!text || text === lastProgressText) return;
      lastProgressText = text;
      console.log(`[buddy2api] progress: ${text} (phase: ${phase || '?'})`);
      if (stream) write(sseChunk(completionId, created, model, { reasoning_content: text }));
    },
    onToolCall,
    onTimeout,
    onError: (message) => {
      // WorkBuddy 拒绝 prompt（如 429 频控）。抛错由 _runWithRateLimitRetry 捕获：
      // 频控 → 退避重试；其他错误 → 外层 catch 兜底清理。
      console.warn(`[buddy2api] WorkBuddy error for key=${key}: ${message}`);
      throw new Error(message);
    },
    onDone
  };
}
