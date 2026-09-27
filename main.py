import sys

from map import MapException
from parsing import MapParsing, MapParsingException
from simulation import Simulation


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python main.py <map_file>")
        return 1
    try:
        map = MapParsing(sys.argv[1]).get_map()
        map.start()
        turns = Simulation(map).run()
    except (MapParsingException, MapException) as map_error:
        print(f"Error: {map_error}")
        return 1

    print("\n".join(turns))
    fleet = map.get_drone_count()
    drones = "drone" if fleet == 1 else "drones"
    print(f"\n{len(turns)} turns for {fleet} {drones}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
