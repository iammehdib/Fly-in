*This project has been created as part of the 42 curriculum by mbuchet.*

# Fly-in

## Description

Fly-in is a drone routing simulator. Given a network of zones (a graph
described in a text file), it moves a fleet of drones from a **start hub** to
an **end hub** in as few simulation turns as possible while respecting:

- zone capacities (`max_drones`, default 1; unlimited on the start and end hubs),
- connection capacities (`max_link_capacity`, default 1),
- zone types: `normal` (1 turn), `priority` (1 turn, preferred), `restricted`
  (2 turns, the drone flies on the connection for one turn and **must** land
  on the next one), `blocked` (never entered),
- the turn mechanics of the subject (drones leaving a zone free its capacity
  during the same turn, drones move simultaneously).

The program is made of four independent parts, all written in plain Python
(no graph library) and fully typed:

| Module | Role |
| --- | --- |
| `parsing.py` | Reads and validates the map file with `parse` patterns, builds the `Map`. |
| `models.py`, `map.py` | Domain objects: `Point` (zone), `Connection`, `Transit`, `Drone`, `Map`. |
| `scheduler.py` | Pathfinding + turn scheduling (`PathPlanner`, `Reservations`, `Solver`). |
| `simulation.py` | Turn-by-turn engine that replays the schedule and **re-validates every rule**. |
| `display.py` | Plain output (subject format) and colored terminal visualisation. |
| `main.py` | Command line interface. |

Results on the maps provided with the subject (all of them are at or below the
reference target):

| Map | Drones | Target | Fly-in |
| --- | ---: | ---: | ---: |
| easy/01_linear_path | 2 | ≤ 6 | **4** |
| easy/02_simple_fork | 4 | ≤ 8 | **4** |
| easy/03_basic_capacity | 4 | ≤ 6 | **4** |
| medium/01_dead_end_trap | 5 | ≤ 12 | **8** |
| medium/02_circular_loop | 6 | ≤ 15 | **15** |
| medium/03_priority_puzzle | 5 | ≤ 12 | **7** |
| hard/01_maze_nightmare | 8 | ≤ 30 | **13** |
| hard/02_capacity_hell | 12 | ≤ 35 | **16** |
| hard/03_ultimate_challenge | 15 | ≤ 45 | **26** |
| challenger/01_the_impossible_dream | 25 | record 45 | **43** |

## Instructions

### Requirements

Python 3.10 or later and the [`parse`](https://pypi.org/project/parse/)
library (the reverse of `str.format`, used by the map parser; it is not a
graph library). `flake8`, `mypy` and `pytest` are development tools.

### Installation

```bash
make install          # creates .venv and installs parse, flake8, mypy and pytest
```

### Running

```bash
python main.py maps/medium/03_priority_puzzle.txt            # official output only
python main.py maps/medium/03_priority_puzzle.txt --visual   # colored zones + summary
python main.py maps/hard/03_ultimate_challenge.txt -d 0.4    # animated (clears the screen between turns)
make run MAP=maps/easy/01_linear_path.txt ARGS=--visual
make debug MAP=maps/easy/01_linear_path.txt                   # same, inside pdb
```

Options:

| Option | Meaning |
| --- | --- |
| `-v`, `--visual` | Show the colored state of the zones at every turn and the summary metrics. |
| `-d`, `--delay SECONDS` | Animate the visual output (implies `--visual`). |
| `--no-color` | Disable ANSI colors. |

Any parsing error stops the program with exit code 1 and a message such as
`Error: line 3: invalid zone type 'lava' (normal, blocked, restricted, priority) -> 'hub: mid 1 0 [zone=lava]'`.

### Quality checks

```bash
make lint             # flake8 + mypy (flags required by the subject)
make lint-strict      # flake8 + mypy --strict
make test             # pytest: parser, solver targets, engine rules
make clean            # remove caches
```

### Map format

```
nb_drones: 5
start_hub: hub 0 0 [color=green]
end_hub: goal 10 10 [color=yellow]
hub: roof1 3 4 [zone=restricted color=red]
hub: corridorA 4 3 [zone=priority color=green max_drones=2]
hub: obstacleX 5 5 [zone=blocked color=gray]
connection: hub-roof1
connection: corridorA-tunnelB [max_link_capacity=2]
```

The parser enforces every constraint of the subject: `nb_drones` first and
positive, exactly one start and one end hub, unique names without dashes,
integer coordinates, connections only between previously defined zones, no
duplicated connection (`a-b` and `b-a` are the same), valid metadata (`zone`,
`color`, `max_drones` for zones, `max_link_capacity` for connections),
positive capacities. `max_drones` is ignored on the start and end hubs. Extra
edge-case maps (valid and invalid) live in `maps/custom/`.

## Example

Input `maps/medium/03_priority_puzzle.txt`:

```
nb_drones: 5

start_hub: start 0 0 [color=green]
hub: slow_path1 1 -1 [zone=restricted color=red]
hub: slow_path2 2 -1 [color=red]
hub: fast_junction 1 0 [zone=priority color=blue max_drones=2]
hub: fast_path 2 0 [zone=priority color=blue]
hub: merge_point 3 0 [color=yellow max_drones=3]
end_hub: goal 4 0 [color=green]

connection: start-slow_path1
connection: start-fast_junction
connection: slow_path1-slow_path2
connection: slow_path2-merge_point
connection: fast_junction-fast_path
connection: fast_path-merge_point
connection: merge_point-goal [max_link_capacity=2]
```

Output of `python main.py maps/medium/03_priority_puzzle.txt` (7 turns, one
line per turn, `D<ID>-<zone>` or `D<ID>-<connection>` while flying toward a
restricted zone; drones that wait are omitted):

```
D1-fast_junction D2-start-slow_path1
D1-fast_path D2-slow_path1 D3-fast_junction
D1-merge_point D2-slow_path2 D3-fast_path D4-fast_junction
D1-goal D2-merge_point D3-merge_point D4-fast_path D5-fast_junction
D2-goal D3-goal D4-merge_point D5-fast_path
D4-goal D5-merge_point
D5-goal
```

Four drones take the priority path (`fast_junction` → `fast_path`, throughput
of one drone per turn) while `D2` takes the slower restricted path in
parallel, so no drone waits uselessly: the last drone arrives at turn 7.

## Algorithm and implementation strategy

### Model of a turn

A schedule is, for every drone, the list of its positions at the end of each
turn (`plan[0]` is the start hub). A position is either a zone (`Point`) or a
`Transit` (the drone is on a connection, on its way to a restricted zone).
Two rules of the subject are encoded directly in that representation:

- a drone occupying zone *Z* at turn *t* counts toward the capacity of *Z* at
  turn *t* only — a drone that leaves frees the capacity for the same turn;
- a two-turn move toward a restricted zone books the connection at turns *t*
  and *t+1* and the destination at *t+1*: the drone cannot wait on the link.

### Prioritized planning on a time-expanded graph

The fleet is scheduled with **prioritized planning** (also known as
cooperative pathfinding): drones are planned one after the other and every
drone books the zones and connections it uses, per turn, in a `Reservations`
table (two dictionaries `(zone, turn) → count` and `(link, turn) → count`).

Each drone runs a **Dijkstra on the time-expanded graph** whose states are
`(zone, turn)`. From `(zone, t)` it can:

- wait: `(zone, t+1)` if the zone still has room at `t+1` (always true in the
  start hub),
- move to a normal/priority neighbour: `(n, t+1)` if the link has room at
  `t+1` and `n` has room at `t+1`,
- move to a restricted neighbour: `(n, t+2)` if the link has room at `t+1`
  **and** `t+2`, and `n` has room at `t+2`.

The cost is the tuple `(arrival turn, turns spent inside hubs, moves into
non-priority zones)` compared lexicographically. The first component gives
the earliest arrival; the second prefers waiting in the (unlimited) start hub
rather than blocking a hub for other drones; the third makes drones prefer
`priority` zones when several paths are equally fast, as requested by the
subject. Blocked zones are never expanded, dead ends and loops are harmless
because the search is exhaustive and the "visited" set is per `(zone, turn)`.

Since all drones are identical and every drone takes the earliest arrival
available, the order in which they are planned does not matter and the
result is deterministic. On every provided map the number of turns equals
the theoretical minimum (shortest path + throughput of the bottleneck).

### Simulation engine

`Simulation` replays the schedule turn by turn and does **not** trust the
planner: for every move it checks that the connection exists, that blocked
zones are never entered, that restricted zones are entered through a transit
and left the next turn, that no zone exceeds `max_drones` and no connection
exceeds `max_link_capacity`. A violation raises `SimulationException`. It also
produces the official output and the data needed by the display.

### Complexity and memory

- One drone plan: Dijkstra over at most `V × T` states with `E` edges per
  turn, i.e. `O(V·T·log(V·T) + E·T)` where `T` is the arrival turn.
- Whole fleet (`n` drones): `O(n · V · T · log)`. Because arrival turns grow
  with `n` this is quadratic in `n` in the worst case; for fleets larger than
  64 drones the search window of each drone starts near the arrival turn of
  the previous drone (drones are identical, so arrivals are non-decreasing),
  which makes the total linear in `n`: 1000 drones on the "ultimate
  challenge" map are scheduled in about 10 seconds, 25 drones on the
  challenger in 0.3 s.
- Paths are cached in the sense that each drone's schedule is computed once
  and stored on the `Drone`; the reservation table is the only shared state
  and holds `O(n · T)` entries. Nothing is recomputed during the simulation.

## Visual representation

The mandatory output (`python main.py map.txt`) is kept strictly to the
format of the subject so that it can be piped to a checker. `--visual` adds,
for each turn:

- the turn header (number of moves, drones still flying),
- the move line with every destination painted in the color of its zone
  (`color=` metadata of the map file, e.g. `red`, `blue`, `gold`, `rainbow`;
  unknown names are simply printed without color), transits in orange,
- one line per zone that holds drones, with the zone name in its color and
  a marker for its type (`*` priority, `!` restricted, `X` blocked), the
  drones inside and the occupancy (`D2 D3  (2/3)`); the start hub shows how
  many drones are still waiting and the end hub how many were delivered,
- the drones in flight on a connection toward a restricted zone.

```
Turn 4  (5 moves, 4 drones still flying)
  D1-goal D2-merge_point D3-merge_point D4-fast_path D5-fast_junction
  start          0 waiting
  fast_junction* D5  (1/2)
  fast_path*     D4  (1/1)
  merge_point    D2 D3  (2/3)
  goal           1 delivered
```

With `--delay 0.4` the screen is cleared between turns, which gives an
animation of the drones flowing through the network. At the end a summary
prints the secondary metrics of the subject: total turns, movements per
turn, average turns per drone and total weighted path cost. Colors are
automatically disabled when the output is not a terminal (`--no-color`
forces it).

## Resources

- Subject of the project (42 Belgium, Fly-in v1.6).
- E. W. Dijkstra, *A note on two problems in connexion with graphs* (1959) —
  the shortest path algorithm used per drone.
- D. Silver, *Cooperative Pathfinding* (AIIDE 2005) — prioritized planning
  with a space-time reservation table, the core idea of the scheduler.
- Python documentation: [`heapq`](https://docs.python.org/3/library/heapq.html),
  [`argparse`](https://docs.python.org/3/library/argparse.html),
  [`dataclasses`](https://docs.python.org/3/library/dataclasses.html).
- [`parse` documentation](https://github.com/r1chardj0n3s/parse) — the
  format-string based matcher used by the map parser.
- [ANSI escape codes](https://en.wikipedia.org/wiki/ANSI_escape_code) for the
  colored terminal output.
- [flake8](https://flake8.pycqa.org/), [mypy](https://mypy.readthedocs.io/),
  [pytest](https://docs.pytest.org/) documentation.

### Use of AI

AI (Claude) was used as a pair-programming assistant, always reviewed and
tested by hand:

- extracting the requirements of the subject into a checklist and designing
  the module split (parser / models / scheduler / engine / display);
- writing the first version of the time-expanded Dijkstra and of the
  reservation table, then reviewing the handling of restricted zones
  (2-turn transit, link booked on both turns);
- generating the edge-case maps of `maps/custom/` and the pytest suite;
- writing docstrings and this README, and checking flake8/mypy compliance.

All the algorithmic choices (prioritized planning, lexicographic cost,
departure window) were understood, validated on the provided maps and are
explained above.
