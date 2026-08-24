from dataclasses import dataclass

import parse

from map import Map
from models import Point, Color, Zone


@dataclass
class MapLineParsing:
    raw: str
    line: int


class MapParsingException(Exception):

    def __init__(self, line: MapLineParsing, reason: str):
        self.line = line
        self.reason = reason
        super().__init__(f"Invalid line {line.line}: {line.raw} — reason: {reason}")


class MapParsing:

    @dataclass
    class Line:
        data: str
        line: int

    def __init__(self, path_file: str):
        self.__map = Map()
        self.__path_file: str = path_file
        self.__drones_start_count: int = 0
        self.__current_line = None

        try:
            self.parse_file()
        except MapParsingException as e:
            print(e)
        except BaseException as e:
            print(f"Error in parsing file: {e}")

    def get_map(self):
        return self.__map

    def parse_file(self):
        file: str = ""
        try:
            with open(self.__path_file, 'r') as f:
                file = f.read()
        except BaseException as e:
            print(f"Error: {e}")

        lign_count: int = 1

        for line in file.split("\n"):

            self.__current_line = MapLineParsing(line.strip(), lign_count)
            raw = self.__current_line.raw
            lign_count += 1
            if raw.startswith('#') or raw.replace(" ", "") == "":
                continue

            if raw.startswith("nb_drones:"):
                self.parse_nb_drones()
            elif raw.startswith(("start_hub:", "hub:", "end_hub:")):
                self.parse_point()
            elif raw.startswith("connection:"):
                self.parse_connection()
            else:
                raise MapParsingException(self.__current_line, "invalid configuration")

    def parse_nb_drones(self):
        if self.__map.get_drone_count() != 0: return
        try:
            value = self.__current_line.raw.split(":", 1)[1].strip()
            drone_count: int = int(value)
            self.__map.set_drone_count(drone_count)
        except BaseException:
            raise MapParsingException(self.__current_line, "Invalid nb_drones value")

    def parse_point(self):
        result = parse.parse("{type}: {name} {x:d} {y:d} [{metadata}]", self.__current_line.raw)
        if result is None:
            result = parse.parse("{type}: {name} {x:d} {y:d}", self.__current_line.raw)
        if result is None:
            raise MapParsingException(self.__current_line, "Invalid hub line")

        # Check type is correct
        type: str = result["type"]
        if type not in ("start_hub", "hub", "end_hub"):
            raise MapParsingException(self.__current_line, "Invalid type value")

        # Check name is unique
        name: str = result["name"]
        for point in self.get_map().get_points():
            if point == name:
                raise MapParsingException(self.__current_line, "The point name already exist")

        # Check x and y is correct and unique position
        x: int = result["x"]
        y: int = result["y"]
        if 0 <= x and 0 <= y: # TODO: Check if is needed or not
            raise MapParsingException(self.__current_line, "The x or/and y is negative")

        for point in self.get_map().get_points():
            if x == point.get_x() and y == point.get_y():
                raise MapParsingException(self.__current_line, "The x or/and y is already set")

        # Parse metadata
        zone, color, max_drones = self.parse_meta_datas(result.named.get("metadata", ""))

        # Add point to points list
        self.__map.add_point(
            Point(
                type, x, y,
                zone, color, max_drones
            )
        )

    def parse_meta_datas(self, meta_datas_raw: str) -> tuple[Zone, Color, int]:
        zone: Zone = Zone.NORMAL # TODO: To be confirmed
        color: Color = Color.GRAY # TODO: To be confirmed
        max_drones: int = 1 # TODO: To be confirmed

        for meta_data in meta_datas_raw.split(" "):
            key, value = meta_data.split("=")
            match key:
                case "zone":
                    try:
                        zone = Zone(value)
                    except BaseException:
                        raise MapParsingException(self.__current_line, f"'{value}' is not a valid Zone")
                case "color":
                    try:
                        color = Color(value)
                    except BaseException:
                        raise MapParsingException(self.__current_line, f"'{value}' is not a valid Color")
                case "max_drones":
                    try:
                        max_drones = int(value)
                    except BaseException:
                        raise MapParsingException(self.__current_line, f"'{value}' is not a int")
                case _:
                    raise MapParsingException(self.__current_line, "The key of metadata is invalid")

        return zone, color, max_drones

    def parse_connection(self):
        result = parse.parse("connection: {a}:{b} [max_link_capacity={max_link_capacity}]",
                             self.__current_line.raw)
        if result is None:
            result = parse.parse("connection: {a}:{b}", self.__current_line.raw)
        if result is None:
            raise MapParsingException(self.__current_line, "Invalid connection")

        a = result["a"]
        b = result["b"]
        point_a = self.__map.get_point(a)
        point_b = self.__map.get_point(b)

        if point_a is None or point_b is None:
           raise MapParsingException(self.__current_line, "One of point name is not exist")

        if point_a.contain_connection(point_b) or point_b.contain_connection(point_a):
            raise MapParsingException(self.__current_line, "The link already exist")

        max_link_capacity: int = result.named.get("max_link_capacity", 1)

        point_a.add_connection(point_b, max_link_capacity)
        point_b.add_connection(point_a, max_link_capacity)



if __name__ == "__main__":
    map_parsing: MapParsing = MapParsing('./maps/easy/01_linear_path.txt')
    map_parsing.parse_file()

    for point in map_parsing.get_map().get_points():
        print(point.get_name())

    map = map_parsing.get_map()
    map.start()
