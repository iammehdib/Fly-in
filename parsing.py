"""Parser of the map file format described in the subject.

Lines are matched with the ``parse`` library (the reverse of
``str.format``): a pattern such as ``"{type}: {name} {x} {y} [{meta}]"``
extracts the fields of a line. Because a ``{}`` field matches anything
(spaces included), every extracted value is validated afterwards.

Every syntax or semantic error stops the parsing and raises a
``MapParsingException`` carrying the line number and the cause.
"""

from __future__ import annotations

from dataclasses import dataclass

import parse

from map import Map, MapException
from models import Point, PointType, Zone


@dataclass(frozen=True)
class MapLine:
    """A stripped line of the map file with its 1-based number."""

    raw: str
    number: int


class MapParsingException(Exception):
    """Raised when a line of the map file is invalid."""

    def __init__(self, line: MapLine, reason: str) -> None:
        """Create the error for ``line`` explaining ``reason``."""
        self.line = line
        self.reason = reason
        super().__init__(f"line {line.number}: {reason} -> '{line.raw}'")


class MapParsing:
    """Build a ``Map`` from a text file."""

    ZONE_METADATA = ("zone", "color", "max_drones")
    CONNECTION_METADATA = ("max_link_capacity",)
    FORBIDDEN_IN_NAMES = "-[]"

    def __init__(self, path_file: str) -> None:
        """Parse ``path_file`` immediately.

        Raises:
            MapParsingException: on any invalid line.
            MapException: when the file cannot be read or when the
                resulting map violates a structural constraint.
        """
        self.__map = Map()
        self.__current_line = MapLine("", 0)
        self.__drones_defined = False
        self.parse_file(path_file)

    def get_map(self) -> Map:
        """Return the parsed map."""
        return self.__map

    def error(self, reason: str) -> MapParsingException:
        """Build an exception for the line being parsed."""
        return MapParsingException(self.__current_line, reason)

    def parse_file(self, path_file: str) -> None:
        """Read and parse every line of the file, then validate the map."""
        try:
            with open(path_file, "r", encoding="utf-8") as file:
                content = file.read()
        except OSError as error:
            raise MapException(f"cannot read '{path_file}': "
                               f"{error.strerror}") from error

        for number, line in enumerate(content.splitlines(), start=1):
            self.__current_line = MapLine(" ".join(line.split()), number)
            self.parse_line()

        if not self.__drones_defined:
            raise MapException("missing 'nb_drones:' line")
        self.__map.validate()

    def parse_line(self) -> None:
        """Dispatch the current line to the right parser."""
        raw = self.__current_line.raw
        if raw == "" or raw.startswith("#"):
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
            raise self.error("unknown directive")

    def parse_nb_drones(self) -> None:
        """Parse ``nb_drones: <positive integer>``."""
        if self.__drones_defined:
            raise self.error("nb_drones is defined twice")
        result = parse.parse("nb_drones: {value}", self.__current_line.raw)
        if result is None:
            raise self.error("invalid nb_drones syntax")
        drone_count = self.parse_positive_int(self.field(result, "value"),
                                              "nb_drones")
        self.__map.set_drone_count(drone_count)
        self.__drones_defined = True

    def parse_point(self) -> None:
        """Parse a ``start_hub:``, ``hub:`` or ``end_hub:`` line."""
        raw = self.__current_line.raw
        result = parse.parse("{type}: {name} {x} {y} [{meta}]", raw)
        if result is None:
            result = parse.parse("{type}: {name} {x} {y}", raw)
        if result is None:
            raise self.error("invalid zone syntax, expected "
                             "'<type>: <name> <x> <y> [metadata]'")

        # Check type is correct
        point_type = PointType(self.field(result, "type"))

        # Check name is unique
        name = self.parse_name(self.field(result, "name"))
        if self.__map.get_point_from_name(name) is not None:
            raise self.error(f"zone name '{name}' is already used")
        if point_type is not PointType.HUB \
                and self.__map.count_type(point_type) > 0:
            raise self.error(f"only one {point_type.value} is allowed")

        # Check x and y is correct
        x = self.parse_int(self.field(result, "x"), "x")
        y = self.parse_int(self.field(result, "y"), "y")

        # Parse metadata
        zone, color, max_drones = self.parse_zone_metadata(
            result.named.get("meta", ""))

        # Add point to points list
        self.__map.add_point(Point(name, point_type, x, y,
                                   zone, color, max_drones))

    def parse_connection(self) -> None:
        """Parse a ``connection: <a>-<b> [metadata]`` line."""
        raw = self.__current_line.raw
        result = parse.parse("connection: {a}-{b} [{meta}]", raw)
        if result is None:
            result = parse.parse("connection: {a}-{b}", raw)
        if result is None:
            raise self.error("invalid connection syntax, expected "
                             "'connection: <zone1>-<zone2> [metadata]'")

        point_a = self.find_point(self.parse_name(self.field(result, "a")))
        point_b = self.find_point(self.parse_name(self.field(result, "b")))
        values = self.parse_metadata_block(result.named.get("meta", ""),
                                           self.CONNECTION_METADATA)
        capacity = 1
        if "max_link_capacity" in values:
            capacity = self.parse_positive_int(values["max_link_capacity"],
                                               "max_link_capacity")
        try:
            self.__map.add_connection(point_a, point_b, capacity)
        except MapException as error:
            raise self.error(error.reason) from error

    def parse_metadata_block(self, meta: str,
                             allowed: tuple[str, ...]) -> dict[str, str]:
        """Split a ``key=value key=value`` block into a dictionary."""
        values: dict[str, str] = {}
        for token in meta.split():
            key, equal, value = token.partition("=")
            if equal == "" or key == "" or value == "":
                raise self.error(f"invalid metadata '{token}', expected "
                                 "'key=value'")
            if key not in allowed:
                raise self.error(f"unknown metadata '{key}' (allowed: "
                                 f"{', '.join(allowed)})")
            if key in values:
                raise self.error(f"metadata '{key}' is defined twice")
            values[key] = value
        return values

    def parse_zone_metadata(self, meta: str) -> tuple[Zone, str, int]:
        """Parse the metadata block of a zone line."""
        values = self.parse_metadata_block(meta, self.ZONE_METADATA)
        zone = Zone.NORMAL
        if "zone" in values:
            try:
                zone = Zone(values["zone"])
            except ValueError:
                raise self.error(f"invalid zone type '{values['zone']}' "
                                 "(normal, blocked, restricted, priority)")
        color = values.get("color", "none")
        max_drones = 1
        if "max_drones" in values:
            max_drones = self.parse_positive_int(values["max_drones"],
                                                 "max_drones")
        return zone, color, max_drones

    def field(self, result: parse.Result, key: str) -> str:
        """Return the field ``key`` of a parse result as a single token.

        A ``{}`` field of ``parse`` swallows everything, spaces included:
        a space inside it means the line has an unexpected extra token.
        """
        value = str(result[key])
        if " " in value:
            raise self.error(f"unexpected token in '{value}'")
        return value

    def parse_name(self, name: str) -> str:
        """Check that a zone name has no dash, space or bracket."""
        if name == "" or any(char in name
                             for char in self.FORBIDDEN_IN_NAMES):
            raise self.error(f"invalid zone name '{name}' (dashes, spaces "
                             "and brackets are forbidden)")
        return name

    def find_point(self, name: str) -> Point:
        """Return the zone called ``name`` (it must already exist)."""
        point = self.__map.get_point_from_name(name)
        if point is None:
            raise self.error(f"unknown zone '{name}' (zones must be "
                             "defined before their connections)")
        return point

    def parse_int(self, value: str, what: str) -> int:
        """Convert ``value`` to an integer (optional sign, digits only)."""
        digits = value[1:] if value[:1] in "+-" else value
        if not (digits.isascii() and digits.isdecimal()):
            raise self.error(f"{what} must be an integer, got '{value}'")
        return int(value)

    def parse_positive_int(self, value: str, what: str) -> int:
        """Convert ``value`` to a strictly positive integer."""
        number = self.parse_int(value, what)
        if number <= 0:
            raise self.error(f"{what} must be a positive integer, "
                             f"got {number}")
        return number
