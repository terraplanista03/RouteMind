import openrouteservice
from config import OPENROUTESERVICE_KEY


class Geocoder:

    def __init__(self):
        self.client = openrouteservice.Client(
            key=OPENROUTESERVICE_KEY
        )

    def localizar(self, endereco: str):

        try:

            resultado = self.client.pelias_search(
                text=endereco,
                size=1
            )

            if len(resultado["features"]) == 0:
                return None

            feature = resultado["features"][0]

            longitude, latitude = feature["geometry"]["coordinates"]

            propriedades = feature["properties"]

            return {
                "latitude": latitude,
                "longitude": longitude,
                "bairro": propriedades.get("borough", ""),
                "cidade": propriedades.get("locality", ""),
                "estado": propriedades.get("region", ""),
                "cep": propriedades.get("postalcode", ""),
                "pais": propriedades.get("country", "")
            }

        except Exception as erro:

            print(f"Erro ao localizar '{endereco}': {erro}")

            return None