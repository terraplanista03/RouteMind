from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2

from config import Config


class Optimizer:

    def __init__(self):

        self.tempo_maximo = (
            Config.TEMPO_MAXIMO_ROTA
        )

        self.tempo_parada = (
            Config.TEMPO_PARADA
        )

    def otimizar(
        self,
        matriz_tempo
    ):

        self._validar_matriz(
            matriz_tempo
        )

        quantidade_pontos = len(
            matriz_tempo
        )

        quantidade_entregas = (
            quantidade_pontos - 1
        )

        if quantidade_entregas <= 0:
            raise Exception(
                "Nenhuma entrega foi informada."
            )

        self._validar_entregas_individuais(
            matriz_tempo
        )

        for quantidade_motoristas in range(
            1,
            quantidade_entregas + 1
        ):

            rotas = self._resolver(
                matriz_tempo=matriz_tempo,
                quantidade_pontos=quantidade_pontos,
                quantidade_motoristas=quantidade_motoristas
            )

            if rotas:
                return rotas

        raise Exception(
            "Não foi possível organizar todas as entregas "
            "dentro do limite de 120 minutos por motorista."
        )

    def _validar_matriz(
        self,
        matriz_tempo
    ):

        if not matriz_tempo:
            raise Exception(
                "A matriz de tempos está vazia."
            )

        quantidade = len(
            matriz_tempo
        )

        for linha in matriz_tempo:

            if (
                not isinstance(
                    linha,
                    list
                )
                or len(linha) != quantidade
            ):
                raise Exception(
                    "A matriz de tempos recebida é inválida."
                )

    def _validar_entregas_individuais(
        self,
        matriz_tempo
    ):

        entregas_impossiveis = []

        for indice_entrega in range(
            1,
            len(matriz_tempo)
        ):

            tempo_ida = matriz_tempo[
                0
            ][
                indice_entrega
            ]

            tempo_volta = matriz_tempo[
                indice_entrega
            ][
                0
            ]

            if (
                tempo_ida is None
                or tempo_volta is None
            ):

                entregas_impossiveis.append(
                    f"entrega {indice_entrega} "
                    "(rota indisponível)"
                )

                continue

            tempo_total = (
                float(tempo_ida)
                + float(tempo_volta)
                + self.tempo_parada
            )

            if tempo_total > self.tempo_maximo:

                minutos = round(
                    tempo_total / 60,
                    1
                )

                entregas_impossiveis.append(
                    f"entrega {indice_entrega} "
                    f"({minutos} minutos)"
                )

        if entregas_impossiveis:

            detalhes = ", ".join(
                entregas_impossiveis
            )

            raise Exception(
                "Algumas entregas não cabem nem em uma rota "
                "individual de 120 minutos, considerando ida, "
                "20 minutos de parada e retorno à origem: "
                f"{detalhes}."
            )

    def _resolver(
        self,
        matriz_tempo,
        quantidade_pontos,
        quantidade_motoristas
    ):

        manager = pywrapcp.RoutingIndexManager(
            quantidade_pontos,
            quantidade_motoristas,
            0
        )

        routing = pywrapcp.RoutingModel(
            manager
        )

        def tempo_callback(
            from_index,
            to_index
        ):

            origem = manager.IndexToNode(
                from_index
            )

            destino = manager.IndexToNode(
                to_index
            )

            tempo = matriz_tempo[
                origem
            ][
                destino
            ]

            if tempo is None:
                return 999_999_999

            tempo_total = int(
                round(
                    float(tempo)
                )
            )

            if destino != 0:
                tempo_total += self.tempo_parada

            return tempo_total

        callback_index = (
            routing.RegisterTransitCallback(
                tempo_callback
            )
        )

        routing.SetArcCostEvaluatorOfAllVehicles(
            callback_index
        )

        routing.AddDimension(
            callback_index,
            0,
            self.tempo_maximo,
            True,
            "Tempo"
        )

        search_parameters = (
            pywrapcp.DefaultRoutingSearchParameters()
        )

        search_parameters.first_solution_strategy = (
            routing_enums_pb2
            .FirstSolutionStrategy
            .PARALLEL_CHEAPEST_INSERTION
        )

        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2
            .LocalSearchMetaheuristic
            .GUIDED_LOCAL_SEARCH
        )

        search_parameters.time_limit.seconds = 2

        search_parameters.log_search = False

        solution = routing.SolveWithParameters(
            search_parameters
        )

        if solution is None:
            return None

        rotas = []

        for motorista in range(
            quantidade_motoristas
        ):

            rota = []

            index = routing.Start(
                motorista
            )

            while not routing.IsEnd(
                index
            ):

                rota.append(
                    manager.IndexToNode(
                        index
                    )
                )

                index = solution.Value(
                    routing.NextVar(
                        index
                    )
                )

            rota.append(
                manager.IndexToNode(
                    index
                )
            )

            if len(rota) > 2:
                rotas.append(
                    rota
                )

        return rotas