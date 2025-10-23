import os

from openai import OpenAI

from src.schemas.llm_provider import LLMProvider


SYSTEM_PROMPT = (
    "You are an expert UI/UX researcher. Synthesize findings into actionable "
    "recommendations for designers. Return ONLY valid JSON conforming to the "
    "DesignResearchResponse schema. Do not include markdown or prose."
)


class OpenAILLM(LLMProvider):
    def __init__(self, model: str = "gpt-5-mini") -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required.")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def synthesize(self, prompt: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=1, # gpt5 models only support temperature=1
        )
        return resp.choices[0].message.content or ""

    def synthesize_stream(self, prompt: str):
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=1,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and getattr(delta, "content", None):
                yield delta.content


