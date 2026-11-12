"""Experimental same-request decoding guard for Qwen3-14B and vLLM MRV1."""
from dataclasses import dataclass


def repeated_suffix(tokens, start, *, min_period=8, max_period=256, min_span=64):
    """Return the shortest period of a suffix with four complete copies."""
    end = len(tokens)
    for period in range(min_period, min(max_period, (end - start) // 4) + 1):
        copies = max(4, (min_span + period - 1) // period)
        if end - start < copies * period or tokens[-1] != tokens[-1 - period]:
            continue
        block = tokens[-period:]
        if all(tokens[end - (i + 1) * period:end - i * period] == block
               for i in range(1, copies)):
            return period
    return None


@dataclass
class ReasoningGuard:
    """One request's output cursor, independent of its batch slot."""
    assistant_prefix: tuple[int, ...]
    end_tokens: frozenset[int]
    cursor: int = 0
    floor: int = 0
    broke_cycle: bool = False
    done: bool = False

    def inspect(self, prompt_ids, output_ids):
        if self.done or self.cursor == len(output_ids):
            return None
        if self.cursor == 0 and tuple(prompt_ids[-len(self.assistant_prefix):]) != self.assistant_prefix:
            self.done = True
            return None
        new = output_ids[self.cursor:]
        if len(output_ids) < self.cursor or any(token < 0 or token in self.end_tokens for token in new):
            self.done = True
            return None
        self.cursor = len(output_ids)
        period = repeated_suffix(output_ids, self.floor)
        if period is None:
            return None
        return ('close_reasoning' if self.broke_cycle else 'mask_repeated_token',
                output_ids[-period], period)

    def applied(self):
        if self.broke_cycle:
            self.done = True
        self.broke_cycle = True
        self.floor = self.cursor


def apply_action(guard, action, logits, close_token):
    """Leave the row untouched if the proposed edit conflicts with a mask."""
    kind, repeated_token, _ = action
    if kind == 'mask_repeated_token':
        if repeated_token >= len(logits) or not logits[repeated_token].isfinite().item():
            return False
        if logits.isfinite().sum().item() <= 1:
            return False
        logits[repeated_token] = float('-inf')
    else:
        if close_token >= len(logits) or not logits[close_token].isfinite().item():
            return False
        kept = logits[close_token].clone()
        logits.fill_(float('-inf'))
        logits[close_token] = kept
    guard.applied()
    return True


try:
    from vllm.v1.sample.logits_processor import AdapterLogitsProcessor
except ImportError:
    # The detector and CPU tensor checks can run without a vLLM installation.
    AdapterLogitsProcessor = None


if AdapterLogitsProcessor is not None:
    import logging
    from transformers import AutoTokenizer

    log = logging.getLogger(__name__)

    class Qwen3ReasoningGuard(AdapterLogitsProcessor):
        def __init__(self, vllm_config, device, is_pin_memory):
            super().__init__(vllm_config, device, is_pin_memory)
            model = vllm_config.model_config
            if model.hf_config.model_type != 'qwen3' or vllm_config.speculative_config is not None:
                raise ValueError('The experimental processor requires Qwen3 and non-speculative MRV1.')
            if vllm_config.scheduler_config.async_scheduling:
                raise ValueError('The processor requires synchronous committed output token IDs.')
            tokenizer = AutoTokenizer.from_pretrained(
                model.tokenizer, revision=model.tokenizer_revision or model.revision,
                local_files_only=True, trust_remote_code=False,
            )
            def encode(value):
                return tokenizer.encode(value, add_special_tokens=False)
            self.prefix = tuple(encode('<|im_start|>assistant\n'))
            close, tool, eos = (encode(marker) for marker in ('</think>', '<tool_call>', '<|im_end|>'))
            if close != [151668] or tool != [151657] or eos != [151645]:
                raise ValueError('Unexpected Qwen3-14B reasoning or tool boundary tokens.')
            self.close_token = close[0]
            self.end_tokens = frozenset(close + tool + eos + [tokenizer.eos_token_id])

        def is_argmax_invariant(self):
            return False

        def new_req_logits_processor(self, params):
            if (params.allowed_token_ids or params.structured_outputs
                    or getattr(params, 'thinking_token_budget', None) is not None
                    or getattr(params, 'repetition_detection', None) is not None
                    or self.close_token in (params.stop_token_ids or ())
                    or any(marker in '</think>' for marker in (params.stop or ()) if marker)):
                return None
            guard = ReasoningGuard(self.prefix, self.end_tokens)

            def process(prompt_ids, output_ids, logits):
                action = guard.inspect(prompt_ids, output_ids)
                if action is not None and apply_action(guard, action, logits, self.close_token):
                    log.info('WRD reasoning cycle: action=%s output_tokens=%d period=%d',
                             action[0], len(output_ids), action[2])
                return logits

            return process
