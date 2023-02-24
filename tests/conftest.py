from unittest import mock

import matplotlib
import pytest  # type: ignore

import nxscli


def pytest_sessionstart(session):
    # force no TK gui
    matplotlib.use("Agg")


@pytest.fixture(scope="session", autouse=True)
def default_session_fixture(request):
    # mock MplManager show method
    patched = mock.patch.object(
        nxscli.plot_mpl.MplManager, "show", autospec=True
    )
    patched.start()

    def unpatch():
        patched.stop

    request.addfinalizer(unpatch)
