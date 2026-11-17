import argparse
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default="ws://127.0.0.1:8181")
    ap.add_argument("--ckpt", default=os.path.join(HERE, "ckpts",
                                                   "seerdan_policy.enc"))
    ap.add_argument("--round", type=int, default=4,
                    help="deals requested when creating the room (default 4 "
                         "for a quick demo; use a large value for a full "
                         "match to A)")
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    logdir = os.path.join(HERE, "logs")
    os.makedirs(logdir, exist_ok=True)
    procs = {}

    def spawn(seat, extra):
        cmd = [sys.executable, "-u", os.path.join(HERE, "run_bot.py"),
               "--seat", str(seat), "--url", args.url,
               "--device", args.device] + extra
        log = open(os.path.join(logdir, "seat%d.log" % seat), "wb")
        p = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT,
                             cwd=HERE)
        procs[seat] = (p, log)
        return p

    def kill_all():
        for p, log in procs.values():
            if p.poll() is None:
                p.kill()
            log.close()

    try:
        print("[demo] starting seat 0 (SeerDan, creates the room) ...")
        spawn(0, ["--agent", args.ckpt, "--round", str(args.round)])

        room = None
        seat0_log = os.path.join(logdir, "seat0.log")
        for _ in range(40):
            time.sleep(0.5)
            if os.path.exists(seat0_log):
                with open(seat0_log, "r", errors="replace") as f:
                    m = re.search(r"ROOM_ID=(\d+)", f.read())
                if m:
                    room = m.group(1)
                    break
            if procs[0][0].poll() is not None:
                break
        if room is None:
            print("[demo] could not create a room. Is the OpenGuanDan server "
                  "running at %s ?" % args.url)
            print("[demo] see logs/seat0.log for details.")
            kill_all()
            return 1
        print("[demo] room %s created; joining seats 1-3 ..." % room)

        spawn(1, ["--room-id", room, "--agent", "rule"])
        time.sleep(1.0)
        spawn(2, ["--room-id", room, "--agent", args.ckpt])
        time.sleep(1.0)
        spawn(3, ["--room-id", room, "--agent", "rule"])

        print("[demo] match running (room %s). Ctrl-C to stop." % room)
        while True:
            alive = [s for s, (p, _) in procs.items() if p.poll() is None]
            if not alive:
                break
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[demo] interrupted.")
    finally:
        kill_all()

    print("[demo] done. Logs: %s" % logdir)
    for seat in sorted(procs):
        path = os.path.join(logdir, "seat%d.log" % seat)
        print("--- seat %d (%s) ---" % (seat, path))
        with open(path, "r", errors="replace") as f:
            tail = f.readlines()[-6:]
        print("".join(tail).rstrip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
