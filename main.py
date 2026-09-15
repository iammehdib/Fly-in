"""Command line entry point of Fly-in.

Usage::

    python main.py <map_file> [--visual] [--delay SECONDS] [--no-color]

Without ``--visual`` the program prints only the official simulation
output (one line per turn). With it, a colored grid of the network is
displayed at every turn together with the secondary metrics.
"""

import argparse
import errno
import os
import sys

from display import Renderer
from map import MapException
from parsing import MapParsing, MapParsingException
from scheduler import Solver
from simulation import Simulation, SimulationException


class FlyIn:
    """Glue between the parser, the solver, the engine and the display."""

    def __init__(self, arguments: argparse.Namespace) -> None:
        """Store the command line ``arguments``."""
        self.__arguments = arguments

    @staticmethod
    def build_parser() -> argparse.ArgumentParser:
        """Return the command line parser of the program."""
        parser = argparse.ArgumentParser(
            prog="fly-in",
            description="Route a fleet of drones from the start hub to the"
                        " end hub in as few turns as possible.")
        parser.add_argument("map_file", help="path of the map to simulate")
        parser.add_argument("-v", "--visual", action="store_true",
                            help="display the colored state of the zones"
                                 " at every turn and a summary")
        parser.add_argument("-d", "--delay", type=float, default=0.0,
                            metavar="SECONDS",
                            help="animate the visual output by waiting"
                                 " between turns (implies --visual)")
        parser.add_argument("--no-color", action="store_true",
                            help="disable ANSI colors")
        return parser

    def run(self) -> int:
        """Execute the whole pipeline and return the exit code."""
        arguments = self.__arguments
        try:
            network = MapParsing(arguments.map_file).get_map()
            Solver(network).solve()
            renderer = Renderer(network,
                                visual=arguments.visual
                                or arguments.delay > 0,
                                delay=max(0.0, arguments.delay),
                                colored=not arguments.no_color)
            simulation = Simulation(network)
            renderer.render_header()
            for report in simulation.run():
                renderer.render_turn(report)
            renderer.render_summary(simulation, network.get_drones())
        except (MapParsingException, MapException,
                SimulationException) as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print("\nInterrupted.", file=sys.stderr)
            return 130
        except (BrokenPipeError, OSError) as error:
            if error.errno in (errno.EPIPE, errno.EINVAL):
                # The reader closed the pipe (e.g. `| head`): leave quietly.
                devnull = os.open(os.devnull, os.O_WRONLY)
                os.dup2(devnull, sys.stdout.fileno())
                return 0
            print(f"Error: {error}", file=sys.stderr)
            return 1
        except (RecursionError, MemoryError) as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
        return 0


def main(argv: list[str] | None = None) -> int:
    """Parse ``argv`` and run the program."""
    arguments = FlyIn.build_parser().parse_args(argv)
    return FlyIn(arguments).run()


if __name__ == "__main__":
    sys.exit(main())
