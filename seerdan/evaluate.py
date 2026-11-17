def make_agent(spec, seed=None, device="cpu"):

    if spec == "random":
        from .agents import RandomAgent
        return lambda: RandomAgent(seed)
    if spec == "rule":
        from .agents import RuleAgent
        return lambda: RuleAgent()
    if spec.endswith(".enc"):
        from .agents import TorchAgent
        from .weights import load_policy
        model = load_policy(spec, device=device)
        return lambda: TorchAgent(model, device=device)
    raise ValueError("unknown agent spec %r (use 'rule', 'random' or a *.enc"
                     " checkpoint)" % (spec,))
