import sys
from enum import Enum


class PointType(str, Enum):
    """The role a zone plays on the map."""

    START = "start_hub"
    HUB = "hub"
    END = "end_hub"


class Zone(str, Enum):
    """The kind of a zone, which drives how drones may enter it."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

    @property
    def turns(self) -> int:
        """Return how many turns entering a zone of this kind costs."""
        return 2 if self is Zone.RESTRICTED else 1

    @property
    def is_passable(self) -> bool:
        """Return True when a drone is allowed to enter the zone."""
        return self is not Zone.BLOCKED


class Color(str, Enum):
    """A terminal color a zone can be displayed with."""

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
        """Return the escape sequence painting text in this color."""
        color: str = "\033[38;2;"
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
        """Return the text wrapped in this color, unchanged if unknown."""
        if self is Color.RAINBOW:
            return self.colorize_rainbow(text)
        if self.ansi == "":
            return text
        return self.ansi + text + "\033[0m"

    @staticmethod
    def colorize_rainbow(text: str) -> str:
        """Return the text with one color of the rainbow per character."""
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
    """A drone, its position on the map and the route it follows.

    A drone is either inside a zone (get_point) or flying on the
    connection toward a restricted zone (is_in_transit), never both:
    leaving a zone frees its capacity at once.
    """

    def __init__(self, drone_id: int) -> None:
        self.__id = drone_id
        self.__point: "Point | None" = None
        self.__path: list["Point"] = []
        self.__step: int = 0
        self.__transit_from: "Point | None" = None
        self.__transit_to: "Point | None" = None
        self.__transit_turns: int = 0

    def get_name(self) -> str:
        """Return the identifier used by the output format ('D1')."""
        return "D" + str(self.__id)

    def get_point(self) -> "Point | None":
        return self.__point

    def set_point(self, new_point: "Point | None") -> None:
        self.__point = new_point

    def set_path(self, path: list["Point"]) -> None:
        """Assign the route to follow, starting from the current zone."""
        self.__path = list(path)
        self.__step = 0

    def get_step(self) -> int:
        return self.__step

    def next_point(self) -> "Point | None":
        """Return the next zone of the route, None once it is over."""
        if self.__step + 1 >= len(self.__path):
            return None
        return self.__path[self.__step + 1]

    def advance(self) -> None:
        """Record that the drone reached the next zone of its route."""
        if self.__step + 1 < len(self.__path):
            self.__step += 1

    def is_delivered(self) -> bool:
        """Return True once the drone sits in the end hub."""
        if self.__point is None:
            return False
        return self.__point.get_type() is PointType.END

    def start_transit(self, origin: "Point", destination: "Point",
                      turns: int) -> None:
        """Send the drone on the connection joining two zones.

        The remaining turns are spent on the connection, where the
        subject forbids the drone to wait for a free slot.
        """
        self.__transit_from = origin
        self.__transit_to = destination
        self.__transit_turns = turns

    def is_in_transit(self) -> bool:
        return self.__transit_to is not None

    def get_transit_from(self) -> "Point | None":
        return self.__transit_from

    def get_transit_to(self) -> "Point | None":
        return self.__transit_to

    def transit_tick(self) -> bool:
        """Spend one turn flying; True when the destination is reached."""
        if self.__transit_turns > 0:
            self.__transit_turns -= 1
        return self.__transit_turns <= 0

    def end_transit(self) -> None:
        """Forget the connection, once the drone landed in a zone."""
        self.__transit_from = None
        self.__transit_to = None
        self.__transit_turns = 0

    def is_on_link(self, point_a: "Point", point_b: "Point") -> bool:
        """Return True when the drone flies on that connection.

        Connections are bidirectional, so the two zones are compared
        without taking the direction of the flight into account.
        """
        if self.__transit_from is None or self.__transit_to is None:
            return False
        if self.__transit_from is point_a and self.__transit_to is point_b:
            return True
        return self.__transit_from is point_b and self.__transit_to is point_a


class Point:
    """A zone of the map: its metadata, its neighbours and its drones."""

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
        self.__drones: list[Drone] = []
        self.__connections: list["Point"] = []
        self.__max_link: dict["Point", int] = {}
        self.__incoming: int = 0

    def get_name(self) -> str:
        return self.__name

    def get_type(self) -> PointType:
        return self.__type

    def get_x(self) -> int:
        return self.__x

    def get_y(self) -> int:
        return self.__y

    def get_drones(self) -> list[Drone]:
        return list(self.__drones)

    def get_zone(self) -> Zone:
        return self.__zone

    def display_name(self) -> str:
        return self.__color.colorize(self.__name)

    def get_max_drones(self) -> int:
        return self.__max_drones

    def get_connections(self) -> list["Point"]:
        return list(self.__connections)

    def entry_cost(self) -> int:
        """Return how many turns a drone needs to enter this zone."""
        return self.__zone.turns

    def free_slots(self) -> int:
        """Return how many more drones this zone can take right now.

        The start and end hubs have no limit. The slots already booked
        for the current turn by reserve are deducted.
        """
        if self.__type is not PointType.HUB:
            return sys.maxsize
        return self.__max_drones - len(self.__drones) - self.__incoming

    def reserve(self) -> bool:
        """Book a slot for a drone entering during this turn.

        Booking every arrival before moving anybody is what lets several
        drones leave and enter the same zone on the same turn without
        ever exceeding its capacity. False when the zone is full.
        """
        if self.free_slots() <= 0:
            return False
        self.__incoming += 1
        return True

    def clear_reservations(self) -> None:
        """Drop the bookings left behind by an abandoned turn."""
        self.__incoming = 0

    def add_drone(self, drone: Drone) -> None:
        """Put a drone in this zone, taking it out of its previous one."""
        previous = drone.get_point()
        if previous is not None and previous is not self:
            previous.remove_drone(drone)
        if drone not in self.__drones:
            self.__drones.append(drone)
        # The drone is now part of the occupancy count, so its booking
        # must not be deducted a second time.
        if self.__incoming > 0:
            self.__incoming -= 1
        drone.set_point(self)

    def add_drones(self, drones: list[Drone]) -> None:
        for drone in drones:
            self.add_drone(drone)

    def remove_drone(self, drone: Drone) -> None:
        """Take a drone out of this zone, ignoring an absent one."""
        if drone not in self.__drones:
            return
        self.__drones.remove(drone)
        drone.set_point(None)

    def add_connection(self, point: "Point",
                       max_link_capacity: int = 1) -> None:
        self.__connections.append(point)
        self.__max_link[point] = max_link_capacity

    def has_connection(self, point: "Point") -> bool:
        return point in self.__connections

    def get_link_capacity(self, point: "Point") -> int:
        """Return max_link_capacity toward a zone, 0 when not linked."""
        return self.__max_link.get(point, 0)
