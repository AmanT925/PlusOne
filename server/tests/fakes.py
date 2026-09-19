from server.linq import LinqClient


class FakeLinq(LinqClient):
    def __init__(self) -> None:
        self.api_key = "test"
        self.sent: list[dict] = []
        self.typing: list[str] = []
        self.voice_memos: list[dict] = []
        self.media: list[dict] = []
        self.uploads: list[dict] = []

    def enabled(self) -> bool:
        return True

    async def aclose(self) -> None:
        return None

    async def start_typing(self, chat_id: str) -> None:
        self.typing.append(chat_id)

    async def send_text(self, text: str, *, chat_id: str | None = None, to: str | None = None) -> None:
        self.sent.append({"text": text, "chat_id": chat_id, "to": to})

    async def upload_attachment(self, data: bytes, *, filename: str, content_type: str):
        attachment_id = f"att-{len(self.uploads)+1}"
        self.uploads.append(
            {
                "attachment_id": attachment_id,
                "filename": filename,
                "content_type": content_type,
                "size": len(data),
            }
        )
        return {"attachment_id": attachment_id, "download_url": f"https://cdn.example/{attachment_id}"}

    async def send_voice_memo(
        self,
        *,
        chat_id: str,
        attachment_id: str | None = None,
        voice_memo_url: str | None = None,
    ) -> bool:
        self.voice_memos.append(
            {
                "chat_id": chat_id,
                "attachment_id": attachment_id,
                "voice_memo_url": voice_memo_url,
            }
        )
        return True

    async def send_media(
        self,
        *,
        chat_id: str | None = None,
        to: str | None = None,
        media_url: str | None = None,
        attachment_id: str | None = None,
        caption: str | None = None,
    ) -> bool:
        self.media.append(
            {
                "chat_id": chat_id,
                "to": to,
                "media_url": media_url,
                "attachment_id": attachment_id,
                "caption": caption,
            }
        )
        return True
