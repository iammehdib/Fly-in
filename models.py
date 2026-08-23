from dataclasses import dataclass
from enum import Enum


class Zone(str, Enum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

class Color(str, Enum):
    UNDEFINED = "wood"
    RED = "red"
    GREEN = "green"
    YELLOW = "yellow"

@dataclass
class Metadatas:
    raw: str
    zone: Zone = Zone.NORMAL
    color: Color = Color.UNDEFINED
    max_drones: int = 99999999999

class Drone:
    name: str
    point: "Point" = None

class Point:

    def __init__(self, name: str, x: int, y: int, meta_datas: Metadatas):
        self.__name = name
        self.x = x
        self.y = y
        self.meta_datas = meta_datas
        self.__drones: set[Drone] = set()
        self.connections: list["Point"] = []

    def get_name(self) -> str:
        return self.__name

    def get_drones(self) -> set[Drone]:
        return self.__drones

    def add_drone(self, drone: Drone) -> None:
        self.__drones.add(drone)

    def remove_drone(self, drone: Drone) -> None:
        self.__drones.remove(drone)

    def contain_drone(self, drone: Drone) -> bool:
        return drone in self.__drones

    def is_contain_a_drones(self) -> bool:
        return len(self.__drones) != 0

    def add_connection(self, point: "Point") -> None:
        self.connections.append(point)

    def remove_connection(self, point: "Point") -> None:
        self.connections.remove(point)
