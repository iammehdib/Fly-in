"""Graph container of the network of zones."""

from __future__ import annotations

from models import Connection, Drone, Point, PointType


class MapException(Exception):
    """Raised when the map is structurally invalid or unusable."""

    def __init__(self, reason: str) -> None:
        """Create the error with a human readable ``reason``."""
        self.reason = reason
        super().__init__(f"Error in Map: {reason}")


class Map:
    """The network of zones, its connections and the fleet of drones."""

    def __init__(self) -> None:
        """Create an empty map."""
        self.__points: dict[str, Point] = {}
        self.__connections: list[Connection] = []
        self.__drones: list[Drone] = []
        self.__drone_count: int = 0

    def set_drone_count(self, drone_count: int) -> None:
        """Set the size of the fleet and (re)create the drones."""
        self.__drone_count = drone_count
        self.__drones = [Drone(index + 1) for index in range(drone_count)]

    def get_drone_count(self) -> int:
        """Return the size of the fleet."""
        return self.__drone_count

    def get_drones(self) -> list[Drone]:
        """Return the drones, ordered by identifier."""
        return self.__drones

    def add_point(self, point: Point) -> None:
        """Register a zone; its name must be unique."""
        if point.get_name() in self.__points:
            raise MapException(f"duplicate zone '{point.get_name()}'")
        self.__points[point.get_name()] = point

    def get_points(self) -> list[Point]:
        """Return every zone in declaration order."""
        return list(self.__points.values())

    def get_point_from_name(self, name: str) -> Point | None:
        """Return the zone called ``name`` or ``None``."""
        return self.__points.get(name)

    def get_point_from_type(self, point_type: PointType) -> Point | None:
        """Return the first zone of the given type or ``None``."""
        for point in self.__points.values():
            if point.get_type() is point_type:
                return point
        return None

    def count_type(self, point_type: PointType) -> int:
        """Return how many zones have the given type."""
        return sum(1 for point in self.__points.values()
                   if point.get_type() is point_type)

    def add_connection(self, a: Point, b: Point,
                       max_link_capacity: int = 1) -> Connection:
        """Create and register a bidirectional link between two zones."""
        if a is b:
            raise MapException(f"zone '{a.get_name()}' linked to itself")
        if a.has_connection(b):
            raise MapException(f"duplicate connection "
                               f"'{a.get_name()}-{b.get_name()}'")
        connection = Connection(a, b, max_link_capacity)
        self.__connections.append(connection)
        return connection

    def get_connections(self) -> list[Connection]:
        """Return every connection in declaration order."""
        return self.__connections

    def get_start(self) -> Point:
        """Return the start hub (raise if missing)."""
        start = self.get_point_from_type(PointType.START)
        if start is None:
            raise MapException("missing start_hub")
        return start

    def get_end(self) -> Point:
        """Return the end hub (raise if missing)."""
        end = self.get_point_from_type(PointType.END)
        if end is None:
            raise MapException("missing end_hub")
        return end

    def validate(self) -> None:
        """Check the structural constraints of the subject.

        Raises:
            MapException: when the fleet is empty, when the start or end
                hub is missing/duplicated, or when the end hub is not
                reachable from the start hub.
        """
        if self.__drone_count <= 0:
            raise MapException("nb_drones must be a positive integer")
        for point_type in (PointType.START, PointType.END):
            count = self.count_type(point_type)
            if count != 1:
                raise MapException(f"expected exactly one {point_type.value}"
                                   f", found {count}")
        if not self.is_reachable(self.get_start(), self.get_end()):
            raise MapException("the end_hub cannot be reached from the "
                               "start_hub (blocked zones or missing "
                               "connections)")

    @staticmethod
    def is_reachable(origin: Point, target: Point) -> bool:
        """Return ``True`` when ``target`` is reachable from ``origin``.

        Blocked zones are never traversed. A simple depth-first search
        is enough because the graph is small and undirected.
        """
        seen = {origin.get_name()}
        stack = [origin]
        while stack:
            point = stack.pop()
            if point is target:
                return True
            for neighbor in point.get_neighbors():
                name = neighbor.get_name()
                if name in seen or not neighbor.get_zone().is_passable:
                    continue
                seen.add(name)
                stack.append(neighbor)
        return False
