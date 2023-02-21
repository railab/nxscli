import matplotlib


def pytest_sessionstart(session):
    # force no TK gui
    matplotlib.use("Agg")
