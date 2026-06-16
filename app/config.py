from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

SUPPORTED_LEAGUES = {
    "eng.1": "Premier League",
    "esp.1": "LALIGA",
    "ita.1": "Serie A",
    "ger.1": "Bundesliga",
    "fra.1": "Ligue 1",
    "uefa.champions": "Champions League",
    "uefa.europa": "Europa League",
    "fifa.world": "World Cup",
    "uefa.euro": "European Championship",
    "conmebol.america": "Copa América",
    "caf.nations": "Africa Cup of Nations",
    "afc.asian": "Asian Cup",
    "eng.fa": "FA Cup",
    "esp.copa_del_rey": "Copa del Rey",
    "ita.coppa_italia": "Coppa Italia",
    "ger.dfb_pokal": "DFB-Pokal",
    "fra.coupe_de_france": "Coupe de France"
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Footy API"
    cache_ttl_seconds: int = Field(default=20, alias="CACHE_TTL_SECONDS")
    request_timeout_seconds: int = Field(default=10, alias="REQUEST_TIMEOUT_SECONDS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


@lru_cache
def get_settings() -> Settings:
    return Settings()
