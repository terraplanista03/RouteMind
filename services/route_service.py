from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed

from optimizer.optimizer import OptimizationError
from optimizer.optimizer import Optimizer
from services.geocoder import Geocoder
from services.geocoder import GeocodingError
from services.matrix_service import MatrixService
from services.route_formatter import RouteFormatter
from services.route_statistics import RouteStatistics
from services.validator import Validator


class RouteProcessingError(Exception):
    """Erro amigável durante o processamento das rotas."""


class RouteService:

    MAX_GEOCODING_WORKERS = 4

    def __init__(self):

        self.validator = Validator()
        self.geocoder = Geocoder()
        self.matrix = MatrixService()
        self.optimizer = Optimizer()
        self.statistics = RouteStatistics()
        self.formatter = RouteFormatter()

    def processar(
        self,
        origem: str,
        enderecos: str
    ):

        origem = str(
            origem or ""
        ).strip()

        if not origem:

            raise RouteProcessingError(
                "Informe um endereço de origem."
            )

        try:

            entregas = self.validator.criar_lista(
                enderecos
            )

        except Exception as error:

            raise RouteProcessingError(
                f"Não foi possível validar as entregas: {error}"
            ) from error

        if not entregas:

            raise RouteProcessingError(
                "Informe pelo menos um endereço de entrega."
            )

        origem_dados = self._locate_origin(
            origem
        )

        contexto_origem = {
            "cidade": origem_dados.get(
                "cidade",
                ""
            ),
            "estado": origem_dados.get(
                "estado",
                ""
            ),
            "pais": origem_dados.get(
                "pais",
                "Brasil"
            )
        }

        entregas_validas = self._locate_deliveries(
            entregas=entregas,
            contexto=contexto_origem
        )

        coordenadas = self._build_coordinates(
            origem_dados=origem_dados,
            entregas=entregas_validas
        )

        try:

            matriz = self.matrix.calcular(
                coordenadas
            )

        except Exception as error:

            raise RouteProcessingError(
                "Não foi possível calcular os tempos e as "
                f"distâncias: {error}"
            ) from error

        self._validate_matrix(
            matriz=matriz,
            quantidade_pontos=len(
                coordenadas
            )
        )

        try:

            rotas_indices = self.optimizer.otimizar(
                matriz["durations"]
            )

        except OptimizationError as error:

            raise RouteProcessingError(
                str(error)
            ) from error

        except Exception as error:

            raise RouteProcessingError(
                "Ocorreu um erro inesperado durante a "
                "otimização das entregas."
            ) from error

        try:

            analise = self.statistics.calcular(
                matriz_tempo=matriz[
                    "durations"
                ],
                rotas=rotas_indices,
                matriz_distancia=matriz[
                    "distances"
                ]
            )

            rotas = self.formatter.formatar(
                rotas_indices,
                entregas_validas
            )

        except Exception as error:

            raise RouteProcessingError(
                "As rotas foram calculadas, mas não foi "
                "possível preparar o resultado."
            ) from error

        return (
            origem_dados,
            entregas_validas,
            matriz,
            analise,
            rotas
        )

    def _locate_origin(
        self,
        origem: str
    ) -> dict:

        try:

            resultado = self.geocoder.localizar(
                origem
            )

        except GeocodingError as error:

            raise RouteProcessingError(
                str(error)
            ) from error

        if resultado is None:

            raise RouteProcessingError(
                "Não foi possível localizar a origem com "
                "segurança. Confira rua, número, bairro, "
                "cidade, estado e CEP."
            )

        return resultado

    def _locate_deliveries(
        self,
        entregas,
        contexto: dict
    ):

        resultados: list[
            tuple[int, object, dict]
        ] = []

        erros: list[
            tuple[int, str, str]
        ] = []

        quantidade_workers = min(
            self.MAX_GEOCODING_WORKERS,
            len(entregas)
        )

        with ThreadPoolExecutor(
            max_workers=max(
                1,
                quantidade_workers
            )
        ) as executor:

            futures = {}

            for indice, entrega in enumerate(
                entregas,
                start=1
            ):

                future = executor.submit(
                    self.geocoder.localizar,
                    entrega.endereco,
                    contexto
                )

                futures[future] = (
                    indice,
                    entrega
                )

            for future in as_completed(
                futures
            ):

                indice, entrega = futures[
                    future
                ]

                try:

                    dados = future.result()

                except GeocodingError as error:

                    erros.append(
                        (
                            indice,
                            entrega.endereco,
                            str(error)
                        )
                    )

                    continue

                except Exception:

                    erros.append(
                        (
                            indice,
                            entrega.endereco,
                            "erro inesperado na localização"
                        )
                    )

                    continue

                if dados is None:

                    erros.append(
                        (
                            indice,
                            entrega.endereco,
                            "endereço não encontrado com segurança"
                        )
                    )

                    continue

                resultados.append(
                    (
                        indice,
                        entrega,
                        dados
                    )
                )

        if erros:

            erros.sort(
                key=lambda item: item[0]
            )

            detalhes = " | ".join(
                (
                    f"Entrega {indice}: "
                    f"{endereco} ({motivo})"
                )
                for indice, endereco, motivo
                in erros
            )

            raise RouteProcessingError(
                "Não foi possível localizar todas as "
                f"entregas. {detalhes}."
            )

        resultados.sort(
            key=lambda item: item[0]
        )

        entregas_validas = []

        for _, entrega, dados in resultados:

            entrega.latitude = dados[
                "latitude"
            ]

            entrega.longitude = dados[
                "longitude"
            ]

            entrega.bairro = dados.get(
                "bairro",
                ""
            )

            entrega.cidade = dados.get(
                "cidade",
                ""
            )

            entrega.estado = dados.get(
                "estado",
                ""
            )

            try:
                entrega.cep = dados.get(
                    "cep",
                    ""
                )
            except AttributeError:
                pass

            try:
                entrega.endereco_encontrado = dados.get(
                    "endereco_encontrado",
                    entrega.endereco
                )
            except AttributeError:
                pass

            entregas_validas.append(
                entrega
            )

        if not entregas_validas:

            raise RouteProcessingError(
                "Nenhuma entrega válida foi localizada."
            )

        return entregas_validas

    @staticmethod
    def _build_coordinates(
        origem_dados: dict,
        entregas
    ) -> list[list[float]]:

        coordenadas = [
            [
                float(
                    origem_dados["longitude"]
                ),
                float(
                    origem_dados["latitude"]
                )
            ]
        ]

        for entrega in entregas:

            coordenadas.append(
                [
                    float(
                        entrega.longitude
                    ),
                    float(
                        entrega.latitude
                    )
                ]
            )

        return coordenadas

    @staticmethod
    def _validate_matrix(
        matriz: dict,
        quantidade_pontos: int
    ) -> None:

        if not isinstance(
            matriz,
            dict
        ):

            raise RouteProcessingError(
                "O serviço de rotas retornou uma resposta inválida."
            )

        durations = matriz.get(
            "durations"
        )

        distances = matriz.get(
            "distances"
        )

        for nome, conteudo in (
            (
                "tempos",
                durations
            ),
            (
                "distâncias",
                distances
            )
        ):

            if (
                not isinstance(
                    conteudo,
                    list
                )
                or len(
                    conteudo
                ) != quantidade_pontos
            ):

                raise RouteProcessingError(
                    f"A matriz de {nome} retornada é inválida."
                )

            for linha in conteudo:

                if (
                    not isinstance(
                        linha,
                        list
                    )
                    or len(
                        linha
                    ) != quantidade_pontos
                ):

                    raise RouteProcessingError(
                        f"A matriz de {nome} retornada é inválida."
                    )