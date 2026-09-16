from parsing import MapParsing

if __name__ == "__main__":
    map = MapParsing('./maps/medium/02_circular_loop.txt').get_map()
    map.start()

    for path in map.solve():
        print(map.path_cost(path),
              " -> ".join(point.display_name() for point in path))
