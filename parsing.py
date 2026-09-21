from dataclasses import dataclass

import parse  # type: ignore[import-untyped]

from map import Map, MapException
from models import Point, Color, Zone, PointType


@dataclass
class MapLineParsing:
    raw: str
    line: int


class MapParsingException(Exception):

    def __init__(self, line: MapLineParsing, reason: str) -> None:
        self.line = line
        self.reason = reason
        super().__init__(f"invalid line {line.line} "
                         f"'{line.raw}': {reason}")


class MapParsing:

    ZONE_METADATA = ("zone", "color", "max_drones")
    CONNECTION_METADATA = ("max_link_capacity",)
    FORBIDDEN_IN_NAMES = "-[] \t"

    def __init__(self, path_file: str) -> None:
        self.__map = Map()
        self.__drones_defined: bool = False
        self.__current_line = MapLineParsing("", 0)
        self.parse_file(path_file)

    def get_map(self) -> Map:
        return self.__map

    def error(self, reason: str) -> MapParsingException:
        """Build the exception pointing at the line being parsed."""
        return MapParsingException(self.__current_line, reason)

    def parse_file(self, parse_file: str) -> None:
        try:
            with open(parse_file, 'r', encoding="utf-8") as file:
                content = file.read()
        except (OSError, UnicodeDecodeError) as error:
            raise MapException(f"cannot read '{parse_file}': "
                               f"{error}") from error

        for number, line in enumerate(content.splitlines(), start=1):
            self.__current_line = MapLineParsing(" ".join(line.split()),
                                                 number)
            self.parse_line()

        # Out of the loop: there is no current line anymore, so what is
        # left to check is about the map as a whole.
        if not self.__drones_defined:
            raise MapException("missing 'nb_drones:' line")
        self.get_map().validate()

    def parse_line(self) -> None:
        raw = self.__current_line.raw
        if raw == "" or raw.startswith('#'):
            return

        if raw.startswith("nb_drones:"):
            self.parse_nb_drones()
            return

        if not self.__drones_defined:
            raise self.error("the first line must be 'nb_drones: <n>'")

        if raw.startswith(("start_hub:", "hub:", "end_hub:")):
            self.parse_point()
        elif raw.startswith("connection:"):
            self.parse_connection()
        else:
            raise self.error("invalid configuration")

    def parse_nb_drones(self) -> None:
        if self.__drones_defined:
            raise self.error("nb_drones is defined twice")

        value = self.__current_line.raw.split(":", 1)[1].strip()
        self.get_map().set_drone_count(
            self.parse_positive_int(value, "nb_drones"))
        self.__drones_defined = True

    def parse_point(self) -> None:
        raw = self.__current_line.raw
        result = parse.parse("{type}: {name} {x} {y} [{metadata}]", raw)
        if result is None:
            result = parse.parse("{type}: {name} {x} {y}", raw)
        if result is None:
            raise self.error("invalid zone syntax, expected "
                             "'<type>: <name> <x> <y> [metadata]'")

        # Check type is correct
        point_type: PointType = PointType(self.field(result, "type"))

        # Check name is valid and unique
        name: str = self.parse_name(self.field(result, "name"))
        if self.get_map().get_point_from_name(name) is not None:
            raise self.error(f"the zone name '{name}' already exists")

        # Only one start hub and one end hub are allowed
        if point_type is not PointType.HUB \
                and self.get_map().count_type(point_type) > 0:
            raise self.error(f"only one {point_type.value} is allowed")

        # Check x and y are integers and the position is free
        x: int = self.parse_int(self.field(result, "x"), "x")
        y: int = self.parse_int(self.field(result, "y"), "y")
        for point in self.get_map().get_points():
            if x == point.get_x() and y == point.get_y():
                raise self.error(f"position {x} {y} is already used by "
                                 f"'{point.get_name()}'")

        # Parse metadata
        zone, color, max_drones = self.parse_metadata(
            point_type, result.named.get("metadata", ""))

        # Add point to points list
        self.get_map().add_point(
            Point(name, point_type, x, y, zone, color, max_drones))

    def parse_metadata(self, point_type: PointType,
                       meta_datas_raw: str) -> tuple[Zone, Color, int]:
        values = self.parse_metadata_block(meta_datas_raw,
                                           self.ZONE_METADATA)

        zone: Zone = Zone.NORMAL
        if "zone" in values:
            try:
                zone = Zone(values["zone"])
            except ValueError:
                raise self.error(f"invalid zone type '{values['zone']}' "
                                 "(normal, blocked, restricted, priority)")

        # The subject allows any single-word color and fixes no list, so
        # a color we cannot render falls back to no color at all.
        color: Color = Color.UNDEFINED
        if "color" in values:
            try:
                color = Color(values["color"])
            except ValueError:
                color = Color.UNDEFINED

        # The start and end hubs have an unlimited capacity: max_drones
        # is still validated there, but ignored.
        max_drones: int = 1
        if "max_drones" in values:
            value = self.parse_positive_int(values["max_drones"],
                                            "max_drones")
            if point_type is PointType.HUB:
                max_drones = value

        return zone, color, max_drones

    def parse_metadata_block(self, meta: str,
                             allowed: tuple[str, ...]) -> dict[str, str]:
        """Split a 'key=value key=value' block into a dictionary."""
        values: dict[str, str] = {}
        for token in meta.split():
            key, equal, value = token.partition("=")
            if equal == "" or key == "" or value == "":
                raise self.error(f"invalid metadata '{token}', "
                                 "expected 'key=value'")
            if key not in allowed:
                raise self.error(f"unknown metadata '{key}' "
                                 f"(allowed: {', '.join(allowed)})")
            if key in values:
                raise self.error(f"metadata '{key}' is defined twice")
            values[key] = value
        return values

    def parse_connection(self) -> None:
        raw = self.__current_line.raw
        result = parse.parse("connection: {a}-{b} [{metadata}]", raw)
        if result is None:
            result = parse.parse("connection: {a}-{b}", raw)
        if result is None:
            raise self.error("invalid connection syntax, expected "
                             "'connection: <zone1>-<zone2> [metadata]'")

        point_a = self.find_point(self.parse_name(self.field(result, "a")))
        point_b = self.find_point(self.parse_name(self.field(result, "b")))

        if point_a is point_b:
            raise self.error(f"'{point_a.get_name()}' cannot be connected "
                             "to itself")

        if point_a.has_connection(point_b) or point_b.has_connection(point_a):
            raise self.error("the link already exist")

        values = self.parse_metadata_block(
            result.named.get("metadata", ""), self.CONNECTION_METADATA)
        max_link_capacity: int = 1
        if "max_link_capacity" in values:
            max_link_capacity = self.parse_positive_int(
                values["max_link_capacity"], "max_link_capacity")

        point_a.add_connection(point_b, max_link_capacity)
        point_b.add_connection(point_a, max_link_capacity)

    def field(self, result: parse.Result, key: str) -> str:
        """Return a captured field, refusing an unexpected extra token.

        A '{}' field of parse swallows everything, spaces included, so a
        space inside it means the line holds one token too many.
        """
        value = str(result[key])
        if " " in value:
            raise self.error(f"unexpected token in '{value}'")
        return value

    def parse_name(self, name: str) -> str:
        if name == "" or any(char in name
                             for char in self.FORBIDDEN_IN_NAMES):
            raise self.error(f"invalid zone name '{name}' (dashes, spaces "
                             "and brackets are forbidden)")
        return name

    def find_point(self, name: str) -> Point:
        point = self.get_map().get_point_from_name(name)
        if point is None:
            raise self.error(f"unknown zone '{name}' (zones must be "
                             "defined before their connections)")
        return point

    def parse_int(self, value: str, what: str) -> int:
        digits = value[1:] if value[:1] in "+-" else value
        if not (digits.isascii() and digits.isdecimal()):
            raise self.error(f"{what} must be an integer, got '{value}'")
        return int(value)

    def parse_positive_int(self, value: str, what: str) -> int:
        number = self.parse_int(value, what)
        if number <= 0:
            raise self.error(f"{what} must be a positive integer, "
                             f"got {number}")
        return number
