import os

from anthropic import Anthropic

from src.schemas.llm_provider import LLMProvider


SYSTEM_PROMPT = (
    "You are an expert UI/UX researcher. Synthesize findings into actionable "
    "recommendations for designers. Return ONLY valid JSON conforming to the "
    "DesignResearchResponse schema. Do not include markdown or prose."
)


class ClaudeLLM(LLMProvider):
    def __init__(self, model: str = "claude-sonnet-4-5-20250929") -> None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required.")
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def synthesize(self, prompt: str) -> str:
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        # Claude returns a list of content blocks; join all text blocks
        parts = []
        for block in msg.content:
            if getattr(block, "type", None) == "text":
                if getattr(block, "text", None):
                    parts.append(block.text)
        return "".join(parts)

    def synthesize_stream(self, prompt: str):
        # Streaming API for Claude; yields text deltas
        with self.client.messages.stream(
            model=self.model,
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        ) as stream:
            for event in stream:
                # event.type could be 'content_block_delta' with .delta.text
                try:
                    if getattr(event, "type", None) == "content_block_delta":
                        delta = getattr(event, "delta", None)
                        text = getattr(delta, "text", None)
                        if text:
                            yield text
                except Exception:
                    continue


