from parsing import MapParsing

if __name__ == "__main__":
    map_parsing: MapParsing = MapParsing('./maps/challenger/01_the_impossible_dream.txt')

    for p in map_parsing.get_map().get_points():
        print(p.get_type(), p.get_name(),
              p.get_x(), p.get_y(),
              p.get_color(), p.get_zone(), p.get_max_drones()
        )

    map = map_parsing.get_map()
    map.start()
