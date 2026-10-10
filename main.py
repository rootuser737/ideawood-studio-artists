import sys


def _main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--selftest":
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from ideawood_artists.selftest import run
        sys.exit(run(sys.argv[2]))
    from ideawood_artists.gui import main
    main()


if __name__ == "__main__":
    _main()
