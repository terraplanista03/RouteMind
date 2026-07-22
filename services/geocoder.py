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
            key=Config.OPENROUTESERVICE_API_KEY,
            timeout=10,
            retry_timeout=2,
            retry_over_query_limit=False
        )

    def localizar(
        self,
        endereco: str
    ):

        endereco = endereco.strip()

        if not endereco:
            return None

        try:

            resultado = self.client.pelias_search(
                text=endereco,
                size=1,
                boundary_country=["BR"]
            )

            features = resultado.get(
                "features",
                []
            )

            if not features:
                return None

            feature = features[0]

            coordenadas = feature.get(
                "geometry",
                {}
            ).get(
                "coordinates",
                []
            )

            if len(coordenadas) < 2:
                return None

            longitude, latitude = coordenadas

            propriedades = feature.get(
                "properties",
                {}
            )

            endereco_encontrado = propriedades.get(
                "label",
                endereco
            )

            return {
                "latitude": latitude,
                "longitude": longitude,
                "endereco_encontrado": endereco_encontrado,
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
                f"Erro ao localizar '{endereco}': {erro}",
                flush=True
            )

            return None