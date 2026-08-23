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

class Drone:
    name: str
    point: "Point" = None

class Point:

    def __init__(self, name: str, x: int, y: int, meta_datas: dict[str, str]):
        self.__name = name
        self.x: int = x
        self.y: int = y
        self.__meta_datas: dict[str, str] = meta_datas
        self.__drones: set[Drone] = set()
        self.connections: list["Point"] = []

    def get_name(self) -> str:
        return self.__name

    def get_drones(self) -> set[Drone]:
        return self.__drones

    def get_metadata(self, key: str) -> str | None:
        return self.__meta_datas.get(key)

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
