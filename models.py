import sys
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

    @property
    def turns(self) -> int:
        return 2 if self is Zone.RESTRICTED else 1

    @property
    def preference(self) -> float:
        return {Zone.PRIORITY: 1.0, Zone.NORMAL: 0.5}.get(self, 0.0)

    @property
    def is_passable(self) -> bool:
        return self is not Zone.BLOCKED

class Color(str, Enum):
    UNDEFINED = "none"
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

    @property
    def ansi(self) -> str:
        color: str = "[38;2;"
        if self is Color.BLACK:
            color += "0;0;0m"
        elif self is Color.GRAY:
            color += "128;128;128m"
        elif self is Color.RED:
            color += "255;0;0m"
        elif self is Color.DARK_RED:
            color += "139;0;0m"
        elif self is Color.ORANGE:
            color += "255;165;0m"
        elif self is Color.GREEN:
            color += "0;160;0m"
        elif self is Color.LIME:
            color += "50;255;50m"
        elif self is Color.BLUE:
            color += "0;80;255m"
        elif self is Color.CYAN:
            color += "0;255;255m"
        elif self is Color.PURPLE:
            color += "128;0;128m"
        elif self is Color.MAGENTA:
            color += "255;0;255m"
        elif self is Color.VIOLET:
            color += "238;130;238m"
        elif self is Color.CRIMSON:
            color += "220;20;60m"
        elif self is Color.BROWN:
            color += "165;42;42m"
        elif self is Color.MAROON:
            color += "128;0;0m"
        elif self is Color.YELLOW:
            color += "255;255;0m"
        elif self is Color.GOLD:
            color += "255;215;0m"
        elif self is Color.WHITE:
            color += "255;255;255m"
        else:
            return ""
        return color

    def colorize(self, text: str) -> str:
        if self is Color.RAINBOW:
            return self.colorize_rainbow(text)
        if self.ansi == "":
            return text
        return self.ansi + text + "[0m"

    @staticmethod
    def colorize_rainbow(text: str) -> str:
        colors = [Color.RED, Color.ORANGE, Color.YELLOW,
                  Color.LIME, Color.CYAN, Color.BLUE, Color.VIOLET]
        result = ""
        index = 0
        for char in text:
            color = colors[index % len(colors)]
            result += color.colorize(char)
            index += 1
        return result

class Drone:

    def __init__(self, name: str):
        self.__name = name
        self.__point: "Point | None" = None

    def get_name(self) -> str:
        return self.__name

    def get_point(self) -> "Point | None":
        return self.__point

    def set_point(self, new_point: "Point | None") -> None:
        self.__point = new_point

class Point:

    def __init__(self, name: str, point_type: PointType,
                 x: int, y: int, zone: Zone,
                 color: Color, max_drones: int) -> None:
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

    def display_name(self) -> str:
        return self.__color.colorize(self.__name)

    def get_max_drones(self) -> int:
        return self.__max_drones

    def get_connections(self) -> list["Point"]:
        return self.__connections

    def free_slots(self) -> int:
        if self.__type is not PointType.HUB:
            return sys.maxsize
        return self.__max_drones - len(self.__drones)

    def add_drone(self, drone: Drone) -> None:
        previous = drone.get_point()
        if previous is not None and previous is not self:
            previous.remove_drone(drone)
        self.get_drones().add(drone)
        drone.set_point(self)

    def add_drones(self, drones: list[Drone]) -> None:
        for drone in drones:
            self.add_drone(drone)

    def remove_drone(self, drone: Drone) -> None:
        self.get_drones().remove(drone)
        drone.set_point(None)

    def has_drone(self, drone: Drone) -> bool:
        return drone in self.get_drones()

    def has_drones(self) -> bool:
        return bool(self.get_drones())

    def move_drone(self, next_point: "Point") -> bool:
        if not self.has_connection(next_point):
            return False

        room = min(self.__max_link[next_point], next_point.free_slots())
        for drone in list(self.get_drones())[:max(0, room)]:
            next_point.add_drone(drone)

        return True

    def add_connection(self, point: "Point", max_link_capacity: int = 1) -> None:
        self.__connections.append(point)
        self.__max_link[point] = max_link_capacity

    def remove_connection(self, point: "Point") -> None:
        self.__connections.remove(point)
        self.__max_link.pop(point)

    def has_connection(self, point: "Point") -> bool:
        return point in self.__connections
