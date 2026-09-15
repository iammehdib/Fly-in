"""Core domain objects of the Fly-in simulation.

This module contains the zone type enumeration and the entities
manipulated by the whole program: ``Point`` (a zone of the network),
``Connection`` (a bidirectional link between two zones), ``Transit``
(a drone flying on a connection toward a restricted zone) and
``Drone``.
"""

from __future__ import annotations

from enum import Enum
from typing import Union


class PointType(str, Enum):
    """Kind of a zone as declared in the map file."""

    START = "start_hub"
    HUB = "hub"
    END = "end_hub"


class Zone(str, Enum):
    """Zone type, which defines the movement cost and accessibility."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

    @property
    def turns(self) -> int:
        """Return the number of turns needed to enter this zone."""
        return 2 if self is Zone.RESTRICTED else 1

    @property
    def is_passable(self) -> bool:
        """Return ``True`` when a drone is allowed to enter the zone."""
        return self is not Zone.BLOCKED

    @property
    def symbol(self) -> str:
        """Return the one-character marker used by the visual output."""
        return {Zone.RESTRICTED: "!", Zone.PRIORITY: "*",
                Zone.BLOCKED: "X"}.get(self, "")


class Point:
    """A zone of the network (start hub, regular hub or end hub)."""

    def __init__(self, name: str, point_type: PointType,
                 x: int, y: int, zone: Zone = Zone.NORMAL,
                 color: str = "none", max_drones: int = 1) -> None:
        """Create a zone.

        Args:
            name: Unique name of the zone.
            point_type: Start, regular hub or end.
            x: Horizontal coordinate.
            y: Vertical coordinate.
            zone: Zone type (normal, blocked, restricted, priority).
            color: Color name used by the visual representation.
            max_drones: Capacity of the zone (ignored for start/end).
        """
        self.__name = name
        self.__type = point_type
        self.__x = x
        self.__y = y
        self.__zone = zone
        self.__color = color
        self.__max_drones = max_drones
        self.__connections: dict[str, Connection] = {}

    def __repr__(self) -> str:
        return f"Point({self.__name!r})"

    def get_name(self) -> str:
        """Return the unique name of the zone."""
        return self.__name

    def get_type(self) -> PointType:
        """Return the kind of the zone."""
        return self.__type

    def get_x(self) -> int:
        """Return the horizontal coordinate."""
        return self.__x

    def get_y(self) -> int:
        """Return the vertical coordinate."""
        return self.__y

    def get_zone(self) -> Zone:
        """Return the zone type."""
        return self.__zone

    def get_color(self) -> str:
        """Return the color name of the zone (``"none"`` by default)."""
        return self.__color

    def get_max_drones(self) -> int:
        """Return the declared capacity of the zone."""
        return self.__max_drones

    def is_hub(self) -> bool:
        """Return ``True`` for regular hubs (capacity applies)."""
        return self.__type is PointType.HUB

    def is_end(self) -> bool:
        """Return ``True`` for the end hub."""
        return self.__type is PointType.END

    def is_start(self) -> bool:
        """Return ``True`` for the start hub."""
        return self.__type is PointType.START

    def has_unlimited_capacity(self) -> bool:
        """Return ``True`` when the zone is the start or the end hub."""
        return not self.is_hub()

    def get_connections(self) -> list[Connection]:
        """Return every connection attached to the zone."""
        return list(self.__connections.values())

    def get_neighbors(self) -> list[Point]:
        """Return the zones directly linked to this one."""
        return [link.other(self) for link in self.__connections.values()]

    def get_connection_to(self, point: Point) -> Connection | None:
        """Return the connection leading to ``point``, if any."""
        return self.__connections.get(point.get_name())

    def has_connection(self, point: Point) -> bool:
        """Return ``True`` when ``point`` is a direct neighbor."""
        return point.get_name() in self.__connections

    def attach(self, connection: Connection) -> None:
        """Register ``connection`` (which must involve this zone)."""
        self.__connections[connection.other(self).get_name()] = connection


class Connection:
    """A bidirectional link between two zones with a capacity."""

    def __init__(self, a: Point, b: Point,
                 max_link_capacity: int = 1) -> None:
        """Create the link and attach it to both endpoints.

        Args:
            a: First endpoint.
            b: Second endpoint.
            max_link_capacity: Maximum number of drones flying on the
                connection during the same turn.
        """
        self.__a = a
        self.__b = b
        self.__max_link_capacity = max_link_capacity
        # Same key whatever the direction: "a-b" and "b-a" are one link.
        names = sorted((a.get_name(), b.get_name()))
        self.__key = f"{names[0]}-{names[1]}"
        a.attach(self)
        b.attach(self)

    def __repr__(self) -> str:
        return f"Connection({self.key()!r})"

    def get_max_link_capacity(self) -> int:
        """Return the number of drones allowed on the link per turn."""
        return self.__max_link_capacity

    def key(self) -> str:
        """Return a direction-independent identifier of the link."""
        return self.__key

    def other(self, point: Point) -> Point:
        """Return the endpoint that is not ``point``."""
        return self.__b if point is self.__a else self.__a

    def name_from(self, origin: Point) -> str:
        """Return the link name as seen from ``origin`` (``from-to``)."""
        return f"{origin.get_name()}-{self.other(origin).get_name()}"


class Transit:
    """A drone flying on a connection toward a restricted zone."""

    def __init__(self, connection: Connection, origin: Point) -> None:
        """Create a transit state.

        Args:
            connection: The link currently occupied by the drone.
            origin: The zone the drone just left.
        """
        self.__connection = connection
        self.__origin = origin

    def __repr__(self) -> str:
        return f"Transit({self.name()!r})"

    def get_connection(self) -> Connection:
        """Return the link occupied by the drone."""
        return self.__connection

    def get_origin(self) -> Point:
        """Return the zone the drone comes from."""
        return self.__origin

    def get_target(self) -> Point:
        """Return the zone the drone will reach next turn."""
        return self.__connection.other(self.__origin)

    def name(self) -> str:
        """Return the connection name used by the output format."""
        return self.__connection.name_from(self.__origin)


Position = Union[Point, Transit]
"""Where a drone can be at the end of a turn."""


def link_used(previous: Position, current: Position) -> Connection | None:
    """Return the connection a drone flies on between two positions.

    Going from ``previous`` (end of turn t-1) to ``current`` (end of
    turn t), the drone uses a connection when it:

    * is in transit toward a restricted zone (``current`` is a Transit),
    * lands at the end of a transit (``previous`` is a Transit),
    * moves in one turn between two adjacent zones.

    ``None`` means the drone stayed in place (or jumped between two
    zones that are not connected, which the engine reports as an error).
    """
    if isinstance(current, Transit):
        return current.get_connection()
    if isinstance(previous, Transit):
        return previous.get_connection()
    if previous is current:
        return None
    return previous.get_connection_to(current)


class Drone:
    """A drone of the fleet, identified by a positive integer."""

    def __init__(self, drone_id: int) -> None:
        """Create the drone ``D<drone_id>``."""
        self.__id = drone_id
        self.__plan: list[Position] = []

    def __repr__(self) -> str:
        return f"Drone({self.__id})"

    def get_id(self) -> int:
        """Return the numeric identifier."""
        return self.__id

    def get_name(self) -> str:
        """Return the identifier used by the output format (``D1``)."""
        return f"D{self.__id}"

    def get_plan(self) -> list[Position]:
        """Return the scheduled positions, indexed by turn."""
        return self.__plan

    def set_plan(self, plan: list[Position]) -> None:
        """Store the schedule computed by the solver."""
        self.__plan = plan

    def arrival_turn(self) -> int:
        """Return the turn at which the drone reaches the end zone."""
        return len(self.__plan) - 1

    def position_at(self, turn: int) -> Position:
        """Return the position of the drone at the end of ``turn``."""
        if turn >= len(self.__plan):
            return self.__plan[-1]
        return self.__plan[turn]
