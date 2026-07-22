from dataclasses import dataclass


@dataclass
class Delivery:

    endereco: str

    latitude: float = 0.0

    longitude: float = 0.0

    bairro: str = ""

    cidade: str = ""

    estado: str = ""

    tempo_parada: int = 20