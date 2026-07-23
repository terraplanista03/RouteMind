from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from typing import Any


@dataclass
class RouteStop:

    indice: int
    tipo: str
    endereco: str
    latitude: float
    longitude: float
    bairro: str = ""
    cidade: str = ""
    estado: str = ""
    cep: str = ""

    def to_dict(self) -> dict[str, Any]:

        return asdict(
            self
        )


@dataclass
class Route:

    motorista: int
    pontos: list[RouteStop] = field(
        default_factory=list
    )

    distancia_km: float = 0.0
    tempo_deslocamento_minutos: float = 0.0
    tempo_paradas_minutos: float = 0.0
    tempo_total_minutos: float = 0.0

    @property
    def quantidade_entregas(self) -> int:

        return sum(
            1
            for ponto in self.pontos
            if ponto.tipo.lower() == "entrega"
        )

    def add_stop(
        self,
        stop: RouteStop
    ) -> None:

        self.pontos.append(
            stop
        )

    def to_dict(self) -> dict[str, Any]:

        return {
            "motorista": self.motorista,
            "quantidade_entregas": (
                self.quantidade_entregas
            ),
            "distancia_km": round(
                self.distancia_km,
                2
            ),
            "tempo_deslocamento": round(
                self.tempo_deslocamento_minutos,
                1
            ),
            "tempo_paradas": round(
                self.tempo_paradas_minutos,
                1
            ),
            "tempo_total": round(
                self.tempo_total_minutos,
                1
            ),
            "roteiro": [
                ponto.to_dict()
                for ponto in self.pontos
            ]
        }