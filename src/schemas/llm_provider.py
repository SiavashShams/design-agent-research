from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def synthesize(self, prompt: str) -> str:
        """Return raw JSON string for DesignResearchResponse."""
        raise NotImplementedError

    def synthesize_stream(self, prompt: str):
        """Yield incremental string chunks as the model generates output.

        Default implementation falls back to non-streaming synthesize.
        Implementations should override for true token streaming.
        """
        yield self.synthesize(prompt)


