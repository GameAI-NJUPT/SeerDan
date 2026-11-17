import argparse
import asyncio
import json
import queue
import sys
import threading

from .cards import (IDX_RANK_CHAR, flush_potential, is_wildcard, rank_idx,
                    rank_of_char, seq_value, suit_idx)
from .candidate_filter import dedupe_straight_flush_safe
from .combos_adapter import (PASS, PLATE, SFLUSH, STRAIGHT, TUBE, TYPE_NAMES,
                             MoveView)
from .encode import TOTAL_COPIES
from .evaluate import make_agent

PASS_ACT = ["PASS", "PASS", "PASS"]
CARDS_PER_HAND = 27




class WebSocketEnv:









    def __init__(self, user_id, url="ws://localhost:8181", name=None):
        self.user_id = user_id
        self.url = url
        self.name = name or ("SeerDan_%s" % user_id)
        self.room_id = None
        self.seat = None
        self.connected = False
        self.ws = None
        self.msgs = queue.Queue()
        self._ack = threading.Event()
        self._ready = threading.Event()
        self._error = None
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()



        if not self._ready.wait(timeout=15) or not self.connected:
            raise RuntimeError("could not connect to %s: %s"
                               % (url, self._error or "timed out"))

    def _run(self):
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._listen())
        finally:



            pending = asyncio.all_tasks(self.loop)
            for t in pending:
                t.cancel()
            if pending:
                self.loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True))
            self.loop.close()

    async def _listen(self):
        import websockets
        try:
            self.ws = await websockets.connect(self.url)
            self.connected = True
            self._ready.set()
            while self.connected:
                self.msgs.put(json.loads(await self.ws.recv()))
        except Exception as e:
            self._error = repr(e)
            print("[ws] connection ended: %r" % (e,))
        finally:
            self.connected = False
            self._ready.set()
            self.msgs.put(None)

    def _send(self, payload):
        fut = asyncio.run_coroutine_threadsafe(
            self.ws.send(json.dumps(payload)), self.loop)
        fut.result(timeout=10)


    def _await_ack(self, want):





        held = []
        while True:
            m = self.msgs.get(timeout=15)
            if m is None:
                raise RuntimeError("connection lost while joining")
            if m.get("type") == want:
                for h in held:
                    self.msgs.put(h)
                if m.get("code", 200) != 200:
                    raise RuntimeError("%s rejected: %r" % (want, m))
                self.room_id = m["data"].get("roomId", self.room_id)
                self.seat = m["data"]["userNum"]
                return self.seat
            held.append(m)

    def create_room(self, rounds=600):
        self._send({"type": "CREATE_ROOM",
                    "data": {"userId": self.user_id, "userName": self.name,
                             "round": rounds}})
        return self._await_ack("CREATE_ROOM")

    def join_room(self, room_id):
        self.room_id = room_id
        self._send({"type": "JOIN_ROOM",
                    "data": {"userId": self.user_id, "userName": self.name,
                             "roomId": room_id}})
        return self._await_ack("JOIN_ROOM")


    def send_play(self, act):
        self._send({"type": "PLAY",
                    "data": {"roomId": self.room_id, "player": self.seat,
                             "act": act}})

    def send_tribute(self, act):
        self._send({"type": "TRIBUTE",
                    "data": {"roomId": self.room_id, "player": self.seat,
                             "act": act}})

    def send_paytribute(self, tribute_pos, tribute, act):
        self._send({"type": "PAYTRIBUTE",
                    "data": {"roomId": self.room_id, "player": self.seat,
                             "tributePos": tribute_pos, "tribute": tribute,
                             "act": act}})

    def next_message(self, timeout=None):
        return self.msgs.get(timeout=timeout)

    def close(self):
        self.connected = False
        if self.ws is not None:
            try:
                asyncio.run_coroutine_threadsafe(
                    self.ws.close(), self.loop).result(timeout=5)
            except Exception:
                pass
        self._thread.join(timeout=5)




class MatchState:









    def __init__(self, seat):
        self.seat = seat
        self.level_char = "2"
        self.deal_idx = -1
        self.prev_double_down = 0
        self.events = []
        self.anti = False
        self.tribute_ranks = [0] * 15
        self.played = [0] * 4
        self.net_tribute = [0] * 4


    def on_notify(self, m):
        stage = m.get("stage")
        if stage == "beginning":
            self.deal_idx += 1
            self.level_char = m["levelCard"]
            self.events = []
            self.anti = False
            self.tribute_ranks = [0] * 15
            self.played = [0] * 4
            self.net_tribute = [0] * 4
        elif stage == "play":
            self._on_play(m)
        elif stage in ("tribute", "back"):
            self._on_exchange(stage, m)
        elif stage == "anti-tribute":
            self.anti = True
            self.events.append(('anti',))
        elif stage == "episodeOver":
            self._on_deal_end(m)

    def _on_play(self, m):
        pos, act = m.get("curPos"), m.get("curAction")
        if pos is None or pos < 0 or not act:
            return
        if act[0] == "PASS":
            self.events.append(('pass', pos))
            return
        mv = self.move(act)
        self.events.append(('play', pos, mv))
        self.played[pos] += mv.size

    def _on_exchange(self, stage, m):





        kind = 'tribute' if stage == "tribute" else 'return'
        for item in (m.get("result") or []):
            giver, receiver, card = item[0], item[1], item[2]
            r = rank_of_char(card[1])
            self.events.append((kind, giver, r))
            self.tribute_ranks[r] += 1
            self.net_tribute[giver] -= 1
            self.net_tribute[receiver] += 1

    def _on_deal_end(self, m):






        order = m.get("order") or []
        if len(order) != 4:
            return
        dd = (order[0] + 2) % 4 == order[1]
        self.prev_double_down = (1 if dd and order[0] % 2 == 0
                                 else (-1 if dd else 0))


    def move(self, raw):
        return MoveView(raw, rank_of_char(self.level_char), self.level_char)

    def legal(self, act):







        lc = act.get("curRank", self.level_char)
        lv = rank_of_char(lc)
        moves = [MoveView(a, lv, lc) for a in act["actionList"]]
        good = flush_potential(act["handCards"], lc)
        for mv in moves:
            if mv.size:
                mv.flush_cost = sum(
                    1 for c in mv.cards if (suit_idx(c), rank_idx(c)) in good)


        keep, out = dedupe_straight_flush_safe(moves,
                                               act["handCards"], lc)
        return out, keep

    def build_obs(self, act):
        lc = act.get("curRank", self.level_char)
        self.level_char = lc
        legal, keep = self.legal(act)
        ga = act.get("greaterAction")
        lead = None
        if act.get("stage") == "play" and ga and ga[0] != "PASS":
            lead = self.move(ga)
        hand = list(act["handCards"])



        pub = act.get("publicInfo")
        if pub:
            left = [p["rest"] for p in pub]
        else:
            left = [CARDS_PER_HAND - self.played[i] + self.net_tribute[i]
                    for i in range(4)]
        left[self.seat] = len(hand)
        obs = {
            "player": self.seat,
            "stage": act["stage"],
            "level": rank_of_char(lc),
            "level_char": lc,
            "my_level": rank_of_char(act["selfRank"]),
            "opp_level": rank_of_char(act["oppoRank"]),
            "hand": hand,
            "legal": legal,
            "lead": lead,
            "events": self.events,
            "left": left,
            "done": [n == 0 for n in left],
            "deal_idx": max(self.deal_idx, 0),
            "anti": self.anti,
            "prev_double_down": self.prev_double_down,
            "tribute_ranks": self.tribute_ranks,
            "in_flight": [],
        }
        return obs, keep




def check_moves(act, state, report):






    lc = act.get("curRank", state.level_char)
    lv = rank_of_char(lc)
    for raw in act["actionList"]:
        try:
            mv = MoveView(raw, lv, lc)
        except Exception as e:
            report("MoveView failed on %r: %r" % (raw, e))
            continue
        if mv.type == PASS:
            continue
        if len(mv.claim_ranks) != mv.size:
            report("claim/size mismatch %r: %d vs %d"
                   % (raw, len(mv.claim_ranks), mv.size))
            continue


        claims = list(mv.claim_ranks)
        extra = 0
        for c in mv.cards:
            if is_wildcard(c, lc):
                continue
            r = rank_idx(c)
            if r in claims:
                claims.remove(r)
            else:
                extra += 1
        if extra:
            report("unclaimed real cards in %r (extra=%d n_wild=%d)"
                   % (raw, extra, mv.n_wild))
        if mv.type in (STRAIGHT, SFLUSH, PLATE, TUBE):
            want = {STRAIGHT: 5, SFLUSH: 5, PLATE: 3, TUBE: 2}[mv.type]
            distinct = sorted(set(mv.claim_ranks))
            if len(distinct) != want:
                report("%s should span %d ranks, got %d in %r"
                       % (TYPE_NAMES[mv.type], want, len(distinct), raw))
                continue
            seqs = sorted(seq_value(IDX_RANK_CHAR[r]) for r in distinct)
            alt = sorted(s + 13 if s == 1 else s for s in seqs)
            if not (_run(seqs) or _run(alt)):
                report("%s ranks not consecutive %r -> %r"
                       % (TYPE_NAMES[mv.type], raw, distinct))


def _run(seq):
    return all(b - a == 1 for a, b in zip(seq, seq[1:]))


def check_counts(obs, state, act, report):






    if act.get("publicInfo"):
        for i, n in enumerate(obs["left"]):
            if i == state.seat:
                continue
            want = CARDS_PER_HAND - state.played[i] + state.net_tribute[i]
            if n != want:
                report("left[%d]=%d but events imply %d" % (i, n, want))
    v = TOTAL_COPIES.copy()
    for c in obs["hand"]:
        v[rank_idx(c)] -= 1.0
    for ev in obs["events"]:
        if ev[0] == 'play':
            for c in ev[2].cards:
                v[rank_idx(c)] -= 1.0
    if (v < -1e-6).any():
        report("unseen negative before clip: %s" % v.tolist())




def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", default="ws://localhost:8181")
    ap.add_argument("--seat", type=int, required=True, choices=[0, 1, 2, 3],
                    help="informational: the real seat comes from the server's "
                         "userNum (join order). Used for --user-id and to "
                         "decide whether to create the room.")
    ap.add_argument("--room-id", type=int, default=None,
                    help="join this room; omit to create one and print its id")
    ap.add_argument("--user-id", type=int, default=None)
    ap.add_argument("--agent", default="rule",
                    help="ckpt path (*.pt) | rule | random")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--round", type=int, default=600,
                    help="the `round` field sent with CREATE_ROOM (the server "
                         "keeps dealing well past it; use --max-decisions to "
                         "bound a test run). Only used when creating the room.")
    ap.add_argument("--selfcheck", action="store_true",
                    help="validate the rebuilt observation every decision")
    ap.add_argument("--max-decisions", type=int, default=0,
                    help="stop after N decisions (0 = run until disconnect). "
                         "Testing only: the server has no disconnect handling "
                         "and crashes with 'not opened' the next time it tries "
                         "to broadcast to a seat that left mid-match, so kill "
                         "all four seats and the server together instead.")
    args = ap.parse_args(argv)

    agent = make_agent(args.agent, device=args.device)()
    env = WebSocketEnv(args.user_id if args.user_id is not None
                       else 100 + args.seat, args.url)
    seat = (env.create_room(args.round) if args.room_id is None
            else env.join_room(args.room_id))
    print("[ws] connected room=%s seat=%d agent=%s"
          % (env.room_id, seat, args.agent))
    if args.room_id is None:
        print("[ws] ROOM_ID=%s  (other seats join with --room-id %s)"
              % (env.room_id, env.room_id))

    state = MatchState(seat)
    problems = []

    def report(msg):
        problems.append(msg)
        print("[check] %s" % msg)

    n_dec = 0
    try:
        while True:
            m = env.next_message()
            if m is None:
                break
            t = m.get("type")
            if t == "notify":
                if m.get("stage") == "episodeOver":
                    print("[deal %d] order=%s" % (state.deal_idx,
                                                  m.get("order")))
                elif m.get("stage") == "gameResult":
                    print("[match] victory=%s victoryNum=%s"
                          % (m.get("victory"), m.get("victoryNum")))
                state.on_notify(m)
                continue
            if t != "act":
                continue
            if args.selfcheck:
                check_moves(m, state, report)
            obs, keep = state.build_obs(m)
            if args.selfcheck:
                check_counts(obs, state, m, report)
            j = agent.act(obs)
            raw = m["actionList"][keep[j]]
            stage = m["stage"]
            if stage == "play":
                env.send_play(raw)
            elif stage == "tribute":
                env.send_tribute(raw)
            elif stage == "back":
                env.send_paytribute(m["tributePos"], m["tribute"], raw)
            else:
                raise RuntimeError("unknown act stage %r" % stage)
            n_dec += 1
            if args.max_decisions and n_dec >= args.max_decisions:
                print("[ws] reached --max-decisions %d" % n_dec)
                break
    except KeyboardInterrupt:
        pass
    finally:
        env.close()

    print("[ws] done: %d decisions, %d deals" % (n_dec, state.deal_idx + 1))
    if args.selfcheck:
        print("[check] %d problem(s)" % len(problems))
        return 1 if problems else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
