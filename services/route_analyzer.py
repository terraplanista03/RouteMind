from config import Config


class RouteAnalyzer:

    def validar_rotas(
        self,
        estatisticas
    ):

        for rota in estatisticas:

            tempo_segundos = rota.get(
                "tempo_segundos",
                rota.get(
                    "tempo_total",
                    0
                )
            )

            if (
                tempo_segundos
                > Config.TEMPO_MAXIMO_ROTA
            ):
                return False

        return True