import re
import unicodedata
from dataclasses import dataclass
from typing import Any

import requests

from config import Config


class GeocodingError(Exception):
    """Erro controlado durante a localização de um endereço."""


@dataclass
class AddressComponents:
    logradouro: str = ""
    numero: str = ""
    bairro: str = ""
    cidade: str = ""
    estado: str = ""
    cep: str = ""
    pais: str = "Brasil"


class Geocoder:

    FREE_SEARCH_URL = (
        "https://api.openrouteservice.org/geocode/search"
    )

    STRUCTURED_SEARCH_URL = (
        "https://api.openrouteservice.org/"
        "geocode/search/structured"
    )

    REQUEST_TIMEOUT = 12
    MAX_RESULTS = 15
    MINIMUM_SCORE = 100

    def __init__(self):

        api_key = str(
            Config.OPENROUTESERVICE_API_KEY or ""
        ).strip()

        if (
            not api_key
            or api_key == "SUA_CHAVE_AQUI"
        ):
            raise ValueError(
                "A chave da OpenRouteService não foi configurada."
            )

        self.api_key = api_key

    def localizar(
        self,
        endereco: str,
        contexto: dict | None = None
    ) -> dict | None:

        endereco_original = self._clean_text(
            endereco
        )

        if not endereco_original:
            return None

        componentes = self._parse_address(
            endereco_original
        )

        if contexto:
            componentes = self._apply_context(
                componentes,
                contexto
            )

        candidatos: list[dict] = []

        if componentes.logradouro:

            candidatos.extend(
                self._structured_search(
                    componentes
                )
            )

        consultas = self._build_free_queries(
            endereco_original,
            componentes
        )

        for consulta in consultas:

            candidatos.extend(
                self._free_search(
                    consulta
                )
            )

        candidatos = self._remove_duplicates(
            candidatos
        )

        melhor = self._select_best_candidate(
            candidatos=candidatos,
            componentes=componentes,
            endereco_original=endereco_original
        )

        if melhor is None:
            return None

        return self._format_result(
            melhor,
            endereco_original
        )

    def _structured_search(
        self,
        componentes: AddressComponents
    ) -> list[dict]:

        address = componentes.logradouro

        if componentes.numero:
            address += f", {componentes.numero}"

        params = {
            "api_key": self.api_key,
            "address": address,
            "locality": componentes.cidade,
            "region": componentes.estado,
            "postalcode": componentes.cep,
            "country": componentes.pais or "Brasil",
            "boundary.country": "BR",
            "size": self.MAX_RESULTS
        }

        if componentes.bairro:
            params["neighbourhood"] = componentes.bairro

        return self._request(
            self.STRUCTURED_SEARCH_URL,
            params
        )

    def _free_search(
        self,
        consulta: str
    ) -> list[dict]:

        params = {
            "api_key": self.api_key,
            "text": consulta,
            "boundary.country": "BR",
            "size": self.MAX_RESULTS,
            "lang": "pt"
        }

        return self._request(
            self.FREE_SEARCH_URL,
            params
        )

    def _request(
        self,
        url: str,
        params: dict
    ) -> list[dict]:

        clean_params = {
            key: value
            for key, value in params.items()
            if value not in (
                None,
                ""
            )
        }

        try:

            response = requests.get(
                url,
                params=clean_params,
                timeout=self.REQUEST_TIMEOUT
            )

        except requests.Timeout as error:

            raise GeocodingError(
                "O serviço de localização demorou demais "
                "para responder. Tente novamente."
            ) from error

        except requests.RequestException as error:

            raise GeocodingError(
                "Não foi possível acessar o serviço de "
                "localização dos endereços."
            ) from error

        if response.status_code == 401:

            raise GeocodingError(
                "A chave da OpenRouteService foi recusada."
            )

        if response.status_code == 403:

            raise GeocodingError(
                "A chave da OpenRouteService não possui "
                "permissão para localizar endereços."
            )

        if response.status_code == 429:

            raise GeocodingError(
                "O limite de consultas da OpenRouteService "
                "foi atingido. Aguarde e tente novamente."
            )

        try:
            response.raise_for_status()
        except requests.HTTPError as error:
            raise GeocodingError(
                "O serviço de localização retornou um erro "
                f"temporário: HTTP {response.status_code}."
            ) from error

        try:
            data = response.json()
        except ValueError as error:
            raise GeocodingError(
                "O serviço de localização retornou uma "
                "resposta inválida."
            ) from error

        features = data.get(
            "features",
            []
        )

        if not isinstance(
            features,
            list
        ):
            return []

        return features

    def _select_best_candidate(
        self,
        candidatos: list[dict],
        componentes: AddressComponents,
        endereco_original: str
    ) -> dict | None:

        if not candidatos:
            return None

        avaliados = []

        for candidato in candidatos:

            score = self._score_candidate(
                candidato=candidato,
                componentes=componentes,
                endereco_original=endereco_original
            )

            if score is None:
                continue

            avaliados.append(
                (
                    score,
                    candidato
                )
            )

        if not avaliados:
            return None

        avaliados.sort(
            key=lambda item: item[0],
            reverse=True
        )

        melhor_score, melhor_candidato = avaliados[0]

        if melhor_score < self.MINIMUM_SCORE:
            return None

        return melhor_candidato

    def _score_candidate(
        self,
        candidato: dict,
        componentes: AddressComponents,
        endereco_original: str
    ) -> float | None:

        geometry = candidato.get(
            "geometry",
            {}
        )

        coordinates = geometry.get(
            "coordinates",
            []
        )

        if (
            not isinstance(
                coordinates,
                list
            )
            or len(coordinates) < 2
        ):
            return None

        properties = candidato.get(
            "properties",
            {}
        )

        country = self._normalize(
            properties.get(
                "country",
                ""
            )
        )

        country_code = self._normalize(
            properties.get(
                "country_a",
                ""
            )
        )

        if (
            country
            and country != "brasil"
            and country_code not in {
                "br",
                "bra"
            }
        ):
            return None

        score = 0.0

        layer = self._normalize(
            properties.get(
                "layer",
                ""
            )
        )

        layer_scores = {
            "address": 350,
            "venue": 180,
            "street": 80,
            "neighbourhood": 20,
            "locality": 10
        }

        score += layer_scores.get(
            layer,
            0
        )

        confidence = properties.get(
            "confidence",
            0
        )

        try:
            score += float(
                confidence
            ) * 80
        except (
            TypeError,
            ValueError
        ):
            pass

        label = self._normalize(
            properties.get(
                "label",
                ""
            )
        )

        desired_number = self._normalize_number(
            componentes.numero
        )

        result_number = self._normalize_number(
            properties.get(
                "housenumber",
                ""
            )
        )

        if desired_number:

            if result_number == desired_number:
                score += 700

            elif self._number_in_text(
                desired_number,
                label
            ):
                score += 450

            elif result_number:
                score -= 800

            else:
                score -= 250

        desired_postal_code = self._normalize_postal_code(
            componentes.cep
        )

        result_postal_code = self._normalize_postal_code(
            properties.get(
                "postalcode",
                ""
            )
        )

        if desired_postal_code:

            if (
                result_postal_code
                == desired_postal_code
            ):
                score += 500

            elif result_postal_code:
                score -= 250

        desired_city = self._normalize(
            componentes.cidade
        )

        result_city = self._normalize(
            properties.get(
                "locality",
                properties.get(
                    "county",
                    ""
                )
            )
        )

        if desired_city:

            if self._same_or_contains(
                desired_city,
                result_city
            ):
                score += 300

            elif result_city:
                score -= 600

        desired_state = self._normalize_state(
            componentes.estado
        )

        result_state = self._normalize_state(
            properties.get(
                "region_a",
                properties.get(
                    "region",
                    ""
                )
            )
        )

        if desired_state:

            if (
                result_state
                and desired_state == result_state
            ):
                score += 250

            elif result_state:
                score -= 500

        desired_neighbourhood = self._normalize(
            componentes.bairro
        )

        result_neighbourhood = self._normalize(
            properties.get(
                "neighbourhood",
                properties.get(
                    "borough",
                    properties.get(
                        "localadmin",
                        ""
                    )
                )
            )
        )

        if desired_neighbourhood:

            if self._same_or_contains(
                desired_neighbourhood,
                result_neighbourhood
            ):
                score += 180

        desired_street = self._normalize_street(
            componentes.logradouro
        )

        result_street = self._normalize_street(
            properties.get(
                "street",
                properties.get(
                    "name",
                    ""
                )
            )
        )

        if desired_street:

            similarity = self._token_similarity(
                desired_street,
                result_street or label
            )

            score += similarity * 350

            if similarity < 0.35:
                score -= 300

        original_normalized = self._normalize(
            endereco_original
        )

        score += (
            self._token_similarity(
                original_normalized,
                label
            )
            * 100
        )

        return score

    def _format_result(
        self,
        feature: dict,
        endereco_original: str
    ) -> dict:

        properties = feature.get(
            "properties",
            {}
        )

        longitude, latitude = feature[
            "geometry"
        ][
            "coordinates"
        ][
            :2
        ]

        return {
            "latitude": float(latitude),
            "longitude": float(longitude),
            "endereco_original": endereco_original,
            "endereco_encontrado": properties.get(
                "label",
                endereco_original
            ),
            "logradouro": properties.get(
                "street",
                properties.get(
                    "name",
                    ""
                )
            ),
            "numero": str(
                properties.get(
                    "housenumber",
                    ""
                )
            ),
            "bairro": properties.get(
                "neighbourhood",
                properties.get(
                    "borough",
                    properties.get(
                        "localadmin",
                        ""
                    )
                )
            ),
            "cidade": properties.get(
                "locality",
                properties.get(
                    "county",
                    ""
                )
            ),
            "estado": properties.get(
                "region",
                ""
            ),
            "cep": properties.get(
                "postalcode",
                ""
            ),
            "pais": properties.get(
                "country",
                "Brasil"
            ),
            "tipo_resultado": properties.get(
                "layer",
                ""
            ),
            "confianca": properties.get(
                "confidence",
                0
            )
        }

    def _parse_address(
        self,
        endereco: str
    ) -> AddressComponents:

        patterns = [
            re.compile(
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
            ),
            re.compile(
                r"""
                ^\s*
                (?P<logradouro>.+?)
                \s*,\s*
                (?P<numero>\d+[A-Za-z]?)
                \s*,\s*
                (?P<bairro>.+?)
                \s*,\s*
                (?P<cidade>.+?)
                \s*,\s*
                (?P<estado>[A-Za-z]{2})
                \s*,\s*
                (?P<cep>\d{5}-?\d{3})
                \s*$
                """,
                re.VERBOSE
            )
        ]

        for pattern in patterns:

            match = pattern.match(
                endereco
            )

            if match:

                values = match.groupdict()

                return AddressComponents(
                    logradouro=values.get(
                        "logradouro",
                        ""
                    ).strip(),
                    numero=values.get(
                        "numero",
                        ""
                    ).strip(),
                    bairro=values.get(
                        "bairro",
                        ""
                    ).strip(),
                    cidade=values.get(
                        "cidade",
                        ""
                    ).strip(),
                    estado=values.get(
                        "estado",
                        ""
                    ).strip(),
                    cep=values.get(
                        "cep",
                        ""
                    ).strip(),
                    pais="Brasil"
                )

        cep_match = re.search(
            r"\b\d{5}-?\d{3}\b",
            endereco
        )

        cep = (
            cep_match.group(0)
            if cep_match
            else ""
        )

        without_postal_code = re.sub(
            r"\b\d{5}-?\d{3}\b",
            "",
            endereco
        )

        number_match = re.search(
            r"(?:,\s*|\bn[º°o.]?\s*)"
            r"(\d+[A-Za-z]?)\b",
            without_postal_code,
            flags=re.IGNORECASE
        )

        numero = (
            number_match.group(1)
            if number_match
            else ""
        )

        logradouro = without_postal_code

        if numero:
            logradouro = re.split(
                r",\s*"
                + re.escape(numero)
                + r"\b",
                without_postal_code,
                maxsplit=1,
                flags=re.IGNORECASE
            )[0]

        return AddressComponents(
            logradouro=self._clean_text(
                logradouro
            ).strip(
                " ,-"
            ),
            numero=numero,
            cep=cep,
            pais="Brasil"
        )

    def _apply_context(
        self,
        componentes: AddressComponents,
        contexto: dict
    ) -> AddressComponents:

        if not componentes.cidade:
            componentes.cidade = str(
                contexto.get(
                    "cidade",
                    ""
                )
            ).strip()

        if not componentes.estado:
            componentes.estado = str(
                contexto.get(
                    "estado",
                    ""
                )
            ).strip()

        if not componentes.pais:
            componentes.pais = str(
                contexto.get(
                    "pais",
                    "Brasil"
                )
            ).strip()

        return componentes

    def _build_free_queries(
        self,
        endereco_original: str,
        componentes: AddressComponents
    ) -> list[str]:

        queries = [
            endereco_original
        ]

        parts = [
            componentes.logradouro,
            componentes.numero,
            componentes.bairro,
            componentes.cidade,
            componentes.estado,
            componentes.cep,
            "Brasil"
        ]

        complete_query = ", ".join(
            part
            for part in parts
            if part
        )

        if complete_query:
            queries.append(
                complete_query
            )

        if (
            componentes.logradouro
            and componentes.numero
        ):

            queries.append(
                ", ".join(
                    part
                    for part in [
                        f"{componentes.numero} "
                        f"{componentes.logradouro}",
                        componentes.bairro,
                        componentes.cidade,
                        componentes.estado,
                        componentes.cep,
                        "Brasil"
                    ]
                    if part
                )
            )

        unique_queries = []

        for query in queries:

            query = self._clean_text(
                query
            )

            if (
                query
                and query not in unique_queries
            ):
                unique_queries.append(
                    query
                )

        return unique_queries

    @staticmethod
    def _remove_duplicates(
        features: list[dict]
    ) -> list[dict]:

        result = []
        seen = set()

        for feature in features:

            coordinates = feature.get(
                "geometry",
                {}
            ).get(
                "coordinates",
                []
            )

            properties = feature.get(
                "properties",
                {}
            )

            key = (
                tuple(
                    coordinates[:2]
                ),
                properties.get(
                    "label",
                    ""
                )
            )

            if key in seen:
                continue

            seen.add(
                key
            )

            result.append(
                feature
            )

        return result

    @staticmethod
    def _clean_text(
        text: Any
    ) -> str:

        value = str(
            text or ""
        ).strip()

        value = re.sub(
            r"\s+",
            " ",
            value
        )

        value = re.sub(
            r"\s*,\s*",
            ", ",
            value
        )

        return value.strip()

    @staticmethod
    def _normalize(
        text: Any
    ) -> str:

        value = str(
            text or ""
        ).lower()

        value = unicodedata.normalize(
            "NFKD",
            value
        )

        value = "".join(
            character
            for character in value
            if not unicodedata.combining(
                character
            )
        )

        value = re.sub(
            r"[^a-z0-9]+",
            " ",
            value
        )

        return " ".join(
            value.split()
        )

    def _normalize_street(
        self,
        text: Any
    ) -> str:

        value = self._normalize(
            text
        )

        replacements = {
            "avenida": "",
            "av": "",
            "rua": "",
            "r": "",
            "rodovia": "",
            "rod": "",
            "travessa": "",
            "tv": "",
            "estrada": "",
            "est": ""
        }

        words = [
            replacements.get(
                word,
                word
            )
            for word in value.split()
        ]

        return " ".join(
            word
            for word in words
            if word
        )

    def _normalize_state(
        self,
        state: Any
    ) -> str:

        value = self._normalize(
            state
        )

        states = {
            "acre": "ac",
            "alagoas": "al",
            "amapa": "ap",
            "amazonas": "am",
            "bahia": "ba",
            "ceara": "ce",
            "distrito federal": "df",
            "espirito santo": "es",
            "goias": "go",
            "maranhao": "ma",
            "mato grosso": "mt",
            "mato grosso do sul": "ms",
            "minas gerais": "mg",
            "para": "pa",
            "paraiba": "pb",
            "parana": "pr",
            "pernambuco": "pe",
            "piaui": "pi",
            "rio de janeiro": "rj",
            "rio grande do norte": "rn",
            "rio grande do sul": "rs",
            "rondonia": "ro",
            "roraima": "rr",
            "santa catarina": "sc",
            "sao paulo": "sp",
            "sergipe": "se",
            "tocantins": "to"
        }

        return states.get(
            value,
            value
        )

    @staticmethod
    def _normalize_number(
        number: Any
    ) -> str:

        return re.sub(
            r"[^0-9a-z]",
            "",
            str(
                number or ""
            ).lower()
        )

    @staticmethod
    def _normalize_postal_code(
        postal_code: Any
    ) -> str:

        return re.sub(
            r"\D",
            "",
            str(
                postal_code or ""
            )
        )

    @staticmethod
    def _number_in_text(
        number: str,
        text: str
    ) -> bool:

        return bool(
            re.search(
                r"\b"
                + re.escape(number)
                + r"\b",
                text
            )
        )

    @staticmethod
    def _same_or_contains(
        first: str,
        second: str
    ) -> bool:

        if not first or not second:
            return False

        return (
            first == second
            or first in second
            or second in first
        )

    @staticmethod
    def _token_similarity(
        first: str,
        second: str
    ) -> float:

        first_tokens = set(
            first.split()
        )

        second_tokens = set(
            second.split()
        )

        if (
            not first_tokens
            or not second_tokens
        ):
            return 0.0

        intersection = first_tokens.intersection(
            second_tokens
        )

        union = first_tokens.union(
            second_tokens
        )

        return (
            len(intersection)
            / len(union)
        )