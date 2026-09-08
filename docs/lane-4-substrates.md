# lane-4-substrates — final report (extracted 2026-09-07T14:18:27Z)

> Development archive, not current setup guidance. Personal filesystem examples
> were generalized on 2026-09-08; original observations and subsequent corrections
> remain in the development history. See the [documentation index](README.md).


## Substrate assessment: message store + presence for a local multi-vendor agent DM

Machine checked: macOS 25.2 (arm64, APFS), Python 3.14.6 (brew), Node v26.0.0, `/usr/bin/sqlite3` (stock), tmux 3.7b, `claude` 2.1.263, `codex-cli` 0.153.4, `gemini` 0.52.0 — all three accept stdio MCP servers (`claude mcp add`, `codex mcp add`, `gemini mcp add --transport stdio` default), so the seam premise holds. Not installed: nats-server, mosquitto, zeromq, fswatch, notmuch, mu, mutt/neomutt. Installed but not stock: redis-server, watchman (15 MB, 9 deps), brew `flock` CLI.

### 1. Rubric table

| Substrate | S1 zero-install | S2 atomic lock-free append | S3 fail-closed presence | S4 cat/tail-able | S5 pull-friendly | S6 per-project | S7 nothing to keep alive | S8 mac=linux |
|---|---|---|---|---|---|---|---|---|
| **Maildir** | 1 (py stdlib; Node needs ~20 lines of `fs`) | 1 | 0 (needs a sibling primitive) | 1 | 1 | 1 | 1 | 1 (colon OK on APFS, verified) |
| **SQLite WAL** | 1 (py stdlib, `node:sqlite` RC) | partial (atomic, but one writer at a time + busy timeout) | 0 | 0 (binary; needs `sqlite3` CLI; no `tail -f`) | 1 (best query ergonomics) | 1 | 1 (but -wal/-shm sidecars) | 1 (same host only) |
| **JSON dir + JSONL** | 1 | partial (per-file rename OK; JSONL `O_APPEND` interleaving UNVERIFIED for large writes) | 0 | 1 | partial (must invent read markers) | 1 | 1 | 1 |
| **UDS broker/daemon** | 1 (stdlib sockets) | 1 (daemon serializes) | partial (fail-closed only while daemon lives) | inherits its store | 1 | partial (104-byte `sun_path`, verified) | 0 | partial (104 vs 108 bytes; no abstract namespace on mac) |
| **NATS + JetStream** | 0 (brew, ~6 MB) | 1 | partial (`$SYS` CONNECT/DISCONNECT needs system-account config; no LWT) | 0 | 1 | partial | 0 | 1 |
| **Mosquitto MQTT** | 0 (brew, 3 deps) | 1 | 1 (LWT + retained is literally presence) | 0 (`mosquitto_sub` to tail) | partial (offline queue via persistent session; no re-read of history) | partial (topic prefix) | 0 | 1 |
| **ZeroMQ** | 0 (native binding) | n/a | 0 | 0 | 0 (no persistence; absent peer = lost message) | partial | 1 | 1 |
| **Redis Streams** | partial (daemon here but not stock; no stdlib client) | 1 (XADD) | 1 (`CLIENT LIST` connection-based, while daemon lives) | partial (`redis-cli`) | 1 (consumer groups) | partial (key prefix, one global daemon) | 0 | 1 |
| **tmux** | partial (brew on mac) | 0 (send-keys is PUSH into the transcript) | 1 for in-tmux sessions, 0 otherwise | n/a | 0 | partial (`-L` per project) | partial | 1 |
| **FS watch** (add-on, not a store) | py: kqueue mac-only; Node `fs.watch` both | n/a | n/a | n/a | n/a | n/a | n/a | partial |

### 2. Per-substrate assessment

**1. Maildir.** Confirmed: `mailbox.Maildir` is in the Python stdlib (3.14.6 here), and the docs say outright "This design allows Maildir mailboxes to be accessed and modified by multiple unrelated programs without data corruption, so file locking is unnecessary" and "Maildir mailboxes do not support (or require) locking" ([docs.python.org/3/library/mailbox.html](https://docs.python.org/3/library/mailbox.html)). I read the stdlib writer: `_create_tmp` names files `time.MusecPpidQcount.hostname`, `add()` writes to `tmp/`, fsyncs, then `os.link` → `os.rename` fallback into `new/` — the spec's algorithm. Dovecot's operational doc agrees for the delivery side: "delivering mails to `new/` directory doesn't have any problems" and needs no locking ([doc.dovecot.org maildir](https://doc.dovecot.org/main/core/config/mailbox_formats/maildir.html)); Courier: "Maildirs do not require locking" ([courier-mta.org/maildir.html](https://www.courier-mta.org/maildir.html)); algorithm summary at [Wikipedia Maildir](https://en.wikipedia.org/wiki/Maildir) (cr.yp.to timed out twice from here). The body can be RFC 5322 with custom headers; `/` is legal `atext`, so `From: claude-code/darker-22@agentdm` parses as a real addr-spec and `Message-ID`/`In-Reply-To`/`References` give threading for free in any mail reader. Two stdlib caveats: the docs warn name clashes are possible across *threads* of one process (PID-keyed names; across processes PIDs differ, so N MCP servers are fine), and `__setitem__` (the "mark read" path) is a copy+discard+rename, not an in-place rename — do mark-read yourself with one `os.rename(new/X, cur/X:2,S)`. Node has no maintained library (npm `maildir` 0.5.0, last modified 2022), but the writer is ~20 lines of `fs.writeFileSync`/`fsyncSync`/`renameSync`. Human readers: `cat`, `ls new/`, `mutt -f <dir>`, `notmuch`, `mu` — none installed here; all in brew (neomutt/notmuch/mu formulae exist; mutt-reads-Maildir-by-path is standard behavior but UNVERIFIED on this box).

**2. SQLite WAL.** Zero-install on both runtimes: Python `sqlite3` (lib 3.53.3), Node `node:sqlite` `DatabaseSync` (added v22.5.0, unflagged v22.13.0, "Stability: 1.2 Release candidate" since v25.7.0 — [nodejs.org/api/sqlite.html](https://nodejs.org/api/sqlite.html)), plus stock `/usr/bin/sqlite3`. Concurrency: "writers and readers can run at the same time... since there is only one WAL file, there can only be one writer at a time" ([sqlite.org/wal.html](https://www.sqlite.org/wal.html)) — so S2 is atomic but not lock-free; you must set a busy timeout (Python default 5.0 s per [sqlite3 docs](https://docs.python.org/3/library/sqlite3.html); Node `timeout` option defaults to 0, so set it). Same-host is required ("WAL does not work over a network filesystem"), which is fine here but means a repo in iCloud Drive/Dropbox is a trap. Presence has no kernel-backed primitive: a `presence` table needs heartbeats and a sweeper, and crash recovery briefly takes an exclusive lock. At rest it is binary — no `cat`, no `tail -f`; "tail" is a polling `SELECT ... WHERE rowid > ?`. Its real strength is S5: "unread for me" and cross-recipient queries are one indexed statement.

**3. Plain JSON dir + JSONL.** Per-message JSON files written tmp→rename are Maildir with the conventions filed off: you re-derive unique naming, the `new/`→`cur/` read transition, flag encoding, and the reader algorithm, and you lose every existing reader (mutt/notmuch/mu/`formail`) and threading headers. A JSONL log for the human is worse than it looks: `O_APPEND` writes from N processes on a local FS are atomic only below a size threshold that POSIX does not guarantee (UNVERIFIED for large messages), and "mark read" against an append-only log needs per-reader cursor files — a second, bespoke consistency scheme. What it gains: `jq`-native bodies — which a Maildir message carries just as well as `Content-Type: application/json`.

**4. Unix domain socket broker / tiny daemon.** Both stdlibs have sockets, and a daemon can serialize writes and track connected clients (fail-closed *while it lives*). Costs, all verified locally: the socket file persists after the listener is SIGKILLed (readers see `ECONNREFUSED` and must unlink+rebind, a two-starter race), and macOS `sun_path` is 104 bytes (`/usr/include/sys/un.h`) — my 121-char scratchpad path failed with `AF_UNIX path too long`, so a per-project socket under a deep git root does not bind; Linux is 108 and has an abstract namespace macOS lacks. "Who starts it" has no good answer: the first MCP server to bind becomes broker and takes everyone's liveness with it when its CLI exits. For a PULL model the daemon buys nothing the filesystem doesn't already provide; it only buys fan-out/notify, which a human `ls new/` poll covers.

**5. Local brokers.** *NATS*: single 6 MB binary via brew ([docs.nats.io intro](https://docs.nats.io/running-a-nats-service/introduction); release asset sizes via `gh release view nats-io/nats-server`), JetStream needs `-js`; presence exists as `$SYS.ACCOUNT.<acct>.CONNECT/DISCONNECT` but "System events are published into the system account... you connect as a system user" — not available on a bare run ([sys_accounts](https://docs.nats.io/running-a-nats-service/configuration/sys_accounts)); no LWT. *Mosquitto/MQTT*: LWT is the one substrate whose presence is first-class — "The Will Message MUST be published after the Network Connection is subsequently closed and either the Will Delay Interval has elapsed or the Session ends", triggered on keep-alive expiry at 1.5× ([MQTT v5 spec](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html) §3.1.2.5, §3.1.2.10); retained messages are the "last known good" ([mosquitto mqtt(7)](https://mosquitto.org/man/mqtt-7.html)). But it is a daemon with 3 brew deps, its store is opaque, and "read" is an implicit QoS ack — an agent cannot re-read yesterday's thread. *ZeroMQ*: brokerless, but no persistence and a native binding (pyzmq / zeromq.js) — a message to a peer that is not currently receiving is lost, which kills S5. *Redis Streams*: `XADD`/`XREAD BLOCK`/consumer groups map perfectly to inbox semantics ([redis.io streams](https://redis.io/docs/latest/develop/data-types/streams/)) and `CLIENT LIST` is fail-closed presence, but it is one global daemon, the client libraries are not stdlib in either runtime, and redis-server is installed here only by accident. None of these is small enough to be *the* dependency of a per-project dev tool.

**6. tmux.** Claude Squad uses "tmux to create isolated terminal sessions for each agent" and worktrees per branch ([github.com/smtg-ai/claude-squad](https://github.com/smtg-ai/claude-squad)), and tmux exposes real presence (`#{pane_pid}`, `#{pane_dead}`; `man tmux`). But its only transport, `send-keys`, injects text into the pane — that is PUSH into the transcript, the exact thing the requirement forbids; `wait-for` is a client-side barrier ("prevents the client from exiting until woken using wait-for -S"), not a queue; and presence covers only sessions that happen to be inside tmux (a VS Code terminal or iTerm tab is invisible). Acceptable as optional enrichment (store `tmux_pane` in the presence record so a human can jump to it), never as the substrate.

**7. Filesystem watch.** Python stdlib: `select.kqueue` present on macOS, no inotify on Linux (verified) — the portable stdlib watcher is polling `os.listdir(new/)`, which is cheap because `new/` is nearly always empty. Node `fs.watch` is FSEvents on macOS and inotify on Linux, recursive is unsupported on Linux, "filename argument may be null, and events may be reported twice" ([nodejs.org/api/fs.html](https://nodejs.org/api/fs.html)) — fine for a non-recursive watch on `new/`. `fswatch` is not installed; `watchman` is (15 MB, 9 deps) — far too heavy to require. Cost/benefit: a 1-second poll in the human CLI costs nothing and removes the whole dependency question.

**8. Presence.** (a) *heartbeat + pid + `kill -0`*: never fail-closed — a dead process reads "online" until a sweeper ages it out; pid reuse and `EPERM` ambiguity on top. (b) *flock held for the process lifetime*: verified live on APFS in the scratchpad — holder SIGKILLed → a non-blocking `LOCK_EX|LOCK_NB` succeeds immediately (offline); Linux semantics identical ("released... when all such file descriptors have been closed", [man7 flock(2)](https://man7.org/linux/man-pages/man2/flock.2.html)). Two traps, both verified: an fd passed to a child keeps the lock alive after the parent dies (`pass_fds` run: still HELD until the grandchild died) — mitigated because Python fds are non-inheritable by default (printed `False`) and libuv sets CLOEXEC; and Node has no `flock` in stdlib (`fs-ext` native addon, or brew `flock` — not stock macOS, `/usr/bin/flock` absent). Use `flock`, not `fcntl` byte-range locks: macOS `fcntl(2)` states "flock(2) and fcntl locks may be safely used concurrently" (they do not interact) and fcntl's any-close-releases rule is the classic footgun; macOS additionally offers `O_EXLOCK` on `open(2)` (atomic open+lock, BSD-only). (c) *MQTT LWT*: semantically ideal, 1.5×keepalive latency, requires the broker. (d) *daemon tracking pids*: inherits the daemon's liveness problem. Node-stdlib alternative to flock with the same fail-closed property: hold a Unix socket listener; verified `connect()` → `ECONNREFUSED` immediately after SIGKILL — with the 104-byte path trap, so sockets must live under a short directory, not the git root.

### 3. Recommendation

**Store: Maildir, one per recipient identity, RFC 5322 bodies. Presence: a `flock` held on a per-agent file for the MCP server's lifetime.** Maildir is the only option scoring 1 on S1, S2, S4, S5, S6, S7, S8 with a 25-year production record, stdlib in Python, and ~20 lines in Node; flock is the only zero-install presence primitive that the kernel fails closed for you.

**Strongest argument against:** the presence half is a *second* mechanism bolted beside the store, and it constrains the implementation language — `flock` is stdlib only in Python, so a Node MCP server must either add a native addon or switch to the Unix-socket-listener variant (with its path-length trap). MQTT is the one substrate where store and presence are one coherent thing; you are trading that coherence for zero-install and `cat`-ability.

### 4. On-disk layout and presence primitive

Root: `$(git rev-parse --git-common-dir)/agentdm/` — inside `.git/`, so it is never committed, is shared by every worktree by construction (verified: this repo's `darker-selfbuild` worktree resolves to the same common dir, which matters because Claude Squad-style setups put each agent in its own worktree), and vanishes with the repo. Claude Code's sandbox allows Bash writes to the linked worktree's shared `.git` except `hooks/` and `config` ([code.claude.com sandboxing](https://code.claude.com/docs/en/sandboxing)), and the MCP server itself runs outside the sandbox ("a hook or MCP server that Claude Code runs outside the sandbox"). Fallback if any CLI's sandbox turns out to block `.git` writes: `~/.local/state/agentdm/<sha256(realpath common-dir)[:12]>/` with a `project` pointer file.

```
.git/agentdm/
  presence/
    claude-code.darker-22          # flock'd; body = JSON {pid, family, session, worktree, started_at, tmux_pane?}
    codex.darker-a1
  human/{tmp,new,cur}/             # the developer's inbox
  claude-code.darker-22/{tmp,new,cur}/
  codex.darker-a1/{tmp,new,cur}/
```

Message (plain RFC 5322; never fold headers so a 10-line parser works in Node):

```
Message-ID: <1757260000.M412P33538Q1.host@agentdm>
Date: Mon, 07 Sep 2026 09:12:00 -0500
From: claude-code/darker-22@agentdm
To: codex/darker-a1@agentdm
Subject: heads-up: I am editing scripts/wo-lifecycle.sh
In-Reply-To: <...>
X-Agent-Family: claude-code
X-Git-Root: /work/example-project
X-Worktree: /work/example-project-feature
X-Agentdm-Kind: notice
Content-Type: text/plain; charset=utf-8

body...
```

Primitives:
- **send**: write `tmp/<time.MusecPpidQn.host>`, fsync, `rename` (or `link`+unlink) into `<recipient>/new/`. Broadcast = `os.link` the same file into every online recipient's `new/` (the spec's own trick; one inode).
- **fetch unread for me**: `listdir(<me>/new/)`; **mark read**: `rename(new/X, cur/X:2,S)`; **reply**: set `In-Reply-To`.
- **presence (exact)**: at MCP server start, `fd = open("presence/<agent-id>", O_RDWR|O_CREAT)` with the fd non-inheritable (Python default; verified), then `flock(fd, LOCK_EX|LOCK_NB)`; on `EWOULDBLOCK` the id is already live → pick another id (uniqueness for free). Write the JSON record, keep `fd` open until exit, never call `LOCK_UN`. Readers: open the same path, try `LOCK_EX|LOCK_NB`; success = offline (release immediately; the JSON is "last seen"), `EWOULDBLOCK` = online. No sweeper, no cleanup pass. Node variant: `net.createServer().listen("/tmp/agentdm-<hash8>/<agent-id>.sock")` (short path); readers `connect()` — `ECONNREFUSED` = offline.
- **human tail**: `agentdm inbox` polls `human/new/` every 1 s; optional `mutt -f .git/agentdm/human` / `notmuch` / `mu`.

### 5. UNVERIFIED

- Codex CLI: whether `workspace-write` protects `.git/` inside cwd, and whether MCP servers run outside its sandbox (`codex --sandbox` modes verified locally: read-only/workspace-write/danger-full-access, described as applying to "model-generated shell commands"; docs redirect chain ended in a 404). Same question for Gemini CLI's sandbox.
- `mutt -f` / `notmuch` / `mu` rendering of the custom `From:` addr-spec (none installed).
- SQLite per-session `locking_mode=EXCLUSIVE` side-file as a fail-closed presence trick.
- Mosquitto binary size; NATS JetStream `store_dir` details.
- `O_APPEND` interleaving threshold for a shared JSONL from N writers.
- flock behavior on NFS/iCloud/Dropbox-synced repos (assume broken).
- Maildir on Windows (colon in filenames) — out of scope; Python's `colon='!'` exists for it.

Probe scripts (scratchpad only, no side effects): `flock_probe.py`, `uds_probe.py` under `<local-scratch-directory>`.
