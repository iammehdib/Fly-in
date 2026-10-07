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

    rgb: str

    UNDEFINED = ("none", "")
    BLACK = ("black", "0;0;0")
    GRAY = ("gray", "128;128;128")
    RED = ("red", "255;0;0")
    DARK_RED = ("darkred", "139;0;0")
    ORANGE = ("orange", "255;165;0")
    GREEN = ("green", "0;160;0")
    LIME = ("lime", "50;255;50")
    BLUE = ("blue", "0;80;255")
    CYAN = ("cyan", "0;255;255")
    PURPLE = ("purple", "128;0;128")
    MAGENTA = ("magenta", "255;0;255")
    VIOLET = ("violet", "238;130;238")
    CRIMSON = ("crimson", "220;20;60")
    RAINBOW = ("rainbow", "")
    BROWN = ("brown", "165;42;42")
    MAROON = ("maroon", "128;0;0")
    YELLOW = ("yellow", "255;255;0")
    GOLD = ("gold", "255;215;0")
    WHITE = ("white", "255;255;255")

    def __new__(cls, name: str, rgb: str = "") -> "Color":
        """Build a member whose value is its name, carrying its rgb."""
        member = str.__new__(cls, name)
        member._value_ = name
        member.rgb = rgb
        return member

    @property
    def ansi(self) -> str:
        """Return the escape sequence painting text in this color."""
        if self.rgb == "":
            return ""
        return "[38;2;" + self.rgb + "m"

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
    """A drone, its position on the map and the route it follows."""

    def __init__(self, drone_id: int) -> None:
        """Create a drone, outside of any zone and with no route yet."""
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
        """Return the zone holding the drone, None while it flies."""
        return self.__point

    def set_point(self, new_point: "Point | None") -> None:
        """Record the zone holding the drone, None while it flies."""
        self.__point = new_point

    def set_path(self, path: list["Point"]) -> None:
        """Assign the route to follow, starting from the current zone."""
        self.__path = list(path)
        self.__step = 0

    def get_step(self) -> int:
        """Return how far along its route the drone has come."""
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
        """Send the drone on the connection joining two zones."""
        self.__transit_from = origin
        self.__transit_to = destination
        self.__transit_turns = turns

    def is_in_transit(self) -> bool:
        """Return True while the drone flies on a connection."""
        return self.__transit_to is not None

    def get_transit_from(self) -> "Point | None":
        """Return the zone the drone took off from, if it is flying."""
        return self.__transit_from

    def get_transit_to(self) -> "Point | None":
        """Return the zone the drone is flying to, if it is flying."""
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
        """Return True when the drone flies on that connection."""
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
        """Create an empty zone from what its map line declares."""
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
        """Return the name the map file gives to the zone."""
        return self.__name

    def get_type(self) -> PointType:
        """Return whether the zone is the start, the end or a hub."""
        return self.__type

    def get_x(self) -> int:
        """Return the horizontal coordinate of the zone."""
        return self.__x

    def get_y(self) -> int:
        """Return the vertical coordinate of the zone."""
        return self.__y

    def get_drones(self) -> list[Drone]:
        """Return the drones standing in the zone."""
        return list(self.__drones)

    def get_zone(self) -> Zone:
        """Return the kind of the zone, which drives its cost."""
        return self.__zone

    def display_name(self) -> str:
        """Return the name of the zone, painted in its own color."""
        return self.__color.colorize(self.__name)

    def get_max_drones(self) -> int:
        """Return how many drones the zone can hold at once."""
        return self.__max_drones

    def get_connections(self) -> list["Point"]:
        """Return the zones this one is linked to."""
        return list(self.__connections)

    def entry_cost(self) -> int:
        """Return how many turns a drone needs to enter this zone."""
        return self.__zone.turns

    def free_slots(self) -> int:
        """Return how many more drones this zone can take right now."""
        if self.__type is not PointType.HUB:
            return sys.maxsize
        return self.__max_drones - len(self.__drones) - self.__incoming

    def reserve(self) -> bool:
        """Book a slot for a drone entering during this turn."""
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
        """Put a whole group of drones in this zone."""
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
        """Link this zone to another one, one way."""
        self.__connections.append(point)
        self.__max_link[point] = max_link_capacity

    def has_connection(self, point: "Point") -> bool:
        """Return True when a connection joins this zone to another."""
        return point in self.__connections

    def get_link_capacity(self, point: "Point") -> int:
        """Return max_link_capacity toward a zone, 0 when not linked."""
        return self.__max_link.get(point, 0)
