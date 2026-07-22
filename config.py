import os


class Config:

    OPENROUTESERVICE_API_KEY = os.getenv(
        "OPENROUTESERVICE_API_KEY",
        "SUA_CHAVE_AQUI"
    )

    TEMPO_MAXIMO_ROTA = 120 * 60

    TEMPO_PARADA = 20 * 60
