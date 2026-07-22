import openrouteservice

from config import OPENROUTESERVICE_KEY


class MatrixService:

    def __init__(self):

        self.client = openrouteservice.Client(
            key=OPENROUTESERVICE_KEY
        )

    def calcular(self, coordenadas):

        resultado = self.client.distance_matrix(
            locations=coordenadas,
            metrics=["distance", "duration"]
        )

        return resultado