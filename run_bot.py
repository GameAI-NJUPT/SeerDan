import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CKPT = os.path.join(HERE, "ckpts", "seerdan_policy.enc")


def main(argv):
    from seerdan.ws_client import main as ws_main

    argv = list(argv)
    if "--agent" not in argv:
        argv += ["--agent", DEFAULT_CKPT]
    return ws_main(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
