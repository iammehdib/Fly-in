from map import Map, MapException
from models import Point, Zone


class Scheduler:
    """Choose the route every drone of the fleet will follow.

    The routes are picked once, before the first turn: the map never
    changes, so replanning during the simulation would only cost time.
    """

    def __init__(self, map: Map) -> None:
        self.__map = map
        # Slots the routes kept so far have already booked.
        self.__zone_load: dict[str, int] = {}
        self.__link_load: dict[tuple[str, str], int] = {}

    def get_map(self) -> Map:
        return self.__map

    def plan(self) -> None:
        """Give every drone the route it will fly."""
        routes = self.pick_routes()
        if not routes:
            raise MapException("no path joins the start hub to the end hub")
        self.deal_drones(routes)

    def pick_routes(self) -> list[list[Point]]:
        """Keep the cheapest routes that can all be flown at once.

        Two drones whose routes fight over the same zone can each hold
        what the other waits for, and neither moves again. A route is
        only kept when every zone and every connection it borrows still
        has a free slot for it: each route then owns a slot all along
        its way, so its drones always move forward and no deadlock can
        happen. The hubs are left out, they hold the whole fleet.
        """
        self.__zone_load = {}
        self.__link_load = {}

        routes: list[list[Point]] = []
        for path in self.sorted_paths():
            if not self.fits(path):
                continue
            self.book(path)
            routes.append(path)
        return routes

    def sorted_paths(self) -> list[list[Point]]:
        """Return every path, the ones worth flying first."""
        paths = self.get_map().solve()
        paths.sort(key=self.rank)
        return paths

    @staticmethod
    def rank(path: list[Point]) -> tuple[int, int]:
        """Rank a path by its cost, then by the priority zones it uses.

        A priority zone costs one turn, exactly like a normal one, so
        preferring it can never make a route slower: it only settles
        which of two equally fast paths is kept and flown.
        """
        priority = 0
        for point in path[1:-1]:
            if point.get_zone() is Zone.PRIORITY:
                priority += 1
        return Map.path_cost(path), -priority

    def fits(self, path: list[Point]) -> bool:
        """Return True when one more route still fits along a path."""
        for point in path[1:-1]:
            if self.zone_load(point) + 1 > point.get_max_drones():
                return False

        for origin, target in self.links(path):
            if self.link_load(origin, target) + 1 \
                    > origin.get_link_capacity(target):
                return False
        return True

    def book(self, path: list[Point]) -> None:
        """Book one slot for a route in every zone and link it uses."""
        for point in path[1:-1]:
            self.__zone_load[point.get_name()] = self.zone_load(point) + 1

        for origin, target in self.links(path):
            key = self.link_key(origin, target)
            self.__link_load[key] = self.link_load(origin, target) + 1

    def zone_load(self, point: Point) -> int:
        """Return how many routes already booked a zone."""
        return self.__zone_load.get(point.get_name(), 0)

    def link_load(self, point_a: Point, point_b: Point) -> int:
        """Return how many routes already booked a connection."""
        return self.__link_load.get(self.link_key(point_a, point_b), 0)

    def deal_drones(self, routes: list[list[Point]]) -> None:
        """Send each drone on the route that will deliver it first.

        A route already carrying drones makes the next one wait behind
        them, so its queue is added to its cost: a long empty route can
        beat a short crowded one.
        """
        load: list[int] = []
        for _ in routes:
            load.append(0)

        for drone in self.get_map().get_drones():
            best = 0
            index = 0
            for route in routes:
                if Map.path_cost(route) + load[index] \
                        < Map.path_cost(routes[best]) + load[best]:
                    best = index
                index += 1
            drone.set_path(routes[best])
            load[best] += 1

    @staticmethod
    def links(path: list[Point]) -> list[tuple[Point, Point]]:
        """Return the connections a path goes through, in order."""
        links: list[tuple[Point, Point]] = []
        previous = path[0]
        for point in path[1:]:
            links.append((previous, point))
            previous = point
        return links

    @staticmethod
    def link_key(point_a: Point, point_b: Point) -> tuple[str, str]:
        """Return the key naming a connection, whatever its direction."""
        names = [point_a.get_name(), point_b.get_name()]
        names.sort()
        return names[0], names[1]
