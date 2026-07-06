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
    llm_model: str = 'gpt-5.4'
    reply_probability: float = 0.07
    max_replies_per_minute: int = 3
    max_replies_per_day: int = 300
    context_window: int = 15
    trigger_keywords: str = ''
    persona_path: str = 'infra/persona.txt'

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
