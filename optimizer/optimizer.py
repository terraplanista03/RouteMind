import math

from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2

from config import Config


class OptimizationError(Exception):
    """Erro controlado durante a otimização das rotas."""


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

        matriz_original = self._preparar_matriz(
            matriz_tempo
        )

        quantidade_pontos = len(
            matriz_original
        )

        quantidade_entregas = (
            quantidade_pontos - 1
        )

        if quantidade_entregas <= 0:
            raise OptimizationError(
                "Nenhuma entrega foi informada."
            )

        self._validar_entregas_individuais(
            matriz_original
        )

        matriz_com_destino, destino_final = (
            self._adicionar_destino_aberto(
                matriz_original
            )
        )

        quantidade_total_pontos = len(
            matriz_com_destino
        )

        quantidade_motoristas = (
            quantidade_entregas
        )

        inicios = [
            0
            for _ in range(
                quantidade_motoristas
            )
        ]

        finais = [
            destino_final
            for _ in range(
                quantidade_motoristas
            )
        ]

        manager = pywrapcp.RoutingIndexManager(
            quantidade_total_pontos,
            quantidade_motoristas,
            inicios,
            finais
        )

        routing = pywrapcp.RoutingModel(
            manager
        )

        def tempo_callback(
            from_index,
            to_index
        ) -> int:

            origem = manager.IndexToNode(
                from_index
            )

            destino = manager.IndexToNode(
                to_index
            )

            if destino == destino_final:
                return 0

            tempo = matriz_com_destino[
                origem
            ][
                destino
            ]

            if destino != 0:
                tempo += self.tempo_parada

            return tempo

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

        dimensao_tempo = routing.GetDimensionOrDie(
            "Tempo"
        )

        dimensao_tempo.SetGlobalSpanCostCoefficient(
            10
        )

        custo_motorista = max(
            self.tempo_maximo * 100,
            1_000_000
        )

        for motorista in range(
            quantidade_motoristas
        ):

            routing.SetFixedCostOfVehicle(
                custo_motorista,
                motorista
            )

        parametros = (
            pywrapcp.DefaultRoutingSearchParameters()
        )

        parametros.first_solution_strategy = (
            routing_enums_pb2
            .FirstSolutionStrategy
            .PARALLEL_CHEAPEST_INSERTION
        )

        parametros.local_search_metaheuristic = (
            routing_enums_pb2
            .LocalSearchMetaheuristic
            .GUIDED_LOCAL_SEARCH
        )

        parametros.time_limit.seconds = (
            self.MAX_SOLVE_SECONDS
        )

        parametros.log_search = False

        solucao = routing.SolveWithParameters(
            parametros
        )

        if solucao is None:

            raise OptimizationError(
                "Não foi possível encontrar uma divisão "
                "válida das entregas."
            )

        rotas = self._extrair_rotas(
            routing=routing,
            manager=manager,
            solucao=solucao,
            quantidade_motoristas=(
                quantidade_motoristas
            ),
            destino_final=destino_final
        )

        if not rotas:

            raise OptimizationError(
                "O otimizador não gerou nenhuma rota."
            )

        self._validar_resultado(
            rotas=rotas,
            matriz=matriz_original
        )

        return rotas

    def _adicionar_destino_aberto(
        self,
        matriz: list[list[int]]
    ) -> tuple[list[list[int]], int]:

        quantidade_original = len(
            matriz
        )

        destino_final = quantidade_original

        nova_matriz = []

        for linha in matriz:

            nova_linha = list(
                linha
            )

            nova_linha.append(
                0
            )

            nova_matriz.append(
                nova_linha
            )

        linha_destino = [
            0
            for _ in range(
                quantidade_original + 1
            )
        ]

        nova_matriz.append(
            linha_destino
        )

        return (
            nova_matriz,
            destino_final
        )

    def _preparar_matriz(
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

        matriz_preparada = []

        for indice_linha, linha in enumerate(
            matriz_tempo
        ):

            if (
                not isinstance(
                    linha,
                    list
                )
                or len(linha) != quantidade
            ):

                raise OptimizationError(
                    "A matriz de tempos não é quadrada."
                )

            nova_linha = []

            for indice_coluna, valor in enumerate(
                linha
            ):

                if indice_linha == indice_coluna:

                    nova_linha.append(
                        0
                    )

                    continue

                if valor is None:

                    raise OptimizationError(
                        "Não existe rota rodoviária entre "
                        f"os pontos {indice_linha} e "
                        f"{indice_coluna}."
                    )

                try:

                    valor_numerico = float(
                        valor
                    )

                except (
                    TypeError,
                    ValueError
                ) as erro:

                    raise OptimizationError(
                        "A matriz contém um tempo inválido."
                    ) from erro

                if (
                    math.isnan(
                        valor_numerico
                    )
                    or math.isinf(
                        valor_numerico
                    )
                    or valor_numerico < 0
                ):

                    raise OptimizationError(
                        "A matriz contém um tempo inválido."
                    )

                nova_linha.append(
                    max(
                        0,
                        int(
                            round(
                                valor_numerico
                            )
                        )
                    )
                )

            matriz_preparada.append(
                nova_linha
            )

        return matriz_preparada

    def _validar_entregas_individuais(
        self,
        matriz: list[list[int]]
    ) -> None:

        entregas_invalidas = []

        for indice_entrega in range(
            1,
            len(matriz)
        ):

            tempo_total = (
                matriz[0][indice_entrega]
                + self.tempo_parada
            )

            if tempo_total > self.tempo_maximo:

                entregas_invalidas.append(
                    {
                        "indice": indice_entrega,
                        "minutos": round(
                            tempo_total / 60,
                            1
                        )
                    }
                )

        if entregas_invalidas:

            detalhes = ", ".join(
                (
                    f"entrega {item['indice']} "
                    f"({item['minutos']} minutos)"
                )
                for item in entregas_invalidas
            )

            raise OptimizationError(
                "As seguintes entregas ultrapassam o "
                "limite mesmo quando feitas individualmente: "
                f"{detalhes}."
            )

    def _extrair_rotas(
        self,
        routing,
        manager,
        solucao,
        quantidade_motoristas: int,
        destino_final: int
    ) -> list[list[int]]:

        rotas = []

        for motorista in range(
            quantidade_motoristas
        ):

            index = routing.Start(
                motorista
            )

            rota = []

            while not routing.IsEnd(
                index
            ):

                ponto = manager.IndexToNode(
                    index
                )

                if ponto != destino_final:

                    rota.append(
                        ponto
                    )

                index = solucao.Value(
                    routing.NextVar(
                        index
                    )
                )

            if len(rota) > 1:

                rotas.append(
                    rota
                )

        return rotas

    def _validar_resultado(
        self,
        rotas: list[list[int]],
        matriz: list[list[int]]
    ) -> None:

        entregas_esperadas = set(
            range(
                1,
                len(matriz)
            )
        )

        entregas_geradas = []

        for rota in rotas:

            if not rota or rota[0] != 0:

                raise OptimizationError(
                    "Uma rota foi gerada sem iniciar na origem."
                )

            tempo_rota = 0

            for posicao in range(
                len(rota) - 1
            ):

                origem = rota[
                    posicao
                ]

                destino = rota[
                    posicao + 1
                ]

                tempo_rota += matriz[
                    origem
                ][
                    destino
                ]

                if destino != 0:

                    tempo_rota += (
                        self.tempo_parada
                    )

                    entregas_geradas.append(
                        destino
                    )

            if tempo_rota > self.tempo_maximo:

                raise OptimizationError(
                    "Uma rota ultrapassou o tempo máximo."
                )

        if (
            set(
                entregas_geradas
            )
            != entregas_esperadas
        ):

            raise OptimizationError(
                "Nem todas as entregas foram incluídas."
            )

        if (
            len(
                entregas_geradas
            )
            != len(
                set(
                    entregas_geradas
                )
            )
        ):

            raise OptimizationError(
                "Uma entrega foi incluída mais de uma vez."
            )