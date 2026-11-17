import random

import numpy as np
try:
    import torch
except ImportError:
    torch = None

from .combos_adapter import PASS
from .encode import MAX_SEQ, PAD_TOK, encode_decision, unseen_vec


class RandomAgent:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)

    def act(self, obs):
        return self.rng.randrange(len(obs["legal"]))


class RuleAgent:



    def act(self, obs):
        legal = obs["legal"]
        if obs["stage"] != "play":

            return int(min(range(len(legal)), key=lambda i: legal[i].key))
        lead = obs["lead"]
        if lead is None:
            best = min(range(len(legal)),
                       key=lambda i: (legal[i].is_bombish(), -legal[i].size,
                                      legal[i].key))
            return int(best)
        plain = [i for i, m in enumerate(legal)
                 if m.type != PASS and not m.is_bombish()]
        if plain:
            return int(min(plain, key=lambda i: legal[i].key))
        bombs = [i for i, m in enumerate(legal) if m.is_bombish()]
        if bombs:
            me = obs["player"]
            opp_min = min(obs["left"][(me + 1) % 4], obs["left"][(me + 3) % 4])
            if opp_min <= 8 or obs["left"][me] <= 10:
                return int(min(bombs, key=lambda i: (legal[i].bomb_tier(),
                                                     legal[i].key)))
        return 0 if legal[0].type == PASS else int(
            min(range(len(legal)), key=lambda i: legal[i].key))


class TorchAgent:
    def __init__(self, model, device="cpu", eps=0.0, top_k=0, rng=None):
        if torch is None:
            raise RuntimeError("TorchAgent requires PyTorch; install torch first")
        self.model = model.to(device).eval()
        self.device = device
        self.eps = eps
        self.top_k = top_k
        self.rng = rng or random.Random()

    def q_values(self, toks, feats, unseen):
        n = len(toks)
        padded = list(toks) + [PAD_TOK] * (MAX_SEQ - n)
        t = torch.tensor([padded], dtype=torch.long, device=self.device)
        ln = torch.tensor([n], dtype=torch.long, device=self.device)
        f = torch.as_tensor(feats, dtype=torch.float32,
                            device=self.device)[None]
        u = torch.as_tensor(unseen, dtype=torch.float32,
                            device=self.device)[None]
        with torch.no_grad():
            q, _ = self.model(t, ln, f, u)
        return q[0].float().cpu().numpy()

    def act(self, obs):
        n = len(obs["legal"])
        if n == 1:
            return 0
        toks, feats = encode_decision(obs)
        q = self.q_values(toks, feats, unseen_vec(obs))
        if self.eps > 0 and self.rng.random() < self.eps:
            if self.top_k > 1:
                k = min(self.top_k, n)
                return int(np.argsort(q)[-k:][self.rng.randrange(k)])
            return self.rng.randrange(n)
        return int(np.argmax(q))
