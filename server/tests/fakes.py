from server.linq import LinqClient


class FakeLinq(LinqClient):
    def __init__(self) -> None:
        self.api_key = "test"
        self.sent: list[dict] = []
        self.typing: list[str] = []

    def enabled(self) -> bool:
        return True

    async def aclose(self) -> None:
        return None

    async def start_typing(self, chat_id: str) -> None:
        self.typing.append(chat_id)

    async def send_text(self, text: str, *, chat_id: str | None = None, to: str | None = None) -> None:
        self.sent.append({"text": text, "chat_id": chat_id, "to": to})
