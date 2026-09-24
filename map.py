from models import Drone, Point, PointType


class MapException(Exception):

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class Map:

    def __init__(self) -> None:
        self.__drones: list[Drone] = []
        self.__points: list[Point] = []
        self.__drone_count: int = 0
        self.__round = 0

    def get_round(self) -> int:
        return self.__round

    def add_round(self, add_round: int = 1) -> None:
        """Move the simulation clock forward."""
        self.__round += add_round

    def validate(self) -> None:
        """Check the rules that only make sense on the whole map.

        Called once the file is fully parsed: none of these errors can
        be attached to a particular line.
        """
        if self.get_drone_count() <= 0:
            raise MapException("nb_drones must be a positive integer")
        if self.count_type(PointType.START) != 1:
            raise MapException("the map must have exactly one start_hub")
        if self.count_type(PointType.END) != 1:
            raise MapException("the map must have exactly one end_hub")
        if not self.is_end_reachable():
            raise MapException("the end hub cannot be reached "
                               "from the start hub")

    def is_end_reachable(self) -> bool:
        """Return True when a path of passable zones joins start to end."""
        start = self.get_point_from_type(PointType.START)
        end = self.get_point_from_type(PointType.END)
        if start is None or end is None:
            return False

        seen = {start}
        queue = [start]
        while queue:
            point = queue.pop()
            if point is end:
                return True
            for neighbor in point.get_connections():
                if neighbor in seen:
                    continue
                if not neighbor.get_zone().is_passable:
                    continue
                seen.add(neighbor)
                queue.append(neighbor)
        return False

    def start(self) -> None:
        """Create the fleet and gather it in the start hub."""
        start_point = self.get_point_from_type(PointType.START)
        if start_point is None:
            raise MapException("Could not find the start point")

        for drone_name in range(1, self.__drone_count + 1):
            self.add_drone(Drone(drone_name))

        start_point.add_drones(self.__drones)

    def link_usage(self, point_a: Point, point_b: Point) -> int:
        """Count the drones currently flying on a connection.

        Connections are stored on both of their zones, so the drones
        themselves are the single source of truth for the occupancy
        checked against max_link_capacity.
        """
        usage = 0
        for drone in self.get_drones():
            if drone.is_on_link(point_a, point_b):
                usage += 1
        return usage

    def find_paths(self, point: Point, end: Point,
                   path: list[Point]) -> list[list[Point]]:
        if point is end:
            return [path]

        paths: list[list[Point]] = []
        for neighbor in point.get_connections():
            if neighbor in path:
                continue
            if not neighbor.get_zone().is_passable:
                continue
            found_paths = self.find_paths(neighbor, end,
                                          path + [neighbor])
            for found_path in found_paths:
                paths.append(found_path)
        return paths

    @staticmethod
    def path_cost(path: list[Point]) -> int:
        cost = 0
        for point in path[1:]:
            cost += point.get_zone().turns
        return cost

    def solve(self) -> list[list[Point]]:
        start = self.get_point_from_type(PointType.START)
        end = self.get_point_from_type(PointType.END)
        if start is None or end is None:
            raise MapException("Could not find the start or the end point")

        return sorted(self.find_paths(start, end, [start]), key=self.path_cost)

    def get_drones(self) -> list[Drone]:
        return self.__drones

    def get_points(self) -> list[Point]:
        return self.__points

    def set_drone_count(self, drone_count: int) -> None:
        self.__drone_count = drone_count

    def get_drone_count(self) -> int:
        return self.__drone_count

    def add_drone(self, drone: Drone) -> None:
        self.__drones.append(drone)

    def add_point(self, point: Point) -> None:
        self.__points.append(point)

    def get_point_from_name(self, name: str) -> Point | None:
        for point in self.get_points():
            if name == point.get_name():
                return point
        return None

    def get_point_from_type(self, point_type: PointType) -> Point | None:
        for point in self.get_points():
            if point_type == point.get_type():
                return point
        return None

    def count_type(self, point_type: PointType) -> int:
        count: int = 0
        for point in self.get_points():
            if point_type == point.get_type():
                count += 1
        return count
