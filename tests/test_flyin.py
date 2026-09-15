"""Test-suite of Fly-in (run with ``pytest``).

The tests cover the parser (valid and invalid maps), the solver (every
provided map is solved within the reference targets) and the
simulation engine (the schedule respects every rule of the subject).
"""

from __future__ import annotations

import glob
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from map import Map, MapException  # noqa: E402
from models import PointType, Transit, Zone  # noqa: E402
from parsing import MapParsing, MapParsingException  # noqa: E402
from scheduler import Solver  # noqa: E402
from simulation import Simulation, SimulationException  # noqa: E402

MAPS = os.path.join(ROOT, "maps")
TARGETS = {
    "easy/01_linear_path.txt": 6,
    "easy/02_simple_fork.txt": 8,
    "easy/03_basic_capacity.txt": 6,
    "medium/01_dead_end_trap.txt": 12,
    "medium/02_circular_loop.txt": 15,
    "medium/03_priority_puzzle.txt": 12,
    "hard/01_maze_nightmare.txt": 30,
    "hard/02_capacity_hell.txt": 35,
    "hard/03_ultimate_challenge.txt": 45,
    "challenger/01_the_impossible_dream.txt": 45,
}
TOKEN = re.compile(r"^D\d+-[^\s]+$")


def load(relative: str) -> Map:
    """Parse a map of the ``maps`` directory."""
    return MapParsing(os.path.join(MAPS, relative)).get_map()


def solve(relative: str) -> Map:
    """Parse and schedule a map of the ``maps`` directory."""
    network = load(relative)
    Solver(network).solve()
    return network


def run(network: Map) -> list[str]:
    """Simulate a scheduled map and return the output lines."""
    return [report.format_moves() for report in Simulation(network).run()]


class TestParser:
    """Parsing of valid and invalid map files."""

    def test_example_map_from_subject(self, tmp_path: Path) -> None:
        path = os.path.join(str(tmp_path), "subject.txt")
        with open(path, "w", encoding="utf-8") as file:
            file.write(
                "nb_drones: 5\n"
                "start_hub: hub 0 0 [color=green]\n"
                "end_hub: goal 10 10 [color=yellow]\n"
                "hub: roof1 3 4 [zone=restricted color=red]\n"
                "hub: roof2 6 2 [zone=normal color=blue]\n"
                "hub: corridorA 4 3 [zone=priority color=green "
                "max_drones=2]\n"
                "hub: tunnelB 7 4 [zone=normal color=red]\n"
                "hub: obstacleX 5 5 [zone=blocked color=gray]\n"
                "connection: hub-roof1\n"
                "connection: hub-corridorA\n"
                "connection: roof1-roof2\n"
                "connection: roof2-goal\n"
                "connection: corridorA-tunnelB [max_link_capacity=2]\n"
                "connection: tunnelB-goal\n")
        network = MapParsing(path).get_map()
        assert network.get_drone_count() == 5
        assert len(network.get_points()) == 7
        assert len(network.get_connections()) == 6
        corridor = network.get_point_from_name("corridorA")
        assert corridor is not None
        assert corridor.get_zone() is Zone.PRIORITY
        assert corridor.get_max_drones() == 2
        assert corridor.get_color() == "green"
        tunnel = network.get_point_from_name("tunnelB")
        assert tunnel is not None
        link = corridor.get_connection_to(tunnel)
        assert link is not None and link.get_max_link_capacity() == 2
        assert network.get_start().get_type() is PointType.START

    def test_metadata_in_any_order_and_unknown_color(self) -> None:
        network = load("custom/ok_metadata_order.txt")
        mid = network.get_point_from_name("mid")
        assert mid is not None
        assert mid.get_zone() is Zone.PRIORITY
        assert mid.get_color() == "turquoise"
        assert mid.get_max_drones() == 2
        assert network.get_start().has_unlimited_capacity()

    @pytest.mark.parametrize("path", sorted(
        glob.glob(os.path.join(MAPS, "custom", "err_*.txt"))))
    def test_invalid_maps_raise(self, path: str) -> None:
        with pytest.raises((MapParsingException, MapException)):
            MapParsing(path)

    def test_error_reports_line_number(self) -> None:
        with pytest.raises(MapParsingException) as info:
            MapParsing(os.path.join(MAPS, "custom", "err_bad_zone_type.txt"))
        assert info.value.line.number == 3
        assert "lava" in str(info.value)

    def test_missing_file(self) -> None:
        with pytest.raises(MapException):
            MapParsing(os.path.join(MAPS, "does_not_exist.txt"))


class TestSolver:
    """Quality of the schedules."""

    @pytest.mark.parametrize("relative,target", sorted(TARGETS.items()))
    def test_reference_targets(self, relative: str, target: int) -> None:
        network = solve(relative)
        assert len(run(network)) <= target

    def test_challenger_beats_record(self) -> None:
        assert len(run(solve("challenger/01_the_impossible_dream.txt"))) < 45

    def test_blocked_zone_is_avoided(self) -> None:
        network = solve("custom/ok_blocked_shortcut.txt")
        for drone in network.get_drones():
            for position in drone.get_plan():
                assert not isinstance(position, Transit)
                assert position.get_zone().is_passable

    def test_restricted_end_uses_transit(self) -> None:
        lines = run(solve("custom/ok_restricted_end.txt"))
        assert any("relay-bunker" in line for line in lines)
        assert lines[-1].endswith("-bunker")

    def test_large_fleet(self) -> None:
        network = solve("custom/ok_many_drones.txt")
        lines = run(network)
        assert len(lines) == 52
        delivered = {token.split("-")[0] for line in lines
                     for token in line.split() if token.endswith("-goal")}
        assert len(delivered) == 200


class TestSimulation:
    """Validity of the moves replayed by the engine."""

    @pytest.mark.parametrize("relative", sorted(TARGETS))
    def test_output_format(self, relative: str) -> None:
        lines = run(solve(relative))
        assert lines
        for line in lines:
            for token in line.split():
                assert TOKEN.match(token)

    @pytest.mark.parametrize("relative", sorted(TARGETS))
    def test_rules_are_respected(self, relative: str) -> None:
        network = solve(relative)
        end = network.get_end()
        for report in Simulation(network).run():
            for name, drones in report.occupancy.items():
                point = network.get_point_from_name(name)
                assert point is not None
                if point.is_hub():
                    assert len(drones) <= point.get_max_drones()
            for drone in report.delivered:
                assert drone.position_at(report.turn) is end

    def test_engine_rejects_invalid_plan(self) -> None:
        network = load("easy/01_linear_path.txt")
        start, end = network.get_start(), network.get_end()
        for drone in network.get_drones():
            drone.set_plan([start, end])
        with pytest.raises(SimulationException):
            list(Simulation(network).run())

    def test_engine_rejects_over_capacity(self) -> None:
        network = load("easy/01_linear_path.txt")
        start, end = network.get_start(), network.get_end()
        first = network.get_point_from_name("waypoint1")
        second = network.get_point_from_name("waypoint2")
        assert first is not None and second is not None
        for drone in network.get_drones():
            drone.set_plan([start, first, second, end])
        with pytest.raises(SimulationException):
            list(Simulation(network).run())
