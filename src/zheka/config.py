from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from zheka.constants import TRIGGER_KEYWORDS


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='infra/.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    bot_token: str = Field(validation_alias='TG_BOT_TOKEN')
    openai_api_key: str = Field(validation_alias='OPEN_AI_KEY')
    admin_id: int = Field(default=0, validation_alias='TG_ADMIN_ID')
    openai_base_url: str = ''
    llm_model: str
    reply_probability: float = 0.07
    max_replies_per_minute: int = 3
    max_replies_per_day: int = 300
    context_window: int = 15
    trigger_keywords: str = ''
    persona_path: str = 'infra/persona.txt'
    allowed_chat_ids: str = ''
    mcp_url: str = Field(
        default='',
        validation_alias='RAG_MCP_URL',
        description='URL для MCP сервиса',
    )
    search_chat_ids: str = Field(
        default='',
        validation_alias='SEARCH_CHAT_IDS'
    )

    @property
    def allowed_chats(self) -> set[int]:
        """Разрешённые chat_id; пустое множество — без ограничений."""
        return {
            int(chunk.strip())
            for chunk in self.allowed_chat_ids.split(',')
            if chunk.strip()
        }

    def chat_allowed(self, chat_id: int) -> bool:
        """Можно ли боту работать в этом чате."""
        allowed = self.allowed_chats
        return not allowed or chat_id in allowed

    @property
    def search_chats(self) -> set[int]:
        """Чаты с включённым поиском; пусто — поиск выключен везде."""
        return {
            int(chunk.strip())
            for chunk in self.search_chat_ids.split(',')
            if chunk.strip()
        }

    def search_allowed(self, chat_id: int) -> bool:
        """Включён ли агент-поиск в этом чате.

        В отличие от chat_allowed, поиск строго opt-in: нужен
        непустой mcp_url и явное перечисление чата в списке.
        """
        return bool(self.mcp_url) and chat_id in self.search_chats

    @property
    def keywords(self) -> list[str]:
        """Ключевые слова из .env либо дефолтный список из констант."""
        if not self.trigger_keywords:
            return TRIGGER_KEYWORDS
        return [
            word.strip().lower()
            for word in self.trigger_keywords.split(',')
            if word.strip()
        ]
