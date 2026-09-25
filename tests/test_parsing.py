"""Checks on the map file parser and the whole-map validation."""

import pytest

from map import MapException
from models import Color, PointType, Zone
from parsing import MapParsing, MapParsingException

VALID_MAPS = [
    "maps/easy/01_linear_path.txt",
    "maps/easy/02_simple_fork.txt",
    "maps/easy/03_basic_capacity.txt",
    "maps/medium/01_dead_end_trap.txt",
    "maps/medium/02_circular_loop.txt",
    "maps/medium/03_priority_puzzle.txt",
    "maps/hard/01_maze_nightmare.txt",
    "maps/hard/02_capacity_hell.txt",
    "maps/hard/03_ultimate_challenge.txt",
    "maps/challenger/01_the_impossible_dream.txt",
    "maps/custom/ok_blocked_shortcut.txt",
    "maps/custom/ok_many_drones.txt",
    "maps/custom/ok_metadata_order.txt",
    "maps/custom/ok_restricted_end.txt",
    "maps/custom/ok_wide_links.txt",
]

INVALID_MAPS = [
    ("maps/custom/err_no_drones.txt", "nb_drones"),
    ("maps/custom/err_zero_drones.txt", "positive integer"),
    ("maps/custom/err_two_starts.txt", "only one start_hub"),
    ("maps/custom/err_no_end.txt", "exactly one end_hub"),
    ("maps/custom/err_dup_name.txt", "already exists"),
    ("maps/custom/err_unknown_zone.txt", "unknown zone"),
    ("maps/custom/err_dup_connection.txt", "already exist"),
    ("maps/custom/err_bad_zone_type.txt", "invalid zone type"),
    ("maps/custom/err_bad_metadata.txt", "invalid metadata"),
    ("maps/custom/err_bad_capacity.txt", "max_link_capacity"),
    ("maps/custom/err_unreachable.txt", "cannot be reached"),
]


@pytest.mark.parametrize("path", VALID_MAPS)
def test_valid_maps_are_parsed(path: str) -> None:
    drone_map = MapParsing(path).get_map()

    assert drone_map.get_drone_count() > 0
    assert drone_map.count_type(PointType.START) == 1
    assert drone_map.count_type(PointType.END) == 1


@pytest.mark.parametrize("path,reason", INVALID_MAPS)
def test_invalid_maps_are_refused(path: str, reason: str) -> None:
    with pytest.raises((MapParsingException, MapException)) as error:
        MapParsing(path)

    assert reason in str(error.value)


def test_missing_file_is_reported() -> None:
    with pytest.raises(MapException) as error:
        MapParsing("maps/custom/does_not_exist.txt")

    assert "cannot read" in str(error.value)


def test_metadata_is_read() -> None:
    drone_map = MapParsing("maps/easy/01_linear_path.txt").get_map()

    start = drone_map.get_point_from_type(PointType.START)
    assert start is not None
    assert start.get_color() is Color.GREEN
    assert start.get_zone() is Zone.NORMAL


def test_start_and_end_ignore_max_drones() -> None:
    """The subject says the capacity of both hubs is not a limit."""
    drone_map = MapParsing("maps/custom/ok_many_drones.txt").get_map()

    start = drone_map.get_point_from_type(PointType.START)
    end = drone_map.get_point_from_type(PointType.END)
    assert start is not None and end is not None
    assert start.free_slots() > drone_map.get_drone_count()
    assert end.free_slots() > drone_map.get_drone_count()


def test_connections_are_bidirectional() -> None:
    drone_map = MapParsing("maps/custom/ok_wide_links.txt").get_map()

    for point in drone_map.get_points():
        for neighbor in point.get_connections():
            assert neighbor.has_connection(point)
            assert neighbor.get_link_capacity(point) == \
                point.get_link_capacity(neighbor)
