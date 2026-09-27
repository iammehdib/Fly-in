*This project has been created as part of the 42 curriculum by mbuchet.*

# Fly-in

## Description

Fly-in is a drone routing simulator. A map file describes a network of
zones joined by bidirectional connections, and a fleet of drones that
all start in the same hub. The program moves the whole fleet to the end
hub in **as few simulation turns as possible**, while respecting every
constraint the map sets: how many drones a zone can hold, how many can
cross a connection at the same time, which zones are forbidden, and
which ones take two turns to enter.

The program reads a map, refuses it with a clear message if it is
invalid, then prints the simulation turn by turn: one line per turn,
listing every drone that moved and where it went.

The project is written in Python 3.10+, is fully type annotated, passes
`flake8` and `mypy --strict`, and uses no graph library: the graph, the
pathfinding and the scheduling are all written from scratch.

## Instructions

### Requirements

- Python 3.10 or later
- [uv](https://docs.astral.sh/uv/) (the Makefile drives everything
  through it): `curl -LsSf https://astral.sh/uv/install.sh | sh`

### Installation

```sh
make install
```

Creates the virtual environment and installs the only runtime
dependency, `parse`, plus `flake8` and `mypy`.

### Running

```sh
make run                                    # default map
make run MAP=maps/hard/03_ultimate_challenge.txt
```

or directly:

```sh
uv run python main.py maps/medium/02_circular_loop.txt
```

### Other rules

| Rule | What it does |
| --- | --- |
| `make install` | Creates `.venv` and installs the dependencies. |
| `make run` | Runs the simulation on `$(MAP)`. |
| `make debug` | Runs the same thing under `pdb`. |
| `make lint` | `flake8 .` and `mypy .` with the mandatory flags. |
| `make lint-strict` | `flake8 .` and `mypy . --strict`. |
| `make clean` | Removes `__pycache__`, `.mypy_cache` and `dist`. |

## Map format

```
# Comments start with '#' and are ignored.
nb_drones: 4

start_hub: start 0 0 [color=green]
hub: junction 1 0 [color=yellow max_drones=2]
hub: path_a 2 1 [color=blue]
hub: path_b 2 -1 [color=blue]
end_hub: goal 3 0 [color=red]

connection: start-junction [max_link_capacity=2]
connection: junction-path_a
connection: junction-path_b
connection: path_a-goal
connection: path_b-goal
```

- The first line must be `nb_drones: <positive integer>`.
- Zones: `start_hub:`, `end_hub:` and `hub:`, each with a unique name,
  integer coordinates and an optional metadata block.
- Zone metadata: `zone=` (`normal`, `blocked`, `restricted`,
  `priority`), `color=` (any single word), `max_drones=` (default 1,
  ignored on both hubs, which have no limit). Tags come in any order.
- Connections: `connection: <zone1>-<zone2> [max_link_capacity=<n>]`,
  bidirectional, between zones already defined. A connection cannot
  appear twice, in either direction.
- Zone names cannot contain a dash, a space or a bracket.

Any other content stops the program with the line number and the cause.

## Example

Input (`maps/easy/02_simple_fork.txt`, the map above):

```sh
uv run python main.py maps/easy/02_simple_fork.txt
```

Expected output (zone names are colored in a real terminal):

```
D1-junction D2-junction
D1-path_a D2-path_b D3-junction D4-junction
D1-goal D2-goal D3-path_a D4-path_b
D3-goal D4-goal

4 turns for 4 drones
```

Turn 1, two drones enter `junction`, which is all it can hold. Turn 2,
they split over the two branches, which frees `junction` for the two
others **during the same turn**. Four drones are delivered in four
turns, the theoretical minimum for this map.

A drone flying toward a `restricted` zone needs two turns, and shows
the connection it is on in between:

```
D1-relay D2-relay
D1-relay-bunker D3-relay
D1-bunker D2-relay-bunker
```

An invalid map stops the program:

```
$ uv run python main.py maps/custom/err_bad_zone_type.txt
Error: invalid line 3 'hub: mid 1 0 [zone=lava]': invalid zone type
'lava' (normal, blocked, restricted, priority)
```

## Algorithm choices and implementation strategy

The program is split in four stages, one class each.

### 1. Parsing — `parsing.py`

`MapParsing` reads the file once, line by line, and builds the map as
it goes. Every rule that can be attached to a line is checked there and
raises `MapParsingException`, which carries the line number and the raw
line. The rules that only make sense on the finished map — exactly one
start hub, exactly one end hub, a positive drone count, and an end hub
actually reachable — are checked by `Map.validate()` once the file is
closed, and raise `MapException` with no line number.

The file is read through a context manager, and `OSError` and
`UnicodeDecodeError` are turned into the same clear error, so an
unreadable or binary file never produces a traceback.

### 2. Pathfinding — `map.py`

`Map.find_paths()` is a depth-first search that enumerates every simple
path from the start hub to the end hub, skipping `blocked` zones and
never visiting the same zone twice. `Map.path_cost()` weights a path by
the zone types it crosses (`restricted` costs 2 turns, everything else
1), and `Map.solve()` returns the paths sorted by cost.

Enumerating every path is exponential in theory. It is affordable here
because the maps are small and the search prunes blocked zones and
cycles: the largest provided map (the challenger, 25 drones) yields
6454 paths in about half a second, and the result is computed **once**
per run, never inside the turn loop.

`Map.is_end_reachable()` is a plain breadth-first search used at
validation time, so an unsolvable map is rejected before any work.

### 3. Scheduling — `scheduler.py`

This is where the strategy lives. Two decisions:

**Which routes to fly.** Paths are ranked by cost, then by the number
of `priority` zones they cross. A priority zone costs one turn exactly
like a normal one, so preferring it can never make a route slower: it
only settles which of two equally fast paths is kept, which is what the
subject asks for.

The ranked paths are then filtered: a path is kept only if **every zone
and every connection it uses still has a free slot for it**, counting
the routes already kept (`max_drones` and `max_link_capacity`). Each
kept route therefore owns one slot all along its way.

That rule is the heart of the design. Its consequence is that **a
deadlock is impossible**: the leading drone of a route always has room
in its next zone, so it always moves, and by induction the whole queue
behind it moves too. Two drones can never end up each holding what the
other is waiting for. The price is that some routes which *might* have
worked by sharing a zone are refused — a deliberate trade of a few
turns on one map for a guarantee that holds on any map.

**Which drone flies which route.** Each drone takes the route
minimising `path cost + drones already assigned to it`. The queue is
part of the cost, so a long empty route beats a short crowded one, and
the fleet spreads over the network instead of piling up on the fastest
path.

### 4. Simulation — `simulation.py`

`Simulation.run()` loops until every drone is delivered. Each turn has
two phases, in this order:

1. **The drones already flying.** A drone heading for a `restricted`
   zone spends one extra turn on the connection. Its slot in the
   destination was booked when it took off, so it always lands on time
   — the subject forbids waiting on a connection. Landing frees the
   connection and fills the zone before anybody else decides.
2. **The drones on the ground**, served **closest to the end hub
   first**. This ordering is what makes a queue advance as a whole: the
   leading drone leaves its zone, which frees it for the drone right
   behind, inside the same turn. Without it a convoy would only creep
   forward one drone per turn.

A move is allowed only if the destination is passable, has room
(`free_slots()` already deducts the drones flying toward it), and the
connection is not saturated — counting both the drones in transit on it
and the ones crossing it during this very turn.

Entering a `restricted` zone makes the drone leave its zone at once,
book its arrival slot and spend `cost - 1` extra turns on the
connection. Entering any other zone is immediate.

If a whole turn produces no move at all, the state can never change
again, so the program stops with `the drones are stuck` instead of
looping forever.

### Answers to the questions the subject asks

- **Complexity.** Path enumeration is exponential in the worst case but
  runs once; route selection is `O(P × L)` for `P` paths of length `L`;
  dealing `D` drones over `R` routes is `O(D × R)`; a turn is
  `O(D log D)` for the ordering plus `O(D)` for the moves. In practice
  the whole challenger map runs in well under a second.
- **Caching.** Paths are computed once in `prepare()` and each drone
  keeps its route. Nothing is recomputed during the turn loop.
- **Many drones.** The turn loop cost does not depend on the size of
  the map, only on the fleet. 200 drones on a small custom map are
  delivered in 52 turns without any slowdown.
- **Memory.** One `Point` object per zone, one `Drone` per drone, and
  the list of enumerated paths — which is the only structure that grows
  with the topology.

## Visual representation

The simulation writes to the terminal, and every zone name is printed
in the color its metadata declares (`color=`), through true-color ANSI
escape sequences built in `models.Color`:

- **Twenty named colors** plus `rainbow`, which colors a name one
  character at a time.
- A color the program does not know is **not an error**: the name is
  printed plain, as the subject allows any single word.
- A drone in transit shows both ends of its connection, each in its own
  color: `D1-relay-bunker`.
- A summary line closes the run with the number of turns and the size
  of the fleet.

**How it helps.** The output is the exact format the subject requires,
so it stays machine-readable, but the colors turn it into something a
reader can follow: map authors give bottlenecks, priority zones and
dead ends distinct colors, so a glance at a line shows *which part of
the network* the fleet is in, without looking the zone names up in the
map file. Watching a green start, a yellow bottleneck and a red goal
appear in sequence makes a queue or a traffic jam visible immediately —
where a plain white list of names would all look the same.

## Performance

Measured on the maps shipped with the subject, all targets met:

| Map | Drones | Turns | Target |
| --- | --- | --- | --- |
| `easy/01_linear_path` | 2 | **4** | ≤ 6 |
| `easy/02_simple_fork` | 4 | **4** | ≤ 8 |
| `easy/03_basic_capacity` | 4 | **4** | ≤ 6 |
| `medium/01_dead_end_trap` | 5 | **8** | ≤ 12 |
| `medium/02_circular_loop` | 6 | **15** | ≤ 15 |
| `medium/03_priority_puzzle` | 5 | **7** | ≤ 12 |
| `hard/01_maze_nightmare` | 8 | **13** | ≤ 30 |
| `hard/02_capacity_hell` | 12 | **16** | ≤ 35 |
| `hard/03_ultimate_challenge` | 15 | **26** | ≤ 45 |
| `challenger/01_the_impossible_dream` | 25 | 67 | 45 (optional) |

The challenger map is solved but does not beat the reference record:
the deadlock-free rule described above refuses routes that share a
slot, which costs turns on a map built to force sharing. That level is
optional and does not affect the grade.

## Project structure

```
main.py         entry point: argument, error reporting, output
parsing.py      MapParsing: reads a map file, validates every line
map.py          Map: the graph, whole-map validation, pathfinding
models.py       Point, Drone, Zone, PointType, Color
scheduler.py    Scheduler: picks the routes and deals the drones
simulation.py   Simulation: plays the turns and prints the movements
maps/           the subject maps plus custom ones (see maps/README.md)
```

`maps/custom/` holds extra maps written for this project: valid ones
that exercise edge cases (`ok_*.txt`) and invalid ones that must be
refused with a clear message (`err_*.txt`). They are documented in
`maps/custom/README.md`.

## Resources

Documentation and articles used:

- [Python `enum`](https://docs.python.org/3/library/enum.html) — the
  zone types, point types and colors are enums.
- [PEP 484 — Type Hints](https://peps.python.org/pep-0484/) and
  [PEP 257 — Docstring Conventions](https://peps.python.org/pep-0257/)
- [mypy documentation](https://mypy.readthedocs.io/) — strict mode and
  handling a dependency without type stubs.
- [flake8 documentation](https://flake8.pycqa.org/)
- [`parse` library](https://pypi.org/project/parse/) — the only runtime
  dependency, used to read the zone and connection lines.
- [ANSI escape codes](https://en.wikipedia.org/wiki/ANSI_escape_code) —
  the 24-bit color sequences used for the terminal output.
- [Breadth-first search](https://en.wikipedia.org/wiki/Breadth-first_search)
  and [depth-first search](https://en.wikipedia.org/wiki/Depth-first_search)
  — reachability check and path enumeration, both written by hand since
  graph libraries are forbidden.
- [Maximum flow / disjoint paths](https://en.wikipedia.org/wiki/Maximum_flow_problem)
  — background reading on distributing a fleet over several routes,
  which inspired the slot-booking rule of the scheduler.

### Use of AI

AI (Claude Code) was used as an assistant, on clearly delimited tasks,
and every suggestion was reviewed, tested and reworked before being
kept:

- **Reading the subject back to me.** Checking my implementation
  against each requirement of the PDF, in particular the parser
  constraints and the turn mechanics.
- **Reviewing the engine and the scheduler.** The turn ordering and the
  deadlock-free rule were discussed with it; the first version it
  produced had two real bugs I would not have caught alone: a drone
  landing from a flight could move again during the same turn, and a
  drone landing freed its connection one turn too early, which let a
  second drone cross a connection of capacity 1.
- **Writing an independent output checker.** A throwaway script,
  deliberately not part of the project, that replays the program's
  output and verifies every rule (connections, zone and connection
  capacities, blocked zones, one move per drone per turn, every drone
  delivered). That is what found the two bugs above.
- **Cleaning up.** Finding the code no module called any more, the
  missing escape character that made the colors print as raw text, and
  the Makefile rules that still pointed at another project.
- **Rewording.** This README and the commit messages were drafted with
  it and edited by me.

The parser, the data model and the overall design are mine. AI was not
used to produce code I cannot explain: everything in this repository is
code I can walk through and justify.
