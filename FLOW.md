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
   └─ pick next preferred server in rotation (MONITOR_SERVER_IDS)
        │
        ▼
 run_test_for_server(preferred_id)
        │
        ├─► is_throttle_blocked()?  ◄── reads var/throttle_block
        │       │
        │     YES └──► write_log(throttle block)
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
        │                return False ──────────────────────────────┤
        │       NO                                                   │
        ├─► stdout empty?                                            │
        │       YES └──► write_log + send_email(stderr)             │
        │                return False ──────────────────────────────┤
        │       NO                                                   │
        ▼                                                           │
 parse_speedtest_json(stdout)                                       │
        │                                                           │
        ▼                                                           │
 build_influx_payload()                                            │
        │                                                           │
        ▼                                                           │
 create_influx_client().write_points(payload)                      │
        │                                                           │
        ▼                                                           │
 write_log(result line)                                            │
        │                                                           │
        ▼                                                           │
   return True                          return False ◄─────────────┘
        │                                   │
        ▼                                   ▼
 record_server_used()            try each fallback server
   ├─ write var/last_server_id    └─ run_test_for_server(fallback_id)
   ├─ read var/known_servers             (same flow as above)
   └─ if new server:                      │
       write_log + send_email     ┌───────┴────────┐
                                 any           all fail
                                succeed            │
                                  │          write_log + send_email
                                  ▼
                        record_server_used(preferred_id)
        │
        ▼
 write_log(--END--)
```
