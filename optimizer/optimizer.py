from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2


class Optimizer:

    def __init__(self):

        self.tempo_maximo = 120 * 60

        self.tempo_parada = 20 * 60

    def otimizar(self, matriz_tempo):

        quantidade_pontos = len(matriz_tempo)

        quantidade_entregas = quantidade_pontos - 1

        for motoristas in range(1, quantidade_entregas + 1):

            rotas = self._resolver(
                matriz_tempo,
                quantidade_pontos,
                motoristas
            )

            if rotas is not None:
                return rotas

        raise Exception(
            "Não foi possível encontrar uma solução."
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

        routing = pywrapcp.RoutingModel(manager)

        def tempo_callback(from_index, to_index):

            origem = manager.IndexToNode(from_index)

            destino = manager.IndexToNode(to_index)

            tempo = matriz_tempo[origem][destino]

            if tempo is None:
                return 999999999

            tempo = int(tempo)

            if destino != 0:
                tempo += self.tempo_parada

            return tempo

        callback_index = routing.RegisterTransitCallback(
            tempo_callback
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
            .PATH_CHEAPEST_ARC
        )

        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2
            .LocalSearchMetaheuristic
            .GUIDED_LOCAL_SEARCH
        )

        search_parameters.time_limit.seconds = 5

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

            index = routing.Start(motorista)

            while not routing.IsEnd(index):

                ponto = manager.IndexToNode(index)

                rota.append(ponto)

                index = solution.Value(
                    routing.NextVar(index)
                )

            rota.append(
                manager.IndexToNode(index)
            )

            if len(rota) > 2:
                rotas.append(rota)

        if len(rotas) == 0:
            return None

        return rotas