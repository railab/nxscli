import numpy as np

from nxscli.transforms.operators_window import (
    fft_spectrum,
    histogram_counts,
    polar_relation,
    xy_relation,
)
from nxscli.transforms.pipeline import (
    HopGate,
    SampleStore,
    TransformPipeline,
    WindowBinaryProcessor,
    WindowUnaryProcessor,
)


def test_sample_store_max_points() -> None:
    store = SampleStore(max_points=3)
    store.ingest({"a": [1.0, 2.0, 3.0]})
    store.ingest({"a": [4.0, 5.0]})
    assert store.count("a") == 5
    assert store.series("a").tolist() == [3.0, 4.0, 5.0]
    assert store.count("missing") == 0
    assert store.series("missing").tolist() == []


def test_pipeline_fanout_same_source_fft_and_hist() -> None:
    pipe = TransformPipeline(max_points=64)
    pipe.register(
        WindowUnaryProcessor(
            name="fft",
            channel="a",
            window=8,
            hop=4,
            fn=lambda arr: fft_spectrum(arr, window_fn="rect"),
        )
    )
    pipe.register(
        WindowUnaryProcessor(
            name="hist",
            channel="a",
            window=8,
            hop=4,
            fn=lambda arr: histogram_counts(arr, bins=4, range_mode="auto"),
        )
    )

    out1 = pipe.ingest({"a": [0.0, 1.0, 0.0, -1.0]})
    assert set(out1) == {"fft", "hist"}
    assert int(out1["fft"].freq.size) > 0
    assert int(out1["hist"].counts.sum()) == 4

    out2 = pipe.ingest({"a": [0.0, 1.0]})
    assert out2 == {}

    out3 = pipe.ingest({"a": [0.0, -1.0]})
    assert set(out3) == {"fft", "hist"}


def test_pipeline_binary_xy_fanout() -> None:
    pipe = TransformPipeline(max_points=16)
    pipe.register(
        WindowBinaryProcessor(
            name="xy",
            left_channel="x",
            right_channel="y",
            window=8,
            hop=2,
            fn=lambda x, y: xy_relation(x, y, window=8),
        )
    )

    out1 = pipe.ingest({"x": [1.0, 2.0], "y": [3.0, 4.0]})
    assert set(out1) == {"xy"}
    assert out1["xy"].x.tolist() == [1.0, 2.0]
    assert out1["xy"].y.tolist() == [3.0, 4.0]

    out2 = pipe.ingest({"x": [3.0], "y": [5.0]})
    assert out2 == {}

    out3 = pipe.ingest({"x": [4.0], "y": [6.0]})
    assert set(out3) == {"xy"}
    assert np.allclose(out3["xy"].x, np.asarray([1.0, 2.0, 3.0, 4.0]))


def test_pipeline_binary_xy_and_polar_fanout() -> None:
    pipe = TransformPipeline(max_points=16)
    pipe.register(
        WindowBinaryProcessor(
            name="xy",
            left_channel="x",
            right_channel="y",
            window=8,
            hop=2,
            fn=lambda x, y: xy_relation(x, y, window=8),
        )
    )
    pipe.register(
        WindowBinaryProcessor(
            name="polar",
            left_channel="x",
            right_channel="y",
            window=8,
            hop=2,
            fn=lambda x, y: polar_relation(x, y, window=8),
        )
    )

    out = pipe.ingest({"x": [1.0, 0.0], "y": [0.0, 1.0]})
    assert set(out) == {"xy", "polar"}
    assert np.allclose(out["polar"].theta, np.asarray([0.0, np.pi / 2.0]))
    assert np.allclose(out["polar"].radius, np.asarray([1.0, 1.0]))


def test_pipeline_store_property_and_hop_gate_zero_count() -> None:
    pipe = TransformPipeline(max_points=2)
    assert isinstance(pipe.store, SampleStore)
    gate = HopGate(hop=2)
    assert gate.ready(0) is False
