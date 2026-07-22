from config import TEMPO_PARADA


class RouteStatistics:

    def calcular(
        self,
        matriz_tempo,
        rotas,
        matriz_distancia=None
    ):

        tempo_total = 0

        tempo_deslocamento_total = 0

        distancia_total = 0

        estatisticas = []

        for indice_motorista, rota in enumerate(rotas):

            tempo_deslocamento = 0

            distancia_rota = 0

            entregas = 0

            for i in range(len(rota) - 1):

                origem = rota[i]

                destino = rota[i + 1]

                tempo = matriz_tempo[origem][destino]

                if tempo is None:
                    tempo = 0

                tempo_deslocamento += tempo / 60

                if matriz_distancia is not None:

                    distancia = matriz_distancia[origem][destino]

                    if distancia is None:
                        distancia = 0

                    distancia_rota += distancia / 1000

                if destino != 0:
                    entregas += 1

            tempo_paradas = entregas * TEMPO_PARADA

            tempo_rota = (
                tempo_deslocamento
                + tempo_paradas
            )

            tempo_total += tempo_rota

            tempo_deslocamento_total += (
                tempo_deslocamento
            )

            distancia_total += distancia_rota

            estatisticas.append({

                "motorista": indice_motorista + 1,

                "entregas": entregas,

                "tempo_deslocamento": round(
                    tempo_deslocamento,
                    1
                ),

                "tempo_paradas": tempo_paradas,

                "tempo_total": round(
                    tempo_rota,
                    1
                ),

                "distancia_km": round(
                    distancia_rota,
                    1
                )

            })

        return {

            "motoristas": len(rotas),

            "tempo_deslocamento": round(
                tempo_deslocamento_total,
                1
            ),

            "tempo_total": round(
                tempo_total,
                1
            ),

            "distancia_total_km": round(
                distancia_total,
                1
            ),

            "rotas": estatisticas

        }