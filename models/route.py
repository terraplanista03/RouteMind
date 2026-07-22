from dataclasses import dataclass, field

from .delivery import Delivery


@dataclass
class Route:

    motorista: int

    entregas: list[Delivery] = field(default_factory=list)

    distancia: float = 0

    tempo: int = 0
    