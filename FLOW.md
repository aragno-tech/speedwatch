# Speedwatch Flow — no-args invocation

```
python3 speedwatch.py
        │
        ▼
 write_log(--START--)
        │
        ▼
 get_server_candidates()
   ├─ speedtest -L  ──────────────────► list of {id, name} servers
   ├─ read var/last_server_id
   └─ if MONITOR_SERVER_IDS set:
       └─ rotate through those IDs; fallbacks = remaining -L servers
      else:
       └─ preferred = first SERVER_COUNT servers from -L; fallbacks = rest
        │
        ▼
 run_test_for_server(preferred_id)
        │
        ├─► is_throttle_blocked()?  ◄── reads var/throttle_block
        │       │
        │     YES └──► write_log(throttle block)
        │               write_server_log(SKIP reason=throttle_block)
        │                   │
        │                   ▼
        │               return False ──────────────────────────────┐
        │                                                           │
        │      NO                                                   │
        │       │                                                   │
        ▼       ▼                                                   │
   run_speedtest(server_id)                                         │
   └─ /usr/bin/speedtest -f json -s <id>                           │
      returns (stdout, stderr)                                      │
        │                                                           │
        ├─► "Limit reached" in stderr/stdout?                       │
        │       YES └──► set_throttle_block()                       │
        │                write_log + send_email                     │
        │                write_server_log(SKIP reason=rate_limit)   │
        │                return False ──────────────────────────────┤
        │       NO                                                   │
        ├─► stdout empty?                                            │
        │       YES └──► write_log + send_email(stderr)             │
        │                write_server_log(SKIP reason=no_output)    │
        │                return False ──────────────────────────────┤
        │       NO                                                   │
        ▼                                                           │
 parse_speedtest_json(stdout)                                       │
        │                                                           │
        ▼                                                           │
 write_result(tags, fields)                                        │
   ├─ STORAGE=influxdb → create_influx_client().write_points()     │
   ├─ STORAGE=sqlite   → storage_sqlite.write_record()             │
   └─ STORAGE=both     → both of the above                         │
        │                                                           │
        ▼                                                           │
 write_log(result line)                                            │
        │                                                           │
        ▼                                                           │
   return True                          return False ◄─────────────┘
        │                                   │
        ▼                                   ▼
 record_server_used()            is_throttle_blocked()?
   ├─ write var/last_server_id     │
   ├─ read var/known_servers      YES └──► write_server_log(SKIP fallbacks)
   └─ if new server:               │           no fallbacks attempted
       write_log + send_email      │
                                   NO
                                   │
                                   └─► try each fallback server
                                         write_server_log(FALLBACK preferred→fallback)
                                         run_test_for_server(fallback_id)
                                               (same flow as above)
                                               │
                                      ┌────────┴────────┐
                                    any             all fail
                                   succeed               │
                                      │           write_log + send_email
                                      ▼
                            record_server_used(preferred_id)
        │
        ▼
 write_log(--END--)
```
