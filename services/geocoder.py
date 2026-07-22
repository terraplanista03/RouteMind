import openrouteservice

from config import Config


class Geocoder:

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

    def localizar(
        self,
        endereco: str
    ):

        try:

            resultado = self.client.pelias_search(
                text=endereco,
                size=1
            )

            if (
                not resultado.get("features")
            ):

                return None

            feature = resultado["features"][0]

            longitude, latitude = (
                feature["geometry"]["coordinates"]
            )

            propriedades = feature.get(
                "properties",
                {}
            )

            return {
                "latitude": latitude,
                "longitude": longitude,
                "bairro": propriedades.get(
                    "borough",
                    propriedades.get(
                        "neighbourhood",
                        ""
                    )
                ),
                "cidade": propriedades.get(
                    "locality",
                    propriedades.get(
                        "county",
                        ""
                    )
                ),
                "estado": propriedades.get(
                    "region",
                    ""
                ),
                "cep": propriedades.get(
                    "postalcode",
                    ""
                ),
                "pais": propriedades.get(
                    "country",
                    ""
                )
            }

        except Exception as erro:

            print(
                f"Erro ao localizar '{endereco}': {erro}"
            )

            return None