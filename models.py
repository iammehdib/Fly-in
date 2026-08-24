from dataclasses import dataclass
from enum import Enum

class PointType(str, Enum):
    START = "start_hub"
    HUB = "hub"
    END = "end_hub"

class Zone(str, Enum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

class Color(str, Enum):
    BLACK = "black"
    GRAY = "gray"
    RED = "red"
    DARK_RED = "darkred"
    ORANGE = "orange"
    GREEN = "green"
    LIME = "lime"
    BLUE = "blue"
    CYAN = "cyan"
    PURPLE = "purple"
    MAGENTA = "magenta"
    VIOLET = "violet"
    CRIMSON = "crimson"
    RAINBOW = "rainbow"
    BROWN = "brown"
    MAROON = "maroon"
    YELLOW = "yellow"
    GOLD = "gold"
    WHITE = "white"

@dataclass(frozen=True)
class Drone:
    name: str

class Point:

    def __init__(self, name: str, point_type: PointType, x: int, y: int, zone: Zone, color: Color, max_drones: int):
        self.__name = name
        self.__type = point_type
        self.__x: int = x
        self.__y: int = y
        self.__zone = zone
        self.__color = color
        self.__max_drones = max_drones
        self.__drones: set[Drone] = set()
        self.__connections: list["Point"] = []
        self.__max_link: dict["Point", int] = {}

    def get_name(self) -> str:
        return self.__name

    def get_type(self) -> PointType:
        return self.__type

    def get_x(self) -> int:
        return self.__x

    def get_y(self) -> int:
        return self.__y

    def get_drones(self) -> set[Drone]:
        return self.__drones

    def get_zone(self) -> Zone:
        return self.__zone

    def get_color(self) -> Color:
        return self.__color

    def get_max_drones(self) -> int:
        return self.__max_drones

    def add_drone(self, drone: Drone) -> None:
        self.__drones.add(drone)

    def remove_drone(self, drone: Drone) -> None:
        self.__drones.remove(drone)

    def contain_drone(self, drone: Drone) -> bool:
        return drone in self.__drones

    def is_contain_a_drones(self) -> bool:
        return len(self.__drones) != 0

    def move_drone(self, next_point: "Point") -> bool:
        if not self.contain_connection(next_point):
            return False

        max_count: int = next_point.__max_link[next_point]
        count: int = 0
        for drone in list(self.get_drones()):
            if max_count == count:
                break
            self.remove_drone(drone)
            next_point.add_drone(drone)
            count += 1

        return True

    def add_connection(self, point: "Point", max_link_capacity: int = 1) -> None:
        self.__connections.append(point)
        self.__max_link[point] = max_link_capacity

    def remove_connection(self, point: "Point") -> None:
        self.__connections.remove(point)
        self.__max_link.pop(point)

    def contain_connection(self, point: "Point") -> bool:
        return point in self.__connections
