"""Turn-based simulation engine.

The engine replays the schedule computed by the solver turn after turn
and checks, independently of the planner, that every rule of the
subject is respected:

* a move follows an existing connection,
* blocked zones are never entered,
* restricted zones are entered through a two-turn transit, and the
  drone lands right after its transit,
* zones never exceed ``max_drones`` (start and end hubs are unlimited),
* connections never exceed ``max_link_capacity``.

Any violation raises ``SimulationException``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

from map import Map
from models import Drone, Point, Position, Transit, Zone, link_used


class SimulationException(Exception):
    """Raised when a scheduled move breaks a rule of the subject."""

    def __init__(self, turn: int, reason: str) -> None:
        """Create the error for ``turn`` explaining ``reason``."""
        self.turn = turn
        self.reason = reason
        super().__init__(f"Invalid move at turn {turn}: {reason}")


@dataclass
class TurnReport:
    """Everything that happened during one simulation turn."""

    turn: int
    moves: list[tuple[Drone, Position]] = field(default_factory=list)
    occupancy: dict[str, list[Drone]] = field(default_factory=dict)
    transits: list[tuple[Drone, Transit]] = field(default_factory=list)
    delivered: list[Drone] = field(default_factory=list)
    remaining: int = 0

    def format_moves(self) -> str:
        """Return the line of the official output format."""
        tokens: list[str] = []
        for drone, position in self.moves:
            if isinstance(position, Transit):
                destination = position.name()
            else:
                destination = position.get_name()
            tokens.append(f"{drone.get_name()}-{destination}")
        return " ".join(tokens)


class Simulation:
    """Replay and validate the schedule of a fleet."""

    def __init__(self, network: Map) -> None:
        """Prepare the simulation of ``network``."""
        self.__map = network
        self.__end = network.get_end()
        self.__total_turns = 0
        self.__total_moves = 0

    def get_total_turns(self) -> int:
        """Return the number of turns needed to deliver every drone."""
        return self.__total_turns

    def get_total_moves(self) -> int:
        """Return the number of movements printed by the simulation."""
        return self.__total_moves

    def run(self) -> Iterator[TurnReport]:
        """Simulate every turn, yielding a report for each of them."""
        flying = [drone for drone in self.__map.get_drones()
                  if drone.get_plan()]
        turn = 0
        while flying:
            turn += 1
            report = self.__play_turn(turn, flying)
            # Delivered drones are no longer tracked.
            flying = [drone for drone in flying
                      if drone.arrival_turn() > turn]
            report.remaining = len(flying)
            self.__total_turns = turn
            self.__total_moves += len(report.moves)
            yield report

    # -- one turn ---------------------------------------------------------

    def __play_turn(self, turn: int, drones: list[Drone]) -> TurnReport:
        """Apply the moves of ``turn`` and check every rule."""
        report = TurnReport(turn)
        link_usage: dict[str, int] = {}
        for drone in drones:
            previous = drone.position_at(turn - 1)
            current = drone.position_at(turn)
            if current is not previous:
                self.__check_move(turn, drone, previous, current)
                report.moves.append((drone, current))
            self.__record_position(report, drone, current)
            self.__count_link_usage(turn, link_usage, previous, current)
        self.__check_zone_capacities(turn, report)
        return report

    def __record_position(self, report: TurnReport, drone: Drone,
                          position: Position) -> None:
        """Store where ``drone`` is at the end of the turn."""
        if isinstance(position, Transit):
            report.transits.append((drone, position))
        elif position is self.__end:
            report.delivered.append(drone)
        else:
            report.occupancy.setdefault(position.get_name(), []).append(drone)

    # -- rules ------------------------------------------------------------

    @staticmethod
    def __check_move(turn: int, drone: Drone, previous: Position,
                     current: Position) -> None:
        """Check that going from ``previous`` to ``current`` is legal."""
        name = drone.get_name()
        if isinstance(previous, Transit):
            # A drone in flight must land on the zone it was flying to.
            if current is not previous.get_target():
                raise SimulationException(
                    turn, f"{name} must land on "
                    f"{previous.get_target().get_name()} after its transit")
            return
        if isinstance(current, Transit):
            # A drone may only enter a connection attached to its zone,
            # and only toward a restricted zone.
            if current.get_origin() is not previous:
                raise SimulationException(
                    turn, f"{name} enters a connection it is not on")
            if current.get_target().get_zone() is not Zone.RESTRICTED:
                raise SimulationException(
                    turn, f"{name} transits toward a non restricted zone")
            return
        Simulation.__check_direct_move(turn, name, previous, current)

    @staticmethod
    def __check_direct_move(turn: int, name: str, previous: Point,
                            current: Point) -> None:
        """Check a one-turn move between two zones."""
        if previous.get_connection_to(current) is None:
            raise SimulationException(
                turn, f"{name} jumps from {previous.get_name()} to "
                f"{current.get_name()} without connection")
        zone = current.get_zone()
        if not zone.is_passable:
            raise SimulationException(
                turn, f"{name} enters blocked zone {current.get_name()}")
        if zone is Zone.RESTRICTED:
            raise SimulationException(
                turn, f"{name} enters restricted zone {current.get_name()}"
                " in a single turn")

    @staticmethod
    def __count_link_usage(turn: int, usage: dict[str, int],
                           previous: Position, current: Position) -> None:
        """Count the drone on the connection it uses this turn, if any."""
        link = link_used(previous, current)
        if link is None:
            return
        usage[link.key()] = usage.get(link.key(), 0) + 1
        if usage[link.key()] > link.get_max_link_capacity():
            raise SimulationException(
                turn, f"connection {link.key()} exceeds its capacity "
                f"({link.get_max_link_capacity()})")

    def __check_zone_capacities(self, turn: int, report: TurnReport) -> None:
        """Check that no hub holds more drones than ``max_drones``."""
        for name, drones in report.occupancy.items():
            point = self.__map.get_point_from_name(name)
            if point is None or point.has_unlimited_capacity():
                continue
            if len(drones) > point.get_max_drones():
                raise SimulationException(
                    turn, f"zone {name} holds {len(drones)} drones, "
                    f"capacity is {point.get_max_drones()}")
