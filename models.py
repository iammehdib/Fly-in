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
        self.__x: int = x
        self.__y: int = y
        self.__meta_datas: dict[str, str] = meta_datas
        self.__drones: set[Drone] = set()
        self.__connections: list["Point"] = []
        self.__max_link: dict["Point", int] = {}

    def get_name(self) -> str:
        return self.__name

    def get_x(self) -> int:
        return self.__x

    def get_y(self) -> int:
        return self.__y

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
