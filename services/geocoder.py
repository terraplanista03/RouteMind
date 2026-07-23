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

            resultado = self._buscar_estruturado(
                componentes
            )

            if resultado:
                return resultado

        return self._buscar_texto_livre(
            endereco=endereco,
            componentes=componentes,
            contexto=contexto
        )

    def _buscar_estruturado(
        self,
        componentes: dict
    ):

        logradouro = componentes[
            "logradouro"
        ]

        numero = componentes[
            "numero"
        ]

        parametros = {
            "api_key": self.chave,
            "address": (
                f"{logradouro}, {numero}"
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
            "size": 10
        }

        features = self._consultar(
            url=self.URL_ESTRUTURADA,
            parametros=parametros
        )

        return self._selecionar_resultado(
            features=features,
            componentes=componentes,
            exigir_numero=True
        )

    def _buscar_texto_livre(
        self,
        endereco: str,
        componentes: dict | None,
        contexto: dict | None
    ):

        consulta = endereco

        if componentes is None and contexto:

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

            complemento = ", ".join(
                parte
                for parte in [
                    cidade,
                    estado,
                    "Brasil"
                ]
                if parte
            )

            if complemento:

                consulta = (
                    f"{endereco}, {complemento}"
                )

        parametros = {
            "api_key": self.chave,
            "text": consulta,
            "boundary.country": "BR",
            "size": 10,
            "lang": "pt"
        }

        features = self._consultar(
            url=self.URL_BUSCA_LIVRE,
            parametros=parametros
        )

        if componentes:

            return self._selecionar_resultado(
                features=features,
                componentes=componentes,
                exigir_numero=True
            )

        return self._selecionar_resultado(
            features=features,
            componentes=None,
            exigir_numero=False
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
                "demais para responder. Tente novamente."
            ) from erro

        except requests.RequestException as erro:

            print(
                f"Erro no geocodificador: {erro}",
                flush=True
            )

            raise Exception(
                "Não foi possível consultar o serviço "
                "de localização dos endereços."
            ) from erro

        except ValueError as erro:

            raise Exception(
                "O serviço de localização retornou "
                "uma resposta inválida."
            ) from erro

    def _selecionar_resultado(
        self,
        features: list,
        componentes: dict | None,
        exigir_numero: bool
    ):

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

            pontuacao = self._pontuar(
                propriedades=propriedades,
                componentes=componentes
            )

            numero_valido = (
                self._numero_corresponde(
                    propriedades=propriedades,
                    componentes=componentes
                )
            )

            if (
                exigir_numero
                and not numero_valido
            ):
                continue

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

        melhor_feature = candidatos[
            0
        ][
            1
        ]

        return self._formatar_resultado(
            melhor_feature
        )

    def _pontuar(
        self,
        propriedades: dict,
        componentes: dict | None
    ):

        pontuacao = 0

        camada = self._normalizar(
            propriedades.get(
                "layer",
                ""
            )
        )

        if camada == "address":
            pontuacao += 300

        elif camada == "venue":
            pontuacao += 80

        elif camada == "street":
            pontuacao += 20

        confianca = propriedades.get(
            "confidence",
            0
        )

        try:

            pontuacao += (
                float(confianca) * 50
            )

        except (
            TypeError,
            ValueError
        ):
            pass

        if not componentes:
            return pontuacao

        numero_desejado = self._normalizar_numero(
            componentes.get(
                "numero",
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

        if (
            numero_desejado
            and numero_resultado
            == numero_desejado
        ):
            pontuacao += 500

        cep_desejado = self._normalizar_cep(
            componentes.get(
                "cep",
                ""
            )
        )

        cep_resultado = self._normalizar_cep(
            propriedades.get(
                "postalcode",
                ""
            )
        )

        if (
            cep_desejado
            and cep_resultado
            == cep_desejado
        ):
            pontuacao += 350

        cidade_desejada = self._normalizar(
            componentes.get(
                "cidade",
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

        if (
            cidade_desejada
            and cidade_desejada
            == cidade_resultado
        ):
            pontuacao += 200

        estado_desejado = self._normalizar(
            componentes.get(
                "estado",
                ""
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

        if (
            estado_desejado
            and (
                estado_desejado
                == estado_resultado
                or estado_desejado
                in estado_resultado
            )
        ):
            pontuacao += 100

        bairro_desejado = self._normalizar(
            componentes.get(
                "bairro",
                ""
            )
        )

        bairro_resultado = self._normalizar(
            propriedades.get(
                "neighbourhood",
                propriedades.get(
                    "borough",
                    propriedades.get(
                        "localadmin",
                        ""
                    )
                )
            )
        )

        if (
            bairro_desejado
            and bairro_desejado
            == bairro_resultado
        ):
            pontuacao += 100

        return pontuacao

    def _numero_corresponde(
        self,
        propriedades: dict,
        componentes: dict | None
    ):

        if not componentes:
            return True

        numero_desejado = (
            self._normalizar_numero(
                componentes.get(
                    "numero",
                    ""
                )
            )
        )

        if not numero_desejado:
            return True

        numero_resultado = (
            self._normalizar_numero(
                propriedades.get(
                    "housenumber",
                    ""
                )
            )
        )

        if (
            numero_resultado
            == numero_desejado
        ):
            return True

        label = self._normalizar(
            propriedades.get(
                "label",
                ""
            )
        )

        return bool(
            re.search(
                r"\b"
                + re.escape(
                    numero_desejado
                )
                + r"\b",
                label
            )
        )

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

        componentes = resultado.groupdict()

        return {
            chave: valor.strip()
            for chave, valor
            in componentes.items()
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