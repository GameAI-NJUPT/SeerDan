from collections import Counter

from .cards import (BJ, SJ, card_ids, is_wildcard, order_of, rank_idx,
                    rank_of_char, seq_to_rank, seq_value, suit_idx)



PASS, SINGLE, PAIR, TRIPLE, FULL, STRAIGHT, PLATE, TUBE, BOMB, SFLUSH, ROCKET = range(11)
N_TYPES = 11
TYPE_NAMES = ["PASS", "SINGLE", "PAIR", "TRIPLE", "FULL", "STRAIGHT",
              "PLATE", "TUBE", "BOMB", "SFLUSH", "ROCKET"]




_TYPE_MAP = {
    "PASS": PASS,
    "Single": SINGLE,
    "Pair": PAIR,
    "Trips": TRIPLE,
    "ThreeWithTwo": FULL,
    "Straight": STRAIGHT,
    "ThreePair": PLATE,
    "TwoTrips": TUBE,
    "Bomb": BOMB,
    "StraightFlush": SFLUSH,
    "FourKings": ROCKET,
    "tribute": SINGLE,
    "back": SINGLE,
}

_SEQ_TYPES = (STRAIGHT, SFLUSH, PLATE, TUBE)
_BOMB_TIER = {4: 0, 5: 1, 6: 3, 7: 4, 8: 5, 9: 6, 10: 7}
_SF_TIER = 2
_ROCKET_TIER = 99


class MoveView:
    __slots__ = ("type", "key", "cards", "ids", "claim_ranks", "size",
                 "suits", "n_wild", "raw_type", "flush_suit", "flush_cost")

    def __init__(self, raw, lv_idx, level_char):

        t_str, r_str, cards = raw[0], raw[1], raw[2]
        self.raw_type = t_str
        self.type = _TYPE_MAP[t_str]


        self.flush_cost = 0
        if self.type == PASS:
            self.cards, self.ids, self.claim_ranks = [], [], []
            self.size, self.key, self.suits, self.n_wild = 0, 0, [], 0
            self.flush_suit = -1
            return
        self.cards = list(cards)
        self.size = len(self.cards)
        self.ids = card_ids(self.cards)
        self.suits = [suit_idx(c) for c in self.cards]
        self.n_wild = sum(1 for c in self.cards if is_wildcard(c, level_char))


        self.flush_suit = -1
        if self.type == SFLUSH:
            real = [suit_idx(c) for c in self.cards
                    if not is_wildcard(c, level_char) and suit_idx(c) >= 0]
            if real:
                self.flush_suit = Counter(real).most_common(1)[0][0]
        if t_str in ("tribute", "back"):

            r = rank_idx(self.cards[0])
            self.claim_ranks = [r]
            self.key = order_of(r, lv_idx)
            return
        self.claim_ranks = _claim_ranks(self.type, r_str, self.cards,
                                        level_char)
        self.key = _key(self.type, r_str, lv_idx)

    def is_bombish(self):
        return self.type in (BOMB, SFLUSH, ROCKET)

    def bomb_tier(self):
        if self.type == ROCKET:
            return _ROCKET_TIER
        if self.type == SFLUSH:
            return _SF_TIER
        return _BOMB_TIER.get(self.size, 0)

    def is_four_kings(self):
        return self.type == ROCKET

    def __repr__(self):
        return "%s%s" % (TYPE_NAMES[self.type], self.cards)


PASS_MOVE = MoveView(["PASS", "PASS", []], 0, "2")


def _key(mtype, r_str, lv_idx):






    if mtype == ROCKET:
        return 0
    if mtype in _SEQ_TYPES:
        return seq_value(r_str)
    return order_of(rank_of_char(r_str), lv_idx)


def _claim_ranks(mtype, r_str, cards, level_char):

    n = len(cards)
    if mtype == ROCKET:
        return [SJ, SJ, BJ, BJ]
    if mtype in (SINGLE, PAIR, TRIPLE, BOMB):
        return [rank_of_char(r_str)] * n
    if mtype == STRAIGHT or mtype == SFLUSH:
        low = seq_value(r_str)
        return [seq_to_rank(v) for v in range(low, low + 5)]
    if mtype == PLATE:
        low = seq_value(r_str)
        return [seq_to_rank(v) for v in range(low, low + 3)] * 2
    if mtype == TUBE:
        low = seq_value(r_str)
        out = []
        for v in range(low, low + 2):
            out += [seq_to_rank(v)] * 3
        return out
    if mtype == FULL:
        trip = rank_of_char(r_str)


        cnt = Counter(rank_idx(c) for c in cards
                      if not is_wildcard(c, level_char))
        cnt[trip] -= 3
        pair = trip
        for r, k in cnt.items():
            if k > 0:
                pair = r
                break
        return [trip] * 3 + [pair] * 2
    raise ValueError("unhandled move type %r" % (mtype,))


def beats(move, lead, lv_idx):


    if move.type == PASS:
        return False
    if lead is None or lead.type == PASS:
        return True
    if move.is_bombish():
        if not lead.is_bombish():
            return True
        if move.bomb_tier() != lead.bomb_tier():
            return move.bomb_tier() > lead.bomb_tier()
        return move.key > lead.key
    if lead.is_bombish():
        return False
    if move.type != lead.type or move.size != lead.size:
        return False
    return move.key > lead.key
