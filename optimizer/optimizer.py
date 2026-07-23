import math

from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2

from config import Config


class OptimizationError(Exception):
    """Erro controlado durante a otimização."""


class Optimizer:

    MAX_SOLVE_SECONDS = 8

    def __init__(self):

        self.tempo_maximo = int(
            Config.TEMPO_MAXIMO_ROTA
        )

        self.tempo_parada = int(
            Config.TEMPO_PARADA
        )

        if self.tempo_maximo <= 0:
            raise ValueError(
                "O tempo máximo da rota deve ser positivo."
            )

        if self.tempo_parada < 0:
            raise ValueError(
                "O tempo de parada não pode ser negativo."
            )

    def otimizar(
        self,
        matriz_tempo
    ) -> list[list[int]]:

        matrix = self._prepare_matrix(
            matriz_tempo
        )

        quantidade_pontos = len(
            matrix
        )

        quantidade_entregas = (
            quantidade_pontos - 1
        )

        if quantidade_entregas <= 0:
            raise OptimizationError(
                "Nenhuma entrega foi informada."
            )

        self._validate_individual_deliveries(
            matrix
        )

        quantidade_motoristas = (
            quantidade_entregas
        )

        manager = pywrapcp.RoutingIndexManager(
            quantidade_pontos,
            quantidade_motoristas,
            0
        )

        routing = pywrapcp.RoutingModel(
            manager
        )

        def time_callback(
            from_index,
            to_index
        ) -> int:

            origem = manager.IndexToNode(
                from_index
            )

            destino = manager.IndexToNode(
                to_index
            )

            tempo = matrix[
                origem
            ][
                destino
            ]

            if destino != 0:
                tempo += self.tempo_parada

            return tempo

        callback_index = routing.RegisterTransitCallback(
            time_callback
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

        time_dimension = routing.GetDimensionOrDie(
            "Tempo"
        )

        time_dimension.SetGlobalSpanCostCoefficient(
            10
        )

        fixed_vehicle_cost = max(
            self.tempo_maximo * 100,
            1_000_000
        )

        for vehicle in range(
            quantidade_motoristas
        ):

            routing.SetFixedCostOfVehicle(
                fixed_vehicle_cost,
                vehicle
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

        search_parameters.time_limit.seconds = (
            self.MAX_SOLVE_SECONDS
        )

        search_parameters.log_search = False

        solution = routing.SolveWithParameters(
            search_parameters
        )

        if solution is None:

            raise OptimizationError(
                "Não foi possível encontrar uma divisão "
                "válida das entregas. Confira se todos os "
                "endereços estão dentro do alcance permitido."
            )

        rotas = self._extract_routes(
            routing=routing,
            manager=manager,
            solution=solution,
            quantidade_motoristas=quantidade_motoristas
        )

        if not rotas:

            raise OptimizationError(
                "O otimizador não gerou nenhuma rota."
            )

        self._validate_result(
            routes=rotas,
            matrix=matrix
        )

        return rotas

    def _prepare_matrix(
        self,
        matriz_tempo
    ) -> list[list[int]]:

        if (
            not isinstance(
                matriz_tempo,
                list
            )
            or not matriz_tempo
        ):

            raise OptimizationError(
                "A matriz de tempos está vazia ou inválida."
            )

        quantidade = len(
            matriz_tempo
        )

        prepared = []

        for row_index, row in enumerate(
            matriz_tempo
        ):

            if (
                not isinstance(
                    row,
                    list
                )
                or len(row) != quantidade
            ):

                raise OptimizationError(
                    "A matriz de tempos não é quadrada."
                )

            prepared_row = []

            for column_index, value in enumerate(
                row
            ):

                if (
                    row_index == column_index
                ):

                    prepared_row.append(
                        0
                    )

                    continue

                if value is None:

                    raise OptimizationError(
                        "Não existe rota rodoviária entre "
                        f"os pontos {row_index} e "
                        f"{column_index}."
                    )

                try:
                    numeric_value = float(
                        value
                    )
                except (
                    TypeError,
                    ValueError
                ) as error:
                    raise OptimizationError(
                        "A matriz contém um tempo inválido."
                    ) from error

                if (
                    math.isnan(
                        numeric_value
                    )
                    or math.isinf(
                        numeric_value
                    )
                    or numeric_value < 0
                ):

                    raise OptimizationError(
                        "A matriz contém um tempo inválido."
                    )

                prepared_row.append(
                    max(
                        0,
                        int(
                            round(
                                numeric_value
                            )
                        )
                    )
                )

            prepared.append(
                prepared_row
            )

        return prepared

    def _validate_individual_deliveries(
        self,
        matrix: list[list[int]]
    ) -> None:

        invalid_deliveries = []

        for delivery_index in range(
            1,
            len(matrix)
        ):

            total_time = (
                matrix[0][delivery_index]
                + self.tempo_parada
                + matrix[delivery_index][0]
            )

            if total_time > self.tempo_maximo:

                invalid_deliveries.append(
                    {
                        "indice": delivery_index,
                        "minutos": round(
                            total_time / 60,
                            1
                        )
                    }
                )

        if invalid_deliveries:

            details = ", ".join(
                (
                    f"entrega {item['indice']} "
                    f"({item['minutos']} minutos)"
                )
                for item in invalid_deliveries
            )

            raise OptimizationError(
                "As seguintes entregas ultrapassam o "
                "limite mesmo quando feitas individualmente: "
                f"{details}."
            )

    def _extract_routes(
        self,
        routing,
        manager,
        solution,
        quantidade_motoristas: int
    ) -> list[list[int]]:

        routes = []

        for vehicle in range(
            quantidade_motoristas
        ):

            index = routing.Start(
                vehicle
            )

            route = []

            while not routing.IsEnd(
                index
            ):

                route.append(
                    manager.IndexToNode(
                        index
                    )
                )

                index = solution.Value(
                    routing.NextVar(
                        index
                    )
                )

            route.append(
                manager.IndexToNode(
                    index
                )
            )

            if len(route) > 2:

                routes.append(
                    route
                )

        return routes

    def _validate_result(
        self,
        routes: list[list[int]],
        matrix: list[list[int]]
    ) -> None:

        expected_deliveries = set(
            range(
                1,
                len(matrix)
            )
        )

        generated_deliveries = []

        for route in routes:

            if (
                route[0] != 0
                or route[-1] != 0
            ):

                raise OptimizationError(
                    "Uma rota foi gerada sem iniciar e "
                    "terminar na origem."
                )

            route_time = 0

            for position in range(
                len(route) - 1
            ):

                origin = route[position]
                destination = route[
                    position + 1
                ]

                route_time += matrix[
                    origin
                ][
                    destination
                ]

                if destination != 0:

                    route_time += (
                        self.tempo_parada
                    )

                    generated_deliveries.append(
                        destination
                    )

            if route_time > self.tempo_maximo:

                raise OptimizationError(
                    "Uma rota ultrapassou o tempo máximo "
                    "permitido."
                )

        if (
            set(generated_deliveries)
            != expected_deliveries
        ):

            raise OptimizationError(
                "Nem todas as entregas foram incluídas "
                "nas rotas."
            )

        if (
            len(generated_deliveries)
            != len(
                set(
                    generated_deliveries
                )
            )
        ):

            raise OptimizationError(
                "Uma entrega foi incluída em mais de uma rota."
            )