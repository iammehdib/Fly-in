"""Checks on the drones, the zones and the rules they enforce."""

from map import Map
from models import Color, Drone, Point, PointType, Zone
from parsing import MapParsing


def make_point(name: str, zone: Zone = Zone.NORMAL,
               max_drones: int = 1,
               point_type: PointType = PointType.HUB) -> Point:
    return Point(name, point_type, 0, 0, zone, Color.UNDEFINED, max_drones)


def test_drone_name_follows_the_output_format() -> None:
    assert Drone(1).get_name() == "D1"
    assert Drone(12).get_name() == "D12"


def test_colors_are_real_escape_sequences() -> None:
    assert Color.RED.ansi.startswith("\033[")
    assert Color.RED.colorize("x").endswith("\033[0m")
    assert Color.UNDEFINED.colorize("x") == "x"


def test_zone_costs_and_passability() -> None:
    assert Zone.RESTRICTED.turns == 2
    assert Zone.NORMAL.turns == 1
    assert Zone.PRIORITY.turns == 1
    assert Zone.BLOCKED.is_passable is False
    assert Zone.PRIORITY.preference > Zone.NORMAL.preference


def test_a_drone_belongs_to_one_zone_at_a_time() -> None:
    first = make_point("first")
    second = make_point("second")
    drone = Drone(1)

    first.add_drone(drone)
    assert first.has_drone(drone)

    second.add_drone(drone)
    assert second.has_drone(drone)
    assert first.has_drones() is False
    assert drone.get_point() is second


def test_removing_an_absent_drone_is_harmless() -> None:
    point = make_point("point")

    point.remove_drone(Drone(1))

    assert point.count_drones() == 0


def test_capacity_is_reserved_for_the_current_turn() -> None:
    point = make_point("point", max_drones=2)

    assert point.free_slots() == 2
    assert point.reserve() is True
    assert point.reserve() is True
    assert point.free_slots() == 0
    assert point.reserve() is False


def test_an_arrival_consumes_its_reservation() -> None:
    point = make_point("point", max_drones=1)
    drone = Drone(1)

    point.reserve()
    point.add_drone(drone)

    assert point.get_reservations() == 0
    assert point.free_slots() == 0
    assert point.count_drones() == 1


def test_reservations_can_be_dropped() -> None:
    point = make_point("point", max_drones=1)

    point.reserve()
    point.clear_reservations()

    assert point.free_slots() == 1


def test_the_two_hubs_have_no_capacity_limit() -> None:
    start = make_point("start", point_type=PointType.START)
    end = make_point("end", point_type=PointType.END)

    for number in range(1, 20):
        start.add_drone(Drone(number))

    assert start.free_slots() > 0
    assert end.free_slots() > 0


def test_link_capacity_is_readable() -> None:
    first = make_point("first")
    second = make_point("second")
    stranger = make_point("stranger")

    first.add_connection(second, 3)

    assert first.get_link_capacity(second) == 3
    assert first.get_link_capacity(stranger) == 0


def test_transit_lasts_the_cost_of_the_zone() -> None:
    origin = make_point("origin")
    destination = make_point("destination", Zone.RESTRICTED)
    drone = Drone(1)

    drone.start_transit(origin, destination, destination.entry_cost())

    assert drone.is_in_transit() is True
    assert drone.display_position() == "origin-destination"
    assert drone.transit_tick() is False
    assert drone.transit_tick() is True

    drone.end_transit()
    destination.add_drone(drone)

    assert drone.is_in_transit() is False
    assert drone.display_position() == "destination"


def test_a_link_is_recognised_in_both_directions() -> None:
    origin = make_point("origin")
    destination = make_point("destination")
    stranger = make_point("stranger")
    drone = Drone(1)

    drone.start_transit(origin, destination, 2)

    assert drone.is_on_link(origin, destination) is True
    assert drone.is_on_link(destination, origin) is True
    assert drone.is_on_link(origin, stranger) is False


def test_link_usage_counts_the_flying_drones() -> None:
    drone_map = Map()
    origin = make_point("origin")
    destination = make_point("destination")
    drone_map.add_point(origin)
    drone_map.add_point(destination)

    flying = Drone(1)
    waiting = Drone(2)
    drone_map.add_drone(flying)
    drone_map.add_drone(waiting)
    flying.start_transit(origin, destination, 2)

    assert drone_map.link_usage(origin, destination) == 1

    flying.end_transit()

    assert drone_map.link_usage(origin, destination) == 0


def test_a_drone_walks_along_its_path() -> None:
    first = make_point("first")
    second = make_point("second")
    third = make_point("third")
    drone = Drone(1)

    drone.set_path([first, second, third])

    assert drone.get_step() == 0
    assert drone.next_point() is second

    drone.advance()
    assert drone.next_point() is third

    drone.advance()
    assert drone.next_point() is None


def test_a_drone_is_delivered_in_the_end_hub() -> None:
    hub = make_point("hub")
    end = make_point("goal", point_type=PointType.END)
    drone = Drone(1)

    hub.add_drone(drone)
    assert drone.is_delivered() is False

    end.add_drone(drone)
    assert drone.is_delivered() is True


def test_the_fleet_starts_numbered_in_the_start_hub() -> None:
    drone_map = MapParsing("maps/easy/02_simple_fork.txt").get_map()

    drone_map.start()

    start = drone_map.get_point_from_type(PointType.START)
    assert start is not None
    assert start.count_drones() == drone_map.get_drone_count()

    names = []
    for drone in drone_map.get_drones():
        names.append(drone.get_name())
    assert names[0] == "D1"
    assert len(names) == drone_map.get_drone_count()


def test_paths_avoid_blocked_zones() -> None:
    drone_map = MapParsing("maps/custom/ok_blocked_shortcut.txt").get_map()

    for path in drone_map.solve():
        for point in path:
            assert point.get_zone().is_passable
