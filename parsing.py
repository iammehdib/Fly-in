from dataclasses import dataclass

import parse

from utils import debug_log
from models import Point


@dataclass
class MapLineParsing:
    raw: str
    line: int


class MapParsingException(Exception):

    def __init__(self, line: MapLineParsing, reason: str):
        self.line = line
        self.reason = reason
        super().__init__(f"Invalid line {line}: {line} — reason: {reason}")


class Map:

    @dataclass
    class Line:
        data: str
        line: int

    def __init__(self, path_file: str):
        self.__path_file: str = path_file
        self.drones_start_count: int = 1
        self.current_line = None
        self.points: list[Point] = []

        try:
            self.parse_file()
        except MapParsingException as e:
            print(e)
        except Exception as e:
            print(f"Error in parsing file: {e}")

    def parse_file(self):
        file: str = ""
        try:
            with open(self.__path_file, 'r') as f:
                file = f.read()
        except Exception as e:
            print(f"Error: {e}")

        lign_count: int = 0

        for line in file.split("\n"):

            self.current_line = MapLineParsing(line.strip(), lign_count)
            raw = self.current_line.raw
            lign_count += 1
            if raw.startswith('#') or raw.replace(" ", "") == "":
                continue

            if raw.startswith("nb_drones:"):
                self.parse_nb_drones(raw)
            elif raw.startswith(("start_hub:", "hub:", "end_hub:")):
                self.parse_point(raw)
            elif raw.startswith("connection:"):
                self.parse_point(raw)
            else:
                raise MapParsingException(self.current_line, "invalid configuration")

    def parse_nb_drones(self, line: str):
        try:
            value = line.split(":", 1)[1].strip()
            self.drones_start_count = int(value)
        except Exception:
            raise MapParsingException(self.current_line, "Invalid nb_drones value")

    def parse_point(self, line: str):
        result = parse.parse("{type}: {name} {x:d} {y:d} [{metadata}]", line)
        if result is None:
            result = parse.parse("{type}: {name} {x:d} {y:d}", line)
        if result is None:
            raise MapParsingException(self.current_line, "Invalid hub line")

        # Check type is correct
        type: str = result["type"]
        if type not in ("start_hub", "hub", "end_hub"):
            raise ValueError(self.current_line, "Invalid type value")

        # Check name is unique
        name: str = result["name"]
        for point in self.points:
            if point == name:
                raise ValueError(f"The point name already exist at line {self.lign_count}: {line!r}")

        # Check x and y is correct and unique
        self.points.append(Point(result["name"], result["x"], result["y"]))

        print(result["type"])
        print(result["name"])
        print(result["x"])
        print(result["y"])
        print(result.named.get("metadata", ""))

    def parse_connection(self, line: str):
        debug_log(f"Connection: {line}")


if __name__ == "__main__":
    test_map: Map = Map('./maps/easy/01_linear_path.txt')
    test_map.parse_file()