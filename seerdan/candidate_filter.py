from collections import Counter

from .cards import flush_potential, is_wildcard, rank_idx, suit_idx
from .combos_adapter import SFLUSH


def _semantic_key(mv):

    return (mv.type, mv.key, tuple(sorted(mv.claim_ranks)), mv.n_wild)


def _sf_removed(cards, sf_before):

    return tuple(sorted(
        (suit_idx(card), rank_idx(card))
        for card in cards
        if (suit_idx(card), rank_idx(card)) in sf_before
    ))


def _protection_sets(hand, level_char):

    counts = Counter()
    for card in hand:
        if not is_wildcard(card, level_char) and rank_idx(card) < 13:
            counts[rank_idx(card)] += 1
    bomb_ranks = {rank for rank, count in counts.items() if count >= 4}
    bomb_cards = {
        card for card in hand
        if rank_idx(card) in bomb_ranks
        and not is_wildcard(card, level_char)
    }
    return bomb_cards, flush_potential(hand, level_char)


def _representative_key(mv, bomb_cards, sf_cards):

    bomb_overlap = 0 if mv.is_bombish() else sum(
        1 for card in mv.cards if card in bomb_cards)
    sf_overlap = 0 if mv.type == SFLUSH else sum(
        1 for card in mv.cards
        if (suit_idx(card), rank_idx(card)) in sf_cards)
    return (
        bomb_overlap,
        sf_overlap,
        mv.n_wild,
        tuple(sorted(mv.cards)),
    )


def dedupe_straight_flush_safe(moves, hand, level_char):








    groups = {}
    for index, move in enumerate(moves):
        groups.setdefault(_semantic_key(move), []).append((index, move))

    bomb_cards, sf_cards = _protection_sets(hand, level_char)
    kept = []
    reps = []
    for entries in groups.values():
        if len(entries) == 1:
            index, move = entries[0]
            kept.append(index)
            reps.append(move)
            continue
        sf_groups = {}
        for index, move in entries:
            removed = _sf_removed(move.cards, sf_cards)
            sf_groups.setdefault(removed, []).append((index, move))
        for sf_entries in sf_groups.values():
            index, move = min(
                sf_entries,
                key=lambda item: _representative_key(
                    item[1], bomb_cards, sf_cards))
            kept.append(index)
            reps.append(move)



    order = sorted(range(len(kept)), key=lambda i: kept[i])
    return [kept[i] for i in order], [reps[i] for i in order]
