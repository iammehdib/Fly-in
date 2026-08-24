from models import Drone, Point, PointType


class MapException(Exception):

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Error in Map: {reason}")


class Map:

    def __init__(self):
        self.__drones: list[Drone] = []
        self.__points: list[Point] = []
        self.__drone_count: int = 0

    def start(self):
        if self.__drone_count == 0:
            raise MapException("Can't start the map with 0 drone")

        for drone_suffix in range(self.__drone_count):
            drone_name = "drone" + str(drone_suffix)  # TODO: To be confirmed for the name

            self.add_drone(Drone(drone_name))

        start_point = self.get_point_from_type(PointType.START)
        if start_point is None:
            raise MapException("Could not find the start point")

    def get_drones(self) -> list[Drone]:
        return self.__drones

    def get_points(self) -> list[Point]:
        return self.__points

    def set_drone_count(self, drone_count: int):
        self.__drone_count = drone_count

    def get_drone_count(self) -> int:
        return self.__drone_count

    def add_drone(self, drone: Drone):
        self.__drones.append(drone)

    def add_point(self, point: Point):
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