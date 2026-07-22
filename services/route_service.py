from services.validator import Validator
from services.geocoder import Geocoder
from services.matrix_service import MatrixService
from services.route_statistics import RouteStatistics
from services.route_formatter import RouteFormatter
from optimizer.optimizer import Optimizer


class RouteService:

    def __init__(self):

        self.validator = Validator()
        self.geocoder = Geocoder()
        self.matrix = MatrixService()
        self.optimizer = Optimizer()
        self.statistics = RouteStatistics()
        self.formatter = RouteFormatter()

    def processar(self, origem, enderecos):

        entregas = self.validator.criar_lista(enderecos)

        origem_dados = self.geocoder.localizar(origem)

        if origem_dados is None:
            raise Exception(
                "Não foi possível localizar a origem."
            )

        entregas_validas = []

        for entrega in entregas:

            dados = self.geocoder.localizar(
                entrega.endereco
            )

            if dados is None:
                continue

            entrega.latitude = dados["latitude"]
            entrega.longitude = dados["longitude"]
            entrega.bairro = dados["bairro"]
            entrega.cidade = dados["cidade"]
            entrega.estado = dados["estado"]

            entregas_validas.append(entrega)

        if len(entregas_validas) == 0:
            raise Exception(
                "Nenhum endereço válido encontrado."
            )

        coordenadas = [
            [
                origem_dados["longitude"],
                origem_dados["latitude"]
            ]
        ]

        for entrega in entregas_validas:

            coordenadas.append([
                entrega.longitude,
                entrega.latitude
            ])

        matriz = self.matrix.calcular(
            coordenadas
        )

        rotas_indices = self.optimizer.otimizar(
            matriz["durations"]
        )

        analise = self.statistics.calcular(
            matriz["durations"],
            rotas_indices,
            matriz["distances"]
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