from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Stop:
    stop_code: int
    stop_descr: str
    stop_lat: float
    stop_lng: float
    stop_senu: int
    
@dataclass(frozen=True)
class Route:
    code: int
    descr: str
    stops: List[Stop]
