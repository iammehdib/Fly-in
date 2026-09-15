# Custom maps

Extra maps written to exercise edge cases of the parser and of the
simulation engine. Files whose name starts with `err_` are **invalid**
on purpose and must make the program stop with a clear error message
(line number and cause).

| File | What it checks |
| --- | --- |
| `ok_restricted_end.txt` | The end hub itself is a restricted zone (2-turn transit at the very end). |
| `ok_blocked_shortcut.txt` | A blocked zone sits on the shortest path and must be avoided. |
| `ok_wide_links.txt` | Big capacities everywhere: many drones move on the same turn. |
| `ok_many_drones.txt` | 200 drones on a tiny map (throughput and scalability). |
| `ok_metadata_order.txt` | Metadata tags in any order, `max_drones` ignored on start/end, unknown color. |
| `err_no_drones.txt` | First line is not `nb_drones:`. |
| `err_zero_drones.txt` | `nb_drones: 0` is not a positive integer. |
| `err_two_starts.txt` | Two `start_hub:` lines. |
| `err_no_end.txt` | Missing `end_hub:`. |
| `err_dup_name.txt` | Two zones with the same name. |
| `err_dup_connection.txt` | `a-b` then `b-a`. |
| `err_unknown_zone.txt` | Connection toward a zone that is not defined. |
| `err_bad_zone_type.txt` | `zone=lava`. |
| `err_bad_capacity.txt` | `max_link_capacity=0`. |
| `err_bad_metadata.txt` | `[colour red]` (syntactically invalid metadata). |
| `err_unreachable.txt` | The end hub is only reachable through a blocked zone. |
