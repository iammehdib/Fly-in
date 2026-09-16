from models import Drone, Point, PointType


class MapException(Exception):

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Error in Map: {reason}")


class Map:

    def __init__(self) -> None:
        self.__drones: list[Drone] = []
        self.__points: list[Point] = []
        self.__drone_count: int = 0
        self.__round = 0

    def get_round(self) -> int:
        return self.__round

    def add_round(self, add_round: int = 0) -> None:
        self.__round += add_round

    def start(self) -> None:
        if self.__drone_count == 0:
            raise MapException("Can't start the map with 0 drone")

        start_point = self.get_point_from_type(PointType.START)
        if start_point is None:
            raise MapException("Could not find the start point")

        for drone_suffix in range(self.__drone_count):
            drone_name = "drone" + str(drone_suffix)
            self.add_drone(Drone(drone_name))

        end_point = self.get_point_from_type(PointType.END)
        if end_point is None:
            raise MapException("Could not find the start point")

        start_point.add_drones(self.__drones)

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

    def set_drone_count(self, drone_count: int):
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