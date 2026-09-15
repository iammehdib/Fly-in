"""Path planning and turn scheduling of the fleet.

How the fleet is scheduled, in three steps:

1. ``Reservations`` remembers, turn by turn, how many drones occupy each
   zone and each connection.
2. ``PathPlanner`` finds the earliest schedule of ONE drone given those
   reservations (a Dijkstra over the states ``(zone, turn)``).
3. ``Solver`` schedules the drones one after the other, each one booking
   its path in the reservations.
"""

from __future__ import annotations

import heapq
import itertools
from typing import NamedTuple

from map import Map, MapException
from models import (Connection, Drone, Point, Position, Transit, Zone,
                    link_used)

Plan = list[Position]
"""Positions of one drone, indexed by turn (``plan[0]`` is the start)."""


# ---------------------------------------------------------------------------
# Reservations
# ---------------------------------------------------------------------------

class Reservations:
    """Per-turn occupancy of zones and connections.

    ``(zone name, turn) -> number of drones`` and
    ``(connection key, turn) -> number of drones``.
    """

    def __init__(self) -> None:
        """Create an empty reservation table."""
        self.__zones: dict[tuple[str, int], int] = {}
        self.__links: dict[tuple[str, int], int] = {}
        self.__last_turn = 0

    def get_last_turn(self) -> int:
        """Return the last turn holding at least one reservation."""
        return self.__last_turn

    def zone_has_room(self, point: Point, turn: int) -> bool:
        """Return ``True`` if ``point`` can host one more drone at ``turn``."""
        if point.has_unlimited_capacity():
            return True
        used = self.__zones.get((point.get_name(), turn), 0)
        return used < point.get_max_drones()

    def link_has_room(self, link: Connection, turn: int) -> bool:
        """Return ``True`` if one more drone can use ``link`` at ``turn``."""
        used = self.__links.get((link.key(), turn), 0)
        return used < link.get_max_link_capacity()

    def reserve(self, plan: Plan) -> None:
        """Book every zone and connection used by ``plan``."""
        self.__apply(plan, +1)

    def release(self, plan: Plan) -> None:
        """Cancel the bookings of ``plan``."""
        self.__apply(plan, -1)

    def __apply(self, plan: Plan, delta: int) -> None:
        """Add ``delta`` (+1 or -1) to every booking of ``plan``."""
        for turn in range(1, len(plan)):
            previous = plan[turn - 1]
            position = plan[turn]
            link = link_used(previous, position)
            if link is not None:
                self.__bump(self.__links, (link.key(), turn), delta)
            if isinstance(position, Point) \
                    and not position.has_unlimited_capacity():
                self.__bump(self.__zones, (position.get_name(), turn), delta)
            if delta > 0:
                self.__last_turn = max(self.__last_turn, turn)

    @staticmethod
    def __bump(table: dict[tuple[str, int], int],
               key: tuple[str, int], delta: int) -> None:
        """Increment a counter of ``table``, dropping it when it hits 0."""
        value = table.get(key, 0) + delta
        if value <= 0:
            table.pop(key, None)
        else:
            table[key] = value


# ---------------------------------------------------------------------------
# Single-drone planner
# ---------------------------------------------------------------------------

class Cost(NamedTuple):
    """Cost of reaching a state, compared field by field (tuple order).

    The first field is the real objective (arrive as early as possible).
    The two others are tie-breakers: prefer waiting in the start hub
    rather than blocking a hub for the other drones, then prefer
    ``priority`` zones as the subject asks.
    """

    turn: int
    hub_turns: int
    nonpriority_moves: int

    def wait(self, point: Point) -> Cost:
        """Return the cost after staying one more turn in ``point``."""
        return Cost(self.turn + 1,
                    self.hub_turns + (1 if point.is_hub() else 0),
                    self.nonpriority_moves)

    def move_to(self, target: Point, arrival: int) -> Cost:
        """Return the cost after entering ``target`` at ``arrival``."""
        is_priority = target.get_zone() is Zone.PRIORITY
        return Cost(arrival,
                    self.hub_turns + (1 if target.is_hub() else 0),
                    self.nonpriority_moves + (0 if is_priority else 1))

    def tie_break(self) -> tuple[int, int]:
        """Return the secondary part of the cost."""
        return self.hub_turns, self.nonpriority_moves


class State(NamedTuple):
    """A drone standing in ``point`` at the end of ``turn``."""

    point: Point
    turn: int

    def key(self) -> tuple[str, int]:
        """Return a hashable identifier of the state."""
        return self.point.get_name(), self.turn


class Step(NamedTuple):
    """How a state was reached: from ``previous``, maybe via a transit."""

    previous: State
    transit: Transit | None


class PathPlanner:
    """Earliest-arrival search for a single drone.

    This is a Dijkstra on the *time-expanded* graph: a node is a zone at
    a given turn. Waiting is an edge ``(zone, t) -> (zone, t+1)``, moving
    is an edge toward a neighbour one turn later (two turns later for a
    restricted zone). An edge exists only if the reservations leave
    room for the drone.
    """

    def __init__(self, network: Map) -> None:
        """Prepare the planner for ``network``."""
        self.__map = network
        self.__start = network.get_start()
        self.__end = network.get_end()
        # Search data, reset at every call of ``plan``.
        self.__reservations = Reservations()
        self.__heap: list[tuple[Cost, int, State]] = []
        self.__counter = itertools.count()
        self.__best: dict[tuple[str, int], tuple[int, int]] = {}
        self.__steps: dict[tuple[str, int], Step] = {}

    def plan(self, reservations: Reservations, departure: int = 0) -> Plan:
        """Return the earliest schedule compatible with ``reservations``.

        Args:
            reservations: Bookings of the drones already scheduled.
            departure: First turn at which the drone may leave the
                start hub (it waits there before).

        Raises:
            MapException: if the end zone is unreachable.
        """
        self.__reset(reservations)
        # After the last reserved turn the network is empty, so a
        # solution always exists before this horizon (safety net).
        horizon = max(reservations.get_last_turn(), departure) \
            + 2 * len(self.__map.get_points()) + 4

        first = State(self.__start, departure)
        self.__push(first, Cost(departure, 0, 0), step=None)

        while self.__heap:
            cost, _, state = heapq.heappop(self.__heap)
            if self.__is_outdated(state, cost):
                continue
            if state.point is self.__end:
                return self.__build_plan(state)
            if state.turn >= horizon:
                continue
            self.__expand_wait(state, cost)
            for link in state.point.get_connections():
                self.__expand_move(state, cost, link)

        raise MapException("no path leads from the start hub to the end hub")

    # -- search internals -------------------------------------------------

    def __reset(self, reservations: Reservations) -> None:
        """Forget the previous search."""
        self.__reservations = reservations
        self.__heap = []
        self.__counter = itertools.count()
        self.__best = {}
        self.__steps = {}

    def __is_outdated(self, state: State, cost: Cost) -> bool:
        """Return ``True`` if a cheaper way to ``state`` was found since."""
        return self.__best.get(state.key()) != cost.tie_break()

    def __expand_wait(self, state: State, cost: Cost) -> None:
        """Try to stay one more turn in the current zone."""
        next_turn = state.turn + 1
        if not self.__reservations.zone_has_room(state.point, next_turn):
            return
        self.__push(State(state.point, next_turn), cost.wait(state.point),
                    Step(state, transit=None))

    def __expand_move(self, state: State, cost: Cost,
                      link: Connection) -> None:
        """Try to fly through ``link`` toward its other endpoint."""
        target = link.other(state.point)
        zone = target.get_zone()
        if not zone.is_passable:
            return
        arrival = state.turn + zone.turns
        if not self.__reservations.zone_has_room(target, arrival):
            return
        # The link is busy during every turn of the flight (one turn for
        # a normal zone, two for a restricted one).
        for turn in range(state.turn + 1, arrival + 1):
            if not self.__reservations.link_has_room(link, turn):
                return
        transit = Transit(link, state.point) if zone.turns == 2 else None
        self.__push(State(target, arrival), cost.move_to(target, arrival),
                    Step(state, transit))

    def __push(self, state: State, cost: Cost, step: Step | None) -> None:
        """Record ``state`` if ``cost`` is the best known and queue it."""
        known = self.__best.get(state.key())
        if known is not None and known <= cost.tie_break():
            return
        self.__best[state.key()] = cost.tie_break()
        if step is not None:
            self.__steps[state.key()] = step
        # The unique counter breaks ties between equal costs, so the heap
        # never has to compare two ``State`` (``Point`` is not orderable).
        heapq.heappush(self.__heap, (cost, next(self.__counter), state))

    def __build_plan(self, last: State) -> Plan:
        """Walk the recorded steps backward to rebuild the schedule."""
        positions: Plan = []
        state = last
        while state.key() in self.__steps:
            positions.append(state.point)
            step = self.__steps[state.key()]
            if step.transit is not None:
                positions.append(step.transit)
            state = step.previous
        # ``state`` is now the first state: the drone waited in the start
        # hub from turn 0 to its departure turn.
        positions.extend([self.__start] * (state.turn + 1))
        positions.reverse()
        return positions


# ---------------------------------------------------------------------------
# Fleet solver
# ---------------------------------------------------------------------------

class Solver:
    """Schedule the whole fleet, one drone after the other."""

    EXACT_FLEET = 64
    """Fleets up to this size are searched exactly (see ``departure``)."""

    def __init__(self, network: Map) -> None:
        """Create the solver for ``network``."""
        self.__map = network
        self.__planner = PathPlanner(network)
        self.__shortest = 0

    def solve(self) -> None:
        """Compute and assign a schedule to every drone of the map.

        Each drone takes the earliest arrival still available once the
        previous drones have booked their paths. Drones are identical,
        so the order in which they are planned does not matter.
        """
        reservations = Reservations()
        previous_arrival = 0
        for drone in self.__map.get_drones():
            departure = self.departure(previous_arrival)
            plan = self.__planner.plan(reservations, departure)
            reservations.reserve(plan)
            drone.set_plan(plan)
            previous_arrival = drone.arrival_turn()
            if self.__shortest == 0:
                # The first drone flies on an empty network: its arrival
                # is the length of the shortest path.
                self.__shortest = previous_arrival

    def departure(self, previous_arrival: int) -> int:
        """Return the first turn a drone may leave the start hub.

        A drone never arrives before the one planned just before it.
        For large fleets the search therefore starts near that arrival
        (minus a margin of two shortest paths for possible detours),
        which keeps the running time linear in the number of drones
        instead of quadratic. Small fleets are always searched exactly.
        """
        if self.__map.get_drone_count() <= self.EXACT_FLEET:
            return 0
        return max(0, previous_arrival - 2 * self.__shortest)


def drone_cost(drone: Drone) -> int:
    """Return the weighted movement cost of ``drone``'s schedule.

    Entering a normal or priority zone costs 1, a restricted zone 2.
    """
    plan = drone.get_plan()
    cost = 0
    for previous, position in zip(plan, plan[1:]):
        if isinstance(position, Transit):
            continue  # counted when the drone lands
        if link_used(previous, position) is not None:
            cost += position.get_zone().turns
    return cost
