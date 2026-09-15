"""Terminal rendering of the simulation.

* Plain mode prints exactly the format required by the subject: one
  line per turn made of ``D<ID>-<zone>`` tokens.
* Visual mode (``--visual``) adds, for every turn, the list of the
  occupied zones with the drones inside them, painted with the color
  declared in the map file, then a summary of the secondary metrics.
"""

from __future__ import annotations

import sys
import time

from map import Map
from models import Drone, Point, Transit
from scheduler import drone_cost
from simulation import Simulation, TurnReport

RESET = "\x1b[0m"
BOLD = "1"
DIM = "2"
CLEAR = "\x1b[2J\x1b[H"

ANSI_CODES = {
    "black": "90", "gray": "90", "grey": "90",
    "red": "91", "darkred": "31", "crimson": "31", "maroon": "31",
    "green": "92", "lime": "92",
    "yellow": "93", "gold": "93", "orange": "33", "brown": "33",
    "blue": "94", "cyan": "96",
    "purple": "35", "magenta": "95", "violet": "95", "pink": "95",
    "white": "97",
}
"""Map color names to ANSI codes (an unknown name gives no color)."""

RAINBOW = ["91", "33", "93", "92", "96", "94", "95"]


def colorize(text: str, color: str) -> str:
    """Wrap ``text`` in the ANSI sequence of ``color`` (a name or a code)."""
    if color == "rainbow":
        return "".join(colorize(char, RAINBOW[index % len(RAINBOW)])
                       for index, char in enumerate(text))
    code = color if color.isdigit() else ANSI_CODES.get(color, "")
    if code == "":
        return text
    return f"\x1b[{code}m{text}{RESET}"


class Renderer:
    """Print the turns of a simulation in the terminal."""

    def __init__(self, network: Map, visual: bool = False,
                 delay: float = 0.0, colored: bool = True) -> None:
        """Create the renderer.

        Args:
            network: The simulated map.
            visual: Enable the zone list and the summary.
            delay: Seconds to wait between two turns (animation).
            colored: Emit ANSI colors (only when stdout is a terminal).
        """
        self.__map = network
        self.__visual = visual
        self.__delay = delay
        self.__colored = colored and sys.stdout.isatty()
        self.__width = max(len(point.get_name()) + 1
                           for point in network.get_points())

    def paint(self, text: str, color: str) -> str:
        """Return ``text`` colored when colors are enabled."""
        return colorize(text, color) if self.__colored else text

    def paint_point(self, point: Point) -> str:
        """Return the zone name with its type marker, in its color."""
        label = point.get_name() + point.get_zone().symbol
        return self.paint(label.ljust(self.__width), point.get_color())

    def render_header(self) -> None:
        """Print a description of the map (visual mode only)."""
        if not self.__visual:
            return
        print(self.paint("Fly-in simulation", BOLD))
        print(f"{len(self.__map.get_points())} zones, "
              f"{len(self.__map.get_connections())} connections, "
              f"{self.__map.get_drone_count()} drones")
        print("Markers: * priority, ! restricted (2 turns), X blocked\n")

    def render_turn(self, report: TurnReport) -> None:
        """Print the official line of the turn, plus the zones if visual."""
        if not self.__visual:
            print(report.format_moves())
            return
        if self.__delay > 0:
            time.sleep(self.__delay)
            if self.__colored:
                print(CLEAR, end="")
                self.render_header()
        print(self.paint(f"Turn {report.turn}", BOLD)
              + f"  ({len(report.moves)} moves, "
              f"{report.remaining} drones still flying)")
        print("  " + self.__moves_line(report))
        for line in self.__zone_lines(report):
            print("  " + line)
        print()

    def __moves_line(self, report: TurnReport) -> str:
        """Return the moves of the turn, destinations in color."""
        tokens: list[str] = []
        for drone, position in report.moves:
            if isinstance(position, Transit):
                label = self.paint(position.name(), "orange")
            else:
                label = self.paint(position.get_name(), position.get_color())
            tokens.append(f"{drone.get_name()}-{label}")
        return " ".join(tokens) if tokens else self.paint("(no move)", DIM)

    def __zone_lines(self, report: TurnReport) -> list[str]:
        """Return one line per zone holding drones, plus start and end."""
        lines: list[str] = []
        for point in self.__map.get_points():
            drones = report.occupancy.get(point.get_name(), [])
            if point.is_start():
                status = f"{len(drones)} waiting"
            elif point.is_end():
                delivered = self.__map.get_drone_count() - report.remaining
                status = f"{delivered} delivered"
            elif drones:
                names = " ".join(drone.get_name() for drone in drones)
                status = f"{names}  ({len(drones)}/{point.get_max_drones()})"
            else:
                continue
            lines.append(f"{self.paint_point(point)} {status}")
        for drone, transit in report.transits:
            link = self.paint(transit.name().ljust(self.__width), "orange")
            lines.append(f"{link} {drone.get_name()} in flight -> "
                         f"{transit.get_target().get_name()}")
        return lines

    def render_summary(self, simulation: Simulation,
                       drones: list[Drone]) -> None:
        """Print the secondary metrics (visual mode only)."""
        if not self.__visual:
            return
        turns = simulation.get_total_turns()
        moves = simulation.get_total_moves()
        arrivals = [drone.arrival_turn() for drone in drones]
        print(self.paint("Summary", BOLD))
        print(f"  total turns          : {self.paint(str(turns), 'cyan')}")
        print(f"  drones delivered     : {len(drones)}")
        print(f"  movements per turn   : {moves / max(turns, 1):.2f}")
        print(f"  average turns/drone  : "
              f"{sum(arrivals) / max(len(drones), 1):.2f}")
        print(f"  total path cost      : "
              f"{sum(drone_cost(drone) for drone in drones)}")
