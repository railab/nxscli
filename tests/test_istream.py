from nxscli.istream import IServiceRegistry, IStreamProvider


def test_istream_protocols_import() -> None:
    assert IStreamProvider is not None
    assert IServiceRegistry is not None
