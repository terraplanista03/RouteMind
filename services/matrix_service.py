import openrouteservice

from config import Config


class MatrixService:

    def __init__(self):

        if (
            not Config.OPENROUTESERVICE_API_KEY
            or Config.OPENROUTESERVICE_API_KEY == "SUA_CHAVE_AQUI"
        ):
            raise ValueError(
                "A variável OPENROUTESERVICE_API_KEY não foi configurada."
            )

        self.client = openrouteservice.Client(
            key=Config.OPENROUTESERVICE_API_KEY,
            timeout=15,
            retry_timeout=2,
            retry_over_query_limit=False
        )

    def calcular(
        self,
        coordenadas
    ):

        if not coordenadas:
            raise ValueError(
                "Nenhuma coordenada foi informada."
            )

        try:

            resultado = self.client.distance_matrix(
                locations=coordenadas,
                profile="driving-car",
                metrics=[
                    "distance",
                    "duration"
                ],
                resolve_locations=False
            )

        except Exception as erro:

            raise Exception(
                "Não foi possível calcular as distâncias e os "
                "tempos das rotas. Tente novamente em alguns instantes."
            ) from erro

        if (
            not resultado
            or "durations" not in resultado
            or "distances" not in resultado
        ):
            raise Exception(
                "A OpenRouteService retornou uma matriz inválida."
            )

        return resultado