from map import Map, MapException
from models import Drone, Point, PointType
from scheduler import Scheduler


class Simulation:
    """Fly the whole fleet from the start hub to the end hub."""

    def __init__(self, map: Map) -> None:
        """Start a simulation on a map, before its first turn."""
        self.__map = map
        # State of the turn being played: the drones that landed during
        # it, and how many drones used each connection.
        self.__landed: list[Drone] = []
        self.__crossings: dict[tuple[str, str], int] = {}

    def get_map(self) -> Map:
        """Return the map the fleet flies on."""
        return self.__map

    def run(self) -> list[str]:
        """Play the whole simulation and return one line per turn."""
        self.prepare()

        lines: list[str] = []
        while not self.is_finished():
            moves = self.play_turn()
            if not moves:
                raise MapException("the drones are stuck: no move is "
                                   "possible any more")
            lines.append(" ".join(moves))
            if self.get_map().add_round_and_get() > 10000:
                raise MapException("the simulation does not converge")
        return lines

    def prepare(self) -> None:
        """Clear the map and hand every drone the route it will fly."""
        for point in self.get_map().get_points():
            point.clear_reservations()
        Scheduler(self.get_map()).plan()

    def is_finished(self) -> bool:
        """Return True once every drone reached the end hub."""
        for drone in self.get_map().get_drones():
            if not drone.is_delivered():
                return False
        return True

    def play_turn(self) -> list[str]:
        """Play one turn and return what each moving drone did."""
        self.__landed = []
        self.__crossings = {}

        moves = self.land_flying_drones()
        for move in self.move_waiting_drones():
            moves.append(move)
        return moves

    def land_flying_drones(self) -> list[str]:
        """Give one more turn to the drones already on a connection."""
        moves: list[str] = []
        for drone in self.get_map().get_drones():
            if not drone.is_in_transit():
                continue
            if drone.transit_tick():
                moves.append(self.land(drone))
            else:
                moves.append(self.describe(drone, self.link_display(drone)))
        return moves

    def land(self, drone: Drone) -> str:
        """Put a drone that flew its last turn into its destination."""
        destination = drone.get_transit_to()
        if destination is None:
            return ""
        drone.end_transit()
        destination.add_drone(drone)
        drone.advance()
        self.__landed.append(drone)
        return self.describe(drone, destination.display_name())

    def move_waiting_drones(self) -> list[str]:
        """Step every drone that can enter the next zone of its route."""
        # Closest to the end hub first: a zone freed this turn is
        # reusable by the drone behind during that same turn.
        moves: list[str] = []
        for drone in self.sorted_drones():
            if not self.owes_a_move(drone):
                continue

            point = drone.get_point()
            destination = drone.next_point()
            if point is None or destination is None:
                continue
            if not self.can_enter(point, destination):
                continue

            self.use_link(point, destination)
            if destination.entry_cost() > 1:
                moves.append(self.take_off(drone, point, destination))
            else:
                moves.append(self.step_in(drone, destination))
        return moves

    def owes_a_move(self, drone: Drone) -> bool:
        """Return True when a drone can still act during this turn."""
        if drone.is_in_transit() or drone.is_delivered():
            return False
        return drone not in self.__landed

    def take_off(self, drone: Drone, point: Point,
                 destination: Point) -> str:
        """Send a drone flying toward a restricted zone."""
        destination.reserve()
        point.remove_drone(drone)
        drone.start_transit(point, destination, destination.entry_cost() - 1)
        return self.describe(drone, self.link_display(drone))

    def step_in(self, drone: Drone, destination: Point) -> str:
        """Move a drone into the next zone of its route."""
        destination.add_drone(drone)
        drone.advance()
        return self.describe(drone, destination.display_name())

    def can_enter(self, point: Point, destination: Point) -> bool:
        """Return True when a drone may leave a zone for the next one."""
        if not destination.get_zone().is_passable:
            return False
        if destination.entry_cost() > 1:
            if not self.has_room_on_arrival(destination):
                return False
        elif destination.free_slots() <= 0:
            return False

        used = self.get_map().link_usage(point, destination)
        used += self.link_crossings(point, destination)
        return used < point.get_link_capacity(destination)

    def has_room_on_arrival(self, destination: Point) -> bool:
        """Return True when a drone taking off now will have a slot."""
        # The drone lands next turn, once whoever stands in the
        # zone, ahead of it on the same route, has moved on.
        if destination.get_type() is not PointType.HUB:
            return True

        incoming = 0
        for drone in self.get_map().get_drones():
            if drone.get_transit_to() is destination:
                incoming += 1
        return incoming < destination.get_max_drones()

    def use_link(self, point_a: Point, point_b: Point) -> None:
        """Record that one more drone flies on a connection this turn."""
        key = self.link_key(point_a, point_b)
        self.__crossings[key] = self.__crossings.get(key, 0) + 1

    def link_crossings(self, point_a: Point, point_b: Point) -> int:
        """Return how many drones already used a connection this turn."""
        return self.__crossings.get(self.link_key(point_a, point_b), 0)

    def sorted_drones(self) -> list[Drone]:
        """Return the fleet, the drones closest to the end hub first."""
        drones = list(self.get_map().get_drones())
        drones.sort(key=Drone.get_step, reverse=True)
        return drones

    @staticmethod
    def describe(drone: Drone, where: str) -> str:
        """Return one movement, as 'D<ID>-<zone>' or 'D<ID>-<link>'."""
        return drone.get_name() + "-" + where

    @staticmethod
    def link_display(drone: Drone) -> str:
        """Return the colored name of the connection a drone flies on."""
        origin = drone.get_transit_from()
        destination = drone.get_transit_to()
        if origin is None or destination is None:
            return ""
        return origin.display_name() + "-" + destination.display_name()

    @staticmethod
    def link_key(point_a: Point, point_b: Point) -> tuple[str, str]:
        """Return the key naming a connection, whatever its direction."""
        names = [point_a.get_name(), point_b.get_name()]
        names.sort()
        return names[0], names[1]
