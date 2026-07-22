from config import TEMPO_MAXIMO_ROTA


class RouteAnalyzer:

    def validar_rotas(self, estatisticas):

        """
        Verifica se todas as rotas respeitam o limite máximo.
        """

        for rota in estatisticas:

            if rota["tempo_minutos"] > TEMPO_MAXIMO_ROTA:

                return False

        return True