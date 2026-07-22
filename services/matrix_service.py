import openrouteservice

from config import Config


class MatrixService:

    def __init__(self):

        if (
            not Config.OPENROUTESERVICE_API_KEY
            or Config.OPENROUTESERVICE_API_KEY == "SUA_CHAVE_AQUI"
        ):
            raise ValueError(
                "A variável OPENROUTESERVICE_API_KEY não foi configurada."
            )

        self.client = openrouteservice.Client(
            key=Config.OPENROUTESERVICE_API_KEY
        )

    def calcular(
        self,
        coordenadas
    ):

        resultado = self.client.distance_matrix(
            locations=coordenadas,
            metrics=[
                "distance",
                "duration"
            ]
        )

        return resultado