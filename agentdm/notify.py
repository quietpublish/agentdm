"""Optional human notifications: ntfy or Telegram, opted in by the human from the CLI.

Off unless `${XDG_STATE_HOME:-~/.local/state}/agentdm/notify.json` exists. Sends metadata only:
project, sender, recipient, kind, outcome. Never a body, never a reason, and the subject only when the
human explicitly turned that on. Delivery is fire-and-forget on a daemon thread with a short timeout;
a failed or slow push never delays, fails or changes the receipt of the message it describes. This is
the human's pager, not an agent wake path: an agent cannot enable it through the server.
"""
import fcntl, json, os, sys, threading, time, urllib.request
from .store import HUMAN, REQUEST_KINDS, _read_json, _write_json

TIMEOUT_S = 5.0
DEFAULT_CAP_PER_HOUR = 20      # per sender: a looping or spamming peer cannot turn the pager into a drumbeat


def config_path(store):
    return os.path.join(os.path.dirname(store.path), "notify.json")


def load(store):
    return _read_json(config_path(store))


def save(store, config):
    path = config_path(store)
    if config is None:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        return
    _write_json(path, config)
    os.chmod(path, 0o600)


def state_path(store):
    return os.path.join(os.path.dirname(store.path), "notify-state.json")


def admit(store, config, sender, now=None):
    """Sliding one-hour window per sender. Returns True and records the push, or False when the cap
    is reached. The state file is shared by every server on the machine, so it is updated under a lock."""
    cap = config.get("cap_per_hour", DEFAULT_CAP_PER_HOUR)
    now = time.time() if now is None else now
    path = state_path(store)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        raw = os.read(fd, 1 << 20)
        try:
            state = json.loads(raw) if raw else {}
        except ValueError:
            state = {}
        recent = [t for t in state.get(sender, []) if now - t < 3600.0]
        if len(recent) >= cap:
            return False
        recent.append(now)
        state = {k: [t for t in v if now - t < 3600.0] for k, v in state.items() if k != sender}
        state[sender] = recent
        os.lseek(fd, 0, os.SEEK_SET); os.ftruncate(fd, 0)
        os.write(fd, json.dumps(state).encode())
        return True
    finally:
        os.close(fd)


def wants(config, event):
    """Which events reach the human: anything addressed to the human, any request kind, any outcome."""
    if not config:
        return False
    if event["event"] == "outcome":
        return True
    return event["to"] == HUMAN or event["kind"] in REQUEST_KINDS


def render(store, config, event):
    title = "agentdm " + os.path.basename(store.root)
    if event["event"] == "outcome":
        text = f"{event['by']} {event['outcome']} {event['kind']} from {event['to']}"
    else:
        text = f"{event['from']} -> {event['to']}: {event['kind']}"
    if config.get("subject") and event.get("subject"):
        text += " | " + event["subject"]
    return title, text


def requests_for(config, title, text):
    """The HTTP requests one notification expands to. Pure: no I/O."""
    out = []
    ntfy = config.get("ntfy")
    if ntfy and ntfy.get("url"):
        headers = {"Title": title, "Content-Type": "text/plain; charset=utf-8"}
        if ntfy.get("token"):
            headers["Authorization"] = "Bearer " + ntfy["token"]
        out.append(urllib.request.Request(ntfy["url"], data=text.encode(), headers=headers, method="POST"))
    tg = config.get("telegram")
    if tg and tg.get("bot_token") and tg.get("chat_id"):
        url = f"{tg.get('api') or 'https://api.telegram.org'}/bot{tg['bot_token']}/sendMessage"
        body = json.dumps({"chat_id": tg["chat_id"], "text": f"{title}\n{text}"}).encode()
        out.append(urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST"))
    return out


def deliver(requests):
    """Synchronous delivery; returns one (url, status-or-error) per request. Used by `notify test`."""
    results = []
    for req in requests:
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                results.append((req.full_url, resp.status))
        except Exception as exc:
            results.append((req.full_url, f"{type(exc).__name__}: {exc}"))
    return results


def notify(store, event, config=None, sync=False):
    """Push if configured and wanted. Never raises. The long-lived server pushes on a daemon thread so
    a slow endpoint cannot delay a tool response; the short-lived CLI pushes inline (`sync`) because
    its process would otherwise exit before the thread delivers."""
    config = load(store) if config is None else config
    if not wants(config, event):
        return False
    requests = requests_for(config, *render(store, config, event))
    if not requests:
        return False
    sender = event.get("from") or event.get("by") or "?"
    if not admit(store, config, sender):
        sys.stderr.write(f"agentdm: notification from {sender} suppressed: cap reached for this hour\n")
        return False

    def run():
        for url, result in deliver(requests):
            if not isinstance(result, int) or result >= 400:
                sys.stderr.write(f"agentdm: notification to {url} failed: {result}\n")

    if sync:
        run()
    else:
        threading.Thread(target=run, name="agentdm-notify", daemon=True).start()
    return True
