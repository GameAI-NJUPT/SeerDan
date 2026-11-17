NUM_CARDS = 108
NUM_RANKS = 15
SJ, BJ = 13, 14
RANK_NAMES = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10",
              "J", "Q", "K", "sj", "BJ"]


_RANK_IDX = {'A': 0, '2': 1, '3': 2, '4': 3, '5': 4, '6': 5, '7': 6, '8': 7,
             '9': 8, 'T': 9, 'J': 10, 'Q': 11, 'K': 12, 'B': SJ, 'R': BJ}

IDX_RANK_CHAR = {v: k for k, v in _RANK_IDX.items()}


_SUIT_IDX = {'H': 0, 'D': 1, 'S': 2, 'C': 3}


_SEQ_VAL = {'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
            '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13}


def rank_idx(card: str) -> int:

    return _RANK_IDX[card[1]]


def rank_of_char(ch: str) -> int:

    return _RANK_IDX[ch]


def suit_idx(card: str) -> int:

    return -1 if card[1] in ('B', 'R') else _SUIT_IDX[card[0]]


def z10_suit_idx(card: str) -> int:

    return -1 if card[1] in ('B', 'R') else 'SHCD'.index(card[0])


def level_idx(level_char: str) -> int:

    return _RANK_IDX[level_char]


def is_wildcard(card: str, level_char: str) -> bool:

    return card[0] == 'H' and card[1] == level_char


def seq_value(rank_char: str) -> int:

    return _SEQ_VAL[rank_char]


def seq_to_rank(v: int) -> int:

    return 0 if v in (1, 14) else v - 1


def base_card_id(card: str) -> int:

    r = rank_idx(card)
    if r >= SJ:
        return 52 if r == SJ else 53
    return r * 4 + suit_idx(card)


def card_ids(cards) -> list:







    seen = {}
    out = []
    for c in cards:
        b = base_card_id(c)
        n = seen.get(b, 0)
        seen[b] = n + 1
        out.append(b + 54 * min(n, 1))
    return out


def _build_order_tables():


    tables = []
    for lv in range(13):
        seq = [r for r in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 0] if r != lv]
        seq.append(lv)
        seq += [SJ, BJ]
        t = [0] * NUM_RANKS
        for pos, r in enumerate(seq):
            t[r] = pos
        tables.append(t)
    return tables


_ORDER_TABLE = _build_order_tables()


def order_of(rank: int, lv: int) -> int:

    return _ORDER_TABLE[lv][rank]




SEQ_WINDOWS = [[i + k for k in range(5)] for i in range(0, 9)] \
    + [[9, 10, 11, 12, 0]]


def flush_potential(hand, level_char):







    by_suit = {}
    for c in hand:
        s = suit_idx(c)
        if s >= 0 and not is_wildcard(c, level_char):
            by_suit.setdefault(s, set()).add(rank_idx(c))
    good = set()
    for s, ranks in by_suit.items():
        for win in SEQ_WINDOWS:
            have = [r for r in win if r in ranks]
            if len(have) >= 3:
                good.update((s, r) for r in have)
    return good




TOTAL_COPIES_LIST = [8] * 13 + [2, 2]
