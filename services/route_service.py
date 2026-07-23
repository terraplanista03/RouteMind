from optimizer.optimizer import Optimizer
from services.geocoder import Geocoder
from services.matrix_service import MatrixService
from services.route_formatter import RouteFormatter
from services.route_statistics import RouteStatistics
from services.validator import Validator


class RouteService:

    def __init__(self):

        self.validator = Validator()
        self.geocoder = Geocoder()
        self.matrix = MatrixService()
        self.optimizer = Optimizer()
        self.statistics = RouteStatistics()
        self.formatter = RouteFormatter()

    def processar(
        self,
        origem,
        enderecos
    ):

        entregas = self.validator.criar_lista(
            enderecos
        )

        origem_dados = self.geocoder.localizar(
            origem
        )

        if origem_dados is None:

            raise Exception(
                "Não foi possível localizar a origem. "
                "Confira o endereço e tente novamente."
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

        entregas_validas = []
        enderecos_invalidos = []

        for entrega in entregas:

            dados = self.geocoder.localizar(
                endereco=entrega.endereco,
                contexto=contexto_origem
            )

            if dados is None:

                enderecos_invalidos.append(
                    entrega.endereco
                )

                continue

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

            entregas_validas.append(
                entrega
            )

        if enderecos_invalidos:

            lista_invalidos = "; ".join(
                enderecos_invalidos
            )

            raise Exception(
                "Não foi possível localizar os seguintes "
                f"endereços: {lista_invalidos}."
            )

        if not entregas_validas:

            raise Exception(
                "Nenhum endereço válido foi encontrado."
            )

        coordenadas = [
            [
                origem_dados["longitude"],
                origem_dados["latitude"]
            ]
        ]

        for entrega in entregas_validas:

            coordenadas.append(
                [
                    entrega.longitude,
                    entrega.latitude
                ]
            )

        matriz = self.matrix.calcular(
            coordenadas
        )

        rotas_indices = self.optimizer.otimizar(
            matriz["durations"]
        )

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

        return (
            origem_dados,
            entregas_validas,
            matriz,
            analise,
            rotas
        )