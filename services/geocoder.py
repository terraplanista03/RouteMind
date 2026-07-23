import re
import unicodedata

import requests

from config import Config


class Geocoder:

    URL_GEOCODIFICACAO = (
        "https://api.openrouteservice.org/geocode/search"
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

        endereco = self._limpar_endereco(
            endereco
        )

        if not endereco:
            return None

        consultas = self._gerar_consultas(
            endereco=endereco,
            contexto=contexto
        )

        melhores_resultados = []

        for consulta in consultas:

            resultados = self._consultar_api(
                consulta
            )

            for feature in resultados:

                pontuacao = self._calcular_pontuacao(
                    feature=feature,
                    endereco_original=endereco,
                    contexto=contexto
                )

                melhores_resultados.append(
                    (
                        pontuacao,
                        feature
                    )
                )

        if not melhores_resultados:
            return None

        melhores_resultados.sort(
            key=lambda item: item[0],
            reverse=True
        )

        _, melhor_feature = (
            melhores_resultados[0]
        )

        return self._formatar_resultado(
            feature=melhor_feature,
            endereco_original=endereco
        )

    def _consultar_api(
        self,
        consulta: str
    ):

        parametros = {
            "api_key": self.chave,
            "text": consulta,
            "size": 10,
            "lang": "pt"
        }

        try:

            resposta = self.sessao.get(
                self.URL_GEOCODIFICACAO,
                params=parametros,
                timeout=15
            )

            resposta.raise_for_status()

            dados = resposta.json()

            return dados.get(
                "features",
                []
            )

        except requests.RequestException as erro:

            print(
                "Erro ao consultar o geocodificador "
                f"para '{consulta}': {erro}",
                flush=True
            )

            return []

        except ValueError as erro:

            print(
                "Resposta inválida do geocodificador "
                f"para '{consulta}': {erro}",
                flush=True
            )

            return []

    def _gerar_consultas(
        self,
        endereco: str,
        contexto: dict | None
    ):

        consultas = [
            endereco
        ]

        cidade = ""
        estado = ""
        pais = "Brasil"

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

            pais_contexto = str(
                contexto.get(
                    "pais",
                    ""
                )
            ).strip()

            if pais_contexto:
                pais = pais_contexto

        partes_contexto = [
            parte
            for parte in [
                cidade,
                estado,
                pais
            ]
            if parte
        ]

        if partes_contexto:

            consulta_com_contexto = (
                endereco
                + ", "
                + ", ".join(
                    partes_contexto
                )
            )

            consultas.append(
                consulta_com_contexto
            )

        if (
            "brasil"
            not in self._normalizar_texto(
                endereco
            )
        ):

            consultas.append(
                endereco + ", Brasil"
            )

        numero = self._extrair_numero(
            endereco
        )

        if numero:

            endereco_sem_numero = (
                self._remover_numero(
                    endereco,
                    numero
                )
            )

            if endereco_sem_numero:

                consultas.append(
                    f"{endereco_sem_numero}, {numero}, Brasil"
                )

                consultas.append(
                    f"{numero}, {endereco_sem_numero}, Brasil"
                )

        consultas_unicas = []

        for consulta in consultas:

            consulta = self._limpar_endereco(
                consulta
            )

            if (
                consulta
                and consulta not in consultas_unicas
            ):
                consultas_unicas.append(
                    consulta
                )

        return consultas_unicas

    def _calcular_pontuacao(
        self,
        feature: dict,
        endereco_original: str,
        contexto: dict | None
    ):

        propriedades = feature.get(
            "properties",
            {}
        )

        pontuacao = 0.0

        camada = self._normalizar_texto(
            propriedades.get(
                "layer",
                ""
            )
        )

        if camada == "address":
            pontuacao += 100

        elif camada == "venue":
            pontuacao += 70

        elif camada == "street":
            pontuacao += 30

        numero_procurado = self._extrair_numero(
            endereco_original
        )

        numero_resultado = str(
            propriedades.get(
                "housenumber",
                ""
            )
        ).strip()

        label = self._normalizar_texto(
            propriedades.get(
                "label",
                ""
            )
        )

        if numero_procurado:

            if (
                self._normalizar_numero(
                    numero_resultado
                )
                == self._normalizar_numero(
                    numero_procurado
                )
            ):
                pontuacao += 150

            elif self._numero_esta_no_texto(
                numero_procurado,
                label
            ):
                pontuacao += 90

            elif not numero_resultado:
                pontuacao -= 40

            else:
                pontuacao -= 80

        pais = self._normalizar_texto(
            propriedades.get(
                "country",
                ""
            )
        )

        codigo_pais = self._normalizar_texto(
            propriedades.get(
                "country_a",
                ""
            )
        )

        if (
            pais == "brasil"
            or codigo_pais in {
                "br",
                "bra"
            }
        ):
            pontuacao += 50

        if contexto:

            cidade_contexto = (
                self._normalizar_texto(
                    contexto.get(
                        "cidade",
                        ""
                    )
                )
            )

            estado_contexto = (
                self._normalizar_texto(
                    contexto.get(
                        "estado",
                        ""
                    )
                )
            )

            cidade_resultado = (
                self._normalizar_texto(
                    propriedades.get(
                        "locality",
                        propriedades.get(
                            "county",
                            ""
                        )
                    )
                )
            )

            estado_resultado = (
                self._normalizar_texto(
                    propriedades.get(
                        "region",
                        ""
                    )
                )
            )

            if (
                cidade_contexto
                and cidade_contexto
                == cidade_resultado
            ):
                pontuacao += 60

            if (
                estado_contexto
                and estado_contexto
                == estado_resultado
            ):
                pontuacao += 40

        confianca = propriedades.get(
            "confidence",
            0
        )

        try:
            pontuacao += float(
                confianca
            ) * 20

        except (
            TypeError,
            ValueError
        ):
            pass

        return pontuacao

    def _formatar_resultado(
        self,
        feature: dict,
        endereco_original: str
    ):

        geometria = feature.get(
            "geometry",
            {}
        )

        coordenadas = geometria.get(
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

        numero_digitado = self._extrair_numero(
            endereco_original
        )

        numero_encontrado = str(
            propriedades.get(
                "housenumber",
                ""
            )
        ).strip()

        numero_confirmado = True

        if numero_digitado:

            numero_confirmado = (
                self._normalizar_numero(
                    numero_digitado
                )
                == self._normalizar_numero(
                    numero_encontrado
                )
            )

            if (
                not numero_encontrado
                and self._numero_esta_no_texto(
                    numero_digitado,
                    propriedades.get(
                        "label",
                        ""
                    )
                )
            ):
                numero_confirmado = True

        return {
            "latitude": float(latitude),
            "longitude": float(longitude),
            "endereco_original": endereco_original,
            "endereco_encontrado": propriedades.get(
                "label",
                endereco_original
            ),
            "logradouro": propriedades.get(
                "street",
                propriedades.get(
                    "name",
                    ""
                )
            ),
            "numero": (
                numero_encontrado
                or numero_digitado
                or ""
            ),
            "numero_confirmado": numero_confirmado,
            "bairro": propriedades.get(
                "borough",
                propriedades.get(
                    "neighbourhood",
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

    @staticmethod
    def _limpar_endereco(
        endereco: str
    ):

        endereco = str(
            endereco
            or ""
        ).strip()

        endereco = re.sub(
            r"\s+",
            " ",
            endereco
        )

        endereco = re.sub(
            r"\s*,\s*",
            ", ",
            endereco
        )

        return endereco.strip(
            " ,;-"
        )

    @staticmethod
    def _normalizar_texto(
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
    def _extrair_numero(
        endereco: str
    ):

        endereco_sem_cep = re.sub(
            r"\b\d{5}-?\d{3}\b",
            " ",
            endereco
        )

        padroes = [
            r"\bn[º°o.]?\s*(\d+[a-zA-Z]?)\b",
            r"\bnumero\s*(\d+[a-zA-Z]?)\b",
            r",\s*(\d+[a-zA-Z]?)\b",
            r"\b(\d+[a-zA-Z]?)\b"
        ]

        for padrao in padroes:

            resultado = re.search(
                padrao,
                endereco_sem_cep,
                flags=re.IGNORECASE
            )

            if resultado:

                numero = resultado.group(
                    1
                ).strip()

                if len(numero) <= 7:
                    return numero

        return ""

    @staticmethod
    def _remover_numero(
        endereco: str,
        numero: str
    ):

        resultado = re.sub(
            (
                r"\b(?:numero|n[º°o.]?)?\s*"
                + re.escape(numero)
                + r"\b"
            ),
            " ",
            endereco,
            count=1,
            flags=re.IGNORECASE
        )

        resultado = re.sub(
            r"\s*,\s*,+",
            ", ",
            resultado
        )

        resultado = re.sub(
            r"\s+",
            " ",
            resultado
        )

        return resultado.strip(
            " ,;-"
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

    def _numero_esta_no_texto(
        self,
        numero: str,
        texto: str
    ):

        numero = self._normalizar_numero(
            numero
        )

        texto = self._normalizar_texto(
            texto
        )

        return bool(
            re.search(
                r"\b"
                + re.escape(numero)
                + r"\b",
                texto
            )
        )