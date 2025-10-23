from dataclasses import dataclass


@dataclass(frozen=True)
class Line:
    id: int
    code: str
    descr: str