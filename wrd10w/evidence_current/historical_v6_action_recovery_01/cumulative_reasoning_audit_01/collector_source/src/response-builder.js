/**
 * response-builder.js — OpenAI 响应对象构造（纯函数，从 openai-handler.js 拆出）。
 */

/**
 * 构造非流式 tool_calls 挂起响应（工具调用 → 暂停等客户端执行）。
 */
export function buildToolCallResponse(state, toolEvent, completionId, created, model) {
  return {
    id: completionId, object: 'chat.completion', created, model,
    choices: [{
      index: 0,
      message: {
        role: 'assistant',
        content: state.content || null,
        tool_calls: [{
          id: toolEvent.toolCallId, type: 'function',
          function: { name: toolEvent.name, arguments: JSON.stringify(toolEvent.args) }
        }]
      },
      finish_reason: 'tool_calls'
    }],
    usage: buildUsage(state.usage)
  };
}

/**
 * 构造非流式最终响应（含可选 reasoning_content 回显）。
 */
export function buildFinalResponse(state, completionId, created, model) {
  const message = { role: 'assistant', content: state.content };
  if (state.reasoning) message.reasoning_content = state.reasoning;
  return {
    id: completionId, object: 'chat.completion', created, model,
    choices: [{ index: 0, message, finish_reason: state.finishReason || 'stop' }],
    usage: buildUsage(state.usage)
  };
}

/**
 * 归一化 usage 字段。
 *
 * 网关上报了缓存信息时补 `prompt_tokens_details.cached_tokens`（OpenAI 标准
 * 字段），让客户端一眼看出 PROMPT 里绝大多数是命中前缀缓存的部分——否则
 * 只看 prompt_tokens 会以为每条请求都在烧两三万 token。
 */
export function buildUsage(usage) {
  const u = usage || {};
  const promptTokens = u.prompt_tokens || 0;
  const completionTokens = u.completion_tokens || 0;
  const result = {
    prompt_tokens: promptTokens,
    completion_tokens: completionTokens,
    total_tokens: promptTokens + completionTokens
  };
  if (typeof u.cached_tokens === 'number') {
    result.prompt_tokens_details = { cached_tokens: u.cached_tokens };
  }
  return result;
}
