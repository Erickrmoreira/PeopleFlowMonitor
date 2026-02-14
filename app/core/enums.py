from enum import Enum

class Direction(str, Enum):
    IN = "IN"
    OUT = "OUT"


class Position(str, Enum):
    TOP = "top"
    MIDDLE = "middle"
    BOTTOM = "bottom"
