import re
import unicodedata

import requests

from config import Config


class Geocoder:

    URL_ESTRUTURADA = (
        "https://api.openrouteservice.org/"
        "geocode/search/structured"
    )

    URL_BUSCA_LIVRE = (
        "https://api.openrouteservice.org/"
        "geocode/search"
    )

    def __init__(self):

        chave = Config.OPENROUTESERVICE_API_KEY

        if (
            not chave
            or chave == "SUA_CHAVE_AQUI"
        ):
            raise ValueError(
                "A variável OPENROUTESERVICE_API_KEY "
                "não foi configurada."
            )

        self.chave = chave
        self.sessao = requests.Session()

    def localizar(
        self,
        endereco: str,
        contexto: dict | None = None
    ):

        endereco = self._limpar_texto(
            endereco
        )

        if not endereco:
            return None

        componentes = self._separar_endereco(
            endereco
        )

        if componentes:

            features = self._buscar_estruturado(
                componentes
            )

            resultado = self._selecionar_resultado_exato(
                features=features,
                componentes=componentes
            )

            if resultado:
                return resultado

            features = self._buscar_texto_livre(
                endereco
            )

            return self._selecionar_resultado_exato(
                features=features,
                componentes=componentes
            )

        consulta = endereco

        if contexto:

            cidade = str(
                contexto.get(
                    "cidade",
                    ""
                )
            ).strip()

            estado = str(
                contexto.get(
                    "estado",
                    ""
                )
            ).strip()

            partes = [
                parte
                for parte in [
                    consulta,
                    cidade,
                    estado,
                    "Brasil"
                ]
                if parte
            ]

            consulta = ", ".join(
                partes
            )

        features = self._buscar_texto_livre(
            consulta
        )

        return self._selecionar_resultado_simples(
            features
        )

    def _buscar_estruturado(
        self,
        componentes: dict
    ):

        parametros = {
            "api_key": self.chave,
            "address": (
                componentes["logradouro"]
                + ", "
                + componentes["numero"]
            ),
            "neighbourhood": componentes[
                "bairro"
            ],
            "locality": componentes[
                "cidade"
            ],
            "region": componentes[
                "estado"
            ],
            "postalcode": componentes[
                "cep"
            ],
            "country": "Brasil",
            "boundary.country": "BR",
            "size": 20
        }

        return self._consultar(
            url=self.URL_ESTRUTURADA,
            parametros=parametros
        )

    def _buscar_texto_livre(
        self,
        endereco: str
    ):

        parametros = {
            "api_key": self.chave,
            "text": endereco,
            "boundary.country": "BR",
            "size": 20,
            "lang": "pt"
        }

        return self._consultar(
            url=self.URL_BUSCA_LIVRE,
            parametros=parametros
        )

    def _consultar(
        self,
        url: str,
        parametros: dict
    ):

        try:

            resposta = self.sessao.get(
                url,
                params=parametros,
                timeout=15
            )

            resposta.raise_for_status()

            dados = resposta.json()

            return dados.get(
                "features",
                []
            )

        except requests.Timeout as erro:

            raise Exception(
                "O serviço de localização demorou "
                "demais para responder."
            ) from erro

        except requests.RequestException as erro:

            raise Exception(
                "Não foi possível consultar o serviço "
                "de localização."
            ) from erro

        except ValueError as erro:

            raise Exception(
                "O serviço de localização retornou "
                "uma resposta inválida."
            ) from erro

    def _selecionar_resultado_exato(
        self,
        features: list,
        componentes: dict
    ):

        numero_desejado = self._normalizar_numero(
            componentes["numero"]
        )

        cep_desejado = self._normalizar_cep(
            componentes["cep"]
        )

        cidade_desejada = self._normalizar(
            componentes["cidade"]
        )

        estado_desejado = self._normalizar(
            componentes["estado"]
        )

        candidatos = []

        for feature in features:

            propriedades = feature.get(
                "properties",
                {}
            )

            coordenadas = feature.get(
                "geometry",
                {}
            ).get(
                "coordinates",
                []
            )

            if len(coordenadas) < 2:
                continue

            camada = self._normalizar(
                propriedades.get(
                    "layer",
                    ""
                )
            )

            precisao = self._normalizar(
                propriedades.get(
                    "accuracy",
                    ""
                )
            )

            numero_resultado = (
                self._normalizar_numero(
                    propriedades.get(
                        "housenumber",
                        ""
                    )
                )
            )

            cep_resultado = self._normalizar_cep(
                propriedades.get(
                    "postalcode",
                    ""
                )
            )

            cidade_resultado = self._normalizar(
                propriedades.get(
                    "locality",
                    propriedades.get(
                        "county",
                        ""
                    )
                )
            )

            estado_resultado = self._normalizar(
                propriedades.get(
                    "region_a",
                    propriedades.get(
                        "region",
                        ""
                    )
                )
            )

            # Exige um resultado realmente classificado
            # como endereço, e não rua ou estabelecimento.
            if camada != "address":
                continue

            # O número retornado pela API precisa ser
            # exatamente igual ao número digitado.
            if numero_resultado != numero_desejado:
                continue

            if (
                cidade_desejada
                and cidade_resultado
                and cidade_desejada
                != cidade_resultado
            ):
                continue

            if (
                estado_desejado
                and estado_resultado
                and estado_desejado
                not in estado_resultado
                and estado_resultado
                not in estado_desejado
            ):
                continue

            pontuacao = 1000

            if (
                cep_desejado
                and cep_resultado
                == cep_desejado
            ):
                pontuacao += 500

            if precisao == "point":
                pontuacao += 500

            confianca = propriedades.get(
                "confidence",
                0
            )

            try:
                pontuacao += (
                    float(confianca) * 100
                )
            except (
                TypeError,
                ValueError
            ):
                pass

            candidatos.append(
                (
                    pontuacao,
                    feature
                )
            )

        if not candidatos:
            return None

        candidatos.sort(
            key=lambda item: item[0],
            reverse=True
        )

        return self._formatar_resultado(
            candidatos[0][1]
        )

    def _selecionar_resultado_simples(
        self,
        features: list
    ):

        if not features:
            return None

        for feature in features:

            coordenadas = feature.get(
                "geometry",
                {}
            ).get(
                "coordinates",
                []
            )

            if len(coordenadas) >= 2:
                return self._formatar_resultado(
                    feature
                )

        return None

    def _formatar_resultado(
        self,
        feature: dict
    ):

        propriedades = feature.get(
            "properties",
            {}
        )

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

        return {
            "latitude": float(latitude),
            "longitude": float(longitude),
            "endereco_encontrado": propriedades.get(
                "label",
                ""
            ),
            "logradouro": propriedades.get(
                "street",
                propriedades.get(
                    "name",
                    ""
                )
            ),
            "numero": str(
                propriedades.get(
                    "housenumber",
                    ""
                )
            ),
            "bairro": propriedades.get(
                "neighbourhood",
                propriedades.get(
                    "borough",
                    propriedades.get(
                        "localadmin",
                        ""
                    )
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
            ),
            "tipo_resultado": propriedades.get(
                "layer",
                ""
            ),
            "precisao": propriedades.get(
                "accuracy",
                ""
            )
        }

    def _separar_endereco(
        self,
        endereco: str
    ):

        padrao = re.compile(
            r"""
            ^\s*
            (?P<logradouro>.+?)
            \s*,\s*
            (?P<numero>\d+[A-Za-z]?)
            \s*-\s*
            (?P<bairro>.+?)
            \s*,\s*
            (?P<cidade>.+?)
            \s*-\s*
            (?P<estado>[A-Za-z]{2})
            \s*,\s*
            (?P<cep>\d{5}-?\d{3})
            \s*$
            """,
            re.VERBOSE
        )

        resultado = padrao.match(
            endereco
        )

        if not resultado:
            return None

        return {
            chave: valor.strip()
            for chave, valor
            in resultado.groupdict().items()
        }

    @staticmethod
    def _limpar_texto(
        texto
    ):

        texto = str(
            texto
            or ""
        ).strip()

        texto = re.sub(
            r"\s+",
            " ",
            texto
        )

        texto = re.sub(
            r"\s*,\s*",
            ", ",
            texto
        )

        texto = re.sub(
            r"\s*-\s*",
            " - ",
            texto
        )

        return texto

    @staticmethod
    def _normalizar(
        texto
    ):

        texto = str(
            texto
            or ""
        ).lower()

        texto = unicodedata.normalize(
            "NFKD",
            texto
        )

        texto = "".join(
            caractere
            for caractere in texto
            if not unicodedata.combining(
                caractere
            )
        )

        texto = re.sub(
            r"[^a-z0-9]+",
            " ",
            texto
        )

        return " ".join(
            texto.split()
        )

    @staticmethod
    def _normalizar_numero(
        numero
    ):

        return re.sub(
            r"[^0-9a-z]",
            "",
            str(
                numero
                or ""
            ).lower()
        )

    @staticmethod
    def _normalizar_cep(
        cep
    ):

        return re.sub(
            r"\D",
            "",
            str(
                cep
                or ""
            )
        )