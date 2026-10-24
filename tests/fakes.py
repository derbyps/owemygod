class FakeClient:
    def __init__(self, text: str = "", raises: bool = False):
        self.text, self.raises, self.last_prompt, self.calls = text, raises, None, 0

    def complete(self, prompt: str, max_tokens: int, temperature: float) -> str:
        self.calls += 1
        self.last_prompt = prompt
        if self.raises:
            raise TimeoutError("model down")
        return self.text
