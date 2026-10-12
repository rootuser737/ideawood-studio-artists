import sys


def _main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--selftest":
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from ideawood_artists.selftest import run
        sys.exit(run(sys.argv[2]))
    # Show the splash FIRST (it needs only Qt), then load the rest of the app behind it.
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    from ideawood_artists.splash import Splash
    sp = Splash()
    sp.show()
    sp.step("Loading the studio code", 5)
    from ideawood_artists import gui
    gui.APP_NAME and app.setApplicationName(gui.APP_NAME)
    gui.run(app, sp)


if __name__ == "__main__":
    _main()
