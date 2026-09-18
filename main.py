import sys

from map import MapException
from parsing import MapParsing, MapParsingException


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python main.py <map_file>")
        return 1
    try:
        drone_map = MapParsing(sys.argv[1]).get_map()
    except (MapParsingException, MapException) as map_error:
        print(f"Error: {map_error}")
        return 1

    drone_map.start()

    for path in drone_map.solve():
        print(drone_map.path_cost(path),
              " -> ".join(point.display_name() for point in path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
