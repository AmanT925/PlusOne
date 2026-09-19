from server.linq import LinqClient


class FakeLinq(LinqClient):
    def __init__(self) -> None:
        self.api_key = "test"
        self.sent: list[dict] = []
        self.typing: list[str] = []
        self.fail_chats: set[str] = set()

    def enabled(self) -> bool:
        return True

    async def aclose(self) -> None:
        return None

    async def start_typing(self, chat_id: str) -> None:
        self.typing.append(chat_id)

    async def send_text(self, text: str, *, chat_id: str | None = None, to: str | None = None) -> bool:
        if chat_id in self.fail_chats:
            self.sent.append({"text": text, "chat_id": chat_id, "to": to, "ok": False})
            return False
        self.sent.append({"text": text, "chat_id": chat_id, "to": to, "ok": True})
        return True

    async def send_link(self, url: str, *, chat_id: str | None = None, to: str | None = None) -> bool:
        return await self.send_text(url, chat_id=chat_id, to=to)
