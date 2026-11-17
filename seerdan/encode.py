import numpy as np

from .cards import NUM_CARDS, NUM_RANKS, TOTAL_COPIES_LIST, is_wildcard, rank_idx
from .combos_adapter import N_TYPES, PASS, SFLUSH

VOCAB = 176
PAD_TOK, BOS_TOK = 0, 1
LEVEL_BASE = 2
PLAYER_BASE = 15
TYPE_BASE = 19
TRIBUTE_TOK, RETURN_TOK = 30, 31
RANK_BASE = 32
SUIT_BASE = 48
MY_LEVEL_BASE = 52
ANTI_TOK = 65
DOUBLE_DOWN_OURS_TOK = 47
DOUBLE_DOWN_THEIRS_TOK = 66
UNSEEN_BASE = 69
HANDSIZE_BASE = 144
MAX_SEQ = 512

LEGACY_VOCAB = 48
LEGACY_FEAT_DIM = 188


MATCH_PROGRESS_FEAT = 222



BASE_FEAT_DIM = 239



SF_FEAT_DIM = 9
SF_COL_IS_SF = BASE_FEAT_DIM
SF_COL_SUIT = BASE_FEAT_DIM + 1
SF_COL_USES_LEVEL = BASE_FEAT_DIM + 5
SF_COL_USES_WILD = BASE_FEAT_DIM + 6
SF_COL_ROUND = BASE_FEAT_DIM + 7
SF_COL_EARLY = BASE_FEAT_DIM + 8





SF_EARLY_CARDS = 20
SF_EARLY_ROUNDS = 3

FEAT_DIM = BASE_FEAT_DIM + SF_FEAT_DIM


def tokenize(obs, unseen=None):

    viewer = obs["player"]
    toks = [BOS_TOK, LEVEL_BASE + obs["level"],
            MY_LEVEL_BASE + obs["my_level"],
            MY_LEVEL_BASE + obs["opp_level"]]
    dd = obs["prev_double_down"]
    if dd > 0:
        toks.append(DOUBLE_DOWN_OURS_TOK)
    elif dd < 0:
        toks.append(DOUBLE_DOWN_THEIRS_TOK)







    uv = unseen_vec(obs) if unseen is None else unseen
    for r in range(NUM_RANKS):
        toks.append(UNSEEN_BASE + r * 5 + min(int(round(uv[r] * 4.0)), 4))
    left = obs["left"]
    for rel in range(4):
        toks.append(HANDSIZE_BASE + rel * 8
                    + min(int(left[(viewer + rel) % 4]), 7))
    header_len = len(toks)
    for ev in obs["events"]:
        kind = ev[0]
        if kind == 'anti':
            toks.append(ANTI_TOK)
            continue
        p = (ev[1] - viewer) % 4
        if kind == 'pass':
            toks.append(PLAYER_BASE + p)
            toks.append(TYPE_BASE + PASS)
        elif kind == 'play':
            mv = ev[2]
            toks.append(PLAYER_BASE + p)
            toks.append(TYPE_BASE + mv.type)
            for r in sorted(mv.claim_ranks):
                toks.append(RANK_BASE + r)
            if mv.type == SFLUSH and mv.flush_suit >= 0:
                toks.append(SUIT_BASE + mv.flush_suit)
        elif kind == 'tribute':
            toks += [PLAYER_BASE + p, TRIBUTE_TOK, RANK_BASE + ev[2]]
        elif kind == 'return':
            toks += [PLAYER_BASE + p, RETURN_TOK, RANK_BASE + ev[2]]
    if len(toks) > MAX_SEQ:
        toks = toks[:header_len] + toks[-(MAX_SEQ - header_len):]
    return toks


def sf_early_flag(obs):




    hand = obs.get("hand") or ()
    return (len(hand) >= SF_EARLY_CARDS
            or int(obs.get("round_idx", 0)) < SF_EARLY_ROUNDS)


def candidate_is_sf(feats):

    import numpy as _np
    return _np.asarray(feats)[:, SF_COL_IS_SF] > 0.5


def hand_action_features(obs, move, out=None):






    lv = obs["level"]
    lc = obs["level_char"]
    me = obs["player"]
    f = np.zeros(FEAT_DIM, dtype=np.float32) if out is None else out
    hand = obs["hand"]

    for c in hand:
        f[rank_idx(c)] += 0.25
    i = 15
    f[i] = sum(1 for c in hand if is_wildcard(c, lc)) / 2.0; i += 1
    f[i] = len(hand) / 27.0; i += 1
    for rel in range(4):
        f[i + rel] = obs["left"][(me + rel) % 4] / 27.0
    i += 4
    for rel in range(4):
        f[i + rel] = 1.0 if obs["done"][(me + rel) % 4] else 0.0
    i += 4
    f[i + lv] = 1.0; i += 13
    f[i + move.type] = 1.0; i += N_TYPES
    for r in move.claim_ranks:
        f[i + r] += 0.25
    i += 15
    for cid in move.ids:
        f[i + cid] = 1.0
    i += NUM_CARDS
    f[i] = move.size / 27.0; i += 1
    f[i] = move.n_wild / 2.0; i += 1
    f[i] = (move.key / 15.0) if move.type != PASS else 0.0; i += 1
    lead = obs["lead"]
    if lead is not None and lead.type != PASS:
        f[i + lead.type] = 1.0
        f[i + N_TYPES] = lead.key / 15.0
    else:
        f[i + N_TYPES + 1] = 1.0
    i += N_TYPES + 2
    assert i == LEGACY_FEAT_DIM


    if move.size:
        for s in move.suits:
            if s >= 0:
                f[i + s] += 1.0 / move.size
    i += 4
    f[i] = 1.0 if move.is_four_kings() else 0.0; i += 1
    f[i + obs["my_level"]] = 1.0; i += 13
    f[i + obs["opp_level"]] = 1.0; i += 13
    f[i] = 0.0 if obs["stage"] == "play" else 1.0; i += 1
    f[i] = 1.0 if obs["anti"] else 0.0; i += 1

    f[i] = obs["prev_double_down"] * (1.0 if me % 2 == 0 else -1.0); i += 1
    f[i] = min(obs["deal_idx"], 30) / 30.0; i += 1
    tr = obs["tribute_ranks"]
    for r in range(15):
        f[i + r] = tr[r] * 0.25
    i += 15




    f[i] = move.flush_cost * 0.25; i += 1
    assert i == BASE_FEAT_DIM


    is_sf = (move.type == SFLUSH) and move.size > 0
    f[i] = 1.0 if is_sf else 0.0; i += 1
    if is_sf and 0 <= int(move.flush_suit) < 4:
        f[i + int(move.flush_suit)] = 1.0
    i += 4
    uses_level = 0.0
    if is_sf:
        for c in move.cards:
            if rank_idx(c) == lv:
                uses_level = 1.0
                break
    f[i] = uses_level; i += 1
    f[i] = (move.n_wild / 2.0) if is_sf else 0.0; i += 1
    f[i] = min(float(obs.get("round_idx", 0)), 10.0) / 10.0; i += 1
    f[i] = 1.0 if sf_early_flag(obs) else 0.0; i += 1
    assert i == FEAT_DIM
    return f


def encode_decision(obs, unseen=None):

    toks = tokenize(obs, unseen=unseen)
    feats = np.zeros((len(obs["legal"]), FEAT_DIM), dtype=np.float32)
    for j, mv in enumerate(obs["legal"]):
        hand_action_features(obs, mv, out=feats[j])
    return toks, feats






TOTAL_COPIES = np.array(TOTAL_COPIES_LIST, dtype=np.float32)


def unseen_vec(obs):








    v = TOTAL_COPIES.copy()
    for c in obs["hand"]:
        v[rank_idx(c)] -= 1.0
    for ev in obs["events"]:
        if ev[0] == 'play':
            for c in ev[2].cards:
                v[rank_idx(c)] -= 1.0
    for r in obs["in_flight"]:
        v[r] -= 1.0
    np.clip(v, 0.0, None, out=v)
    return (v * 0.25).astype(np.float32)


def belief_label(hidden_hands):




    lab = np.zeros(45, dtype=np.float32)
    for rel, hand in enumerate(hidden_hands):
        base = rel * 15
        for c in hand:
            lab[base + rank_idx(c)] += 0.25
    return lab


def pad_tokens(toks, length=None):
    length = length or MAX_SEQ
    arr = np.zeros(length, dtype=np.int64)
    arr[:len(toks)] = toks[:length]
    return arr, min(len(toks), length)
