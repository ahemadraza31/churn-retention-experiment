"""Unit tests for deterministic RngFactory and order-independent stream generation."""

import numpy as np
import pytest

from churnexp.rng import RngFactory


def test_same_seed_gives_same_draws():
    """Identical master seed and stream name produce bit-for-bit identical sequences."""
    factory1 = RngFactory(20261022)
    factory2 = RngFactory(20261022)

    gen1 = factory1.stream("customer_generator")
    gen2 = factory2.stream("customer_generator")

    draws1 = gen1.uniform(size=50)
    draws2 = gen2.uniform(size=50)
    np.testing.assert_array_equal(draws1, draws2)


def test_different_names_give_different_draws():
    """Different stream names with the same master seed produce different streams."""
    factory = RngFactory(20261022)
    gen_a = factory.stream("domain_alpha")
    gen_b = factory.stream("domain_beta")

    draws_a = gen_a.uniform(size=20)
    draws_b = gen_b.uniform(size=20)
    assert not np.array_equal(draws_a, draws_b)


def test_order_independence_named_streams():
    """Creating streams in a different order produces identical values."""
    f1 = RngFactory(20261022)
    stream_x1 = f1.stream("stream_x")
    stream_y1 = f1.stream("stream_y")

    f2 = RngFactory(20261022)
    stream_y2 = f2.stream("stream_y")  # created first in f2
    stream_x2 = f2.stream("stream_x")  # created second in f2

    np.testing.assert_array_equal(stream_x1.uniform(size=30), stream_x2.uniform(size=30))
    np.testing.assert_array_equal(stream_y1.uniform(size=30), stream_y2.uniform(size=30))


def test_different_master_seed_gives_different_values():
    """Different master seeds produce different pseudo-random sequences."""
    f1 = RngFactory(20261022)
    f2 = RngFactory(99999999)

    gen1 = f1.stream("shared_name")
    gen2 = f2.stream("shared_name")

    assert not np.array_equal(gen1.uniform(size=20), gen2.uniform(size=20))


def test_entity_stream_independence():
    """entity_stream(domain, 5) draw is independent of whether entity_stream(domain, 4) was called."""
    f1 = RngFactory(20261022)
    # Call entity 4 first, then 5
    _ = f1.entity_stream("customer", 4).uniform(size=100)
    draw_5_seq = f1.entity_stream("customer", 5).uniform(size=25)

    f2 = RngFactory(20261022)
    # Directly call entity 5 without ever calling entity 4
    draw_5_direct = f2.entity_stream("customer", 5).uniform(size=25)

    np.testing.assert_array_equal(draw_5_seq, draw_5_direct)


def test_rng_input_validation():
    """RngFactory validates master_seed, name, and entity indices."""
    with pytest.raises(ValueError):
        RngFactory("not_an_int")  # type: ignore

    with pytest.raises(ValueError):
        RngFactory(True)  # type: ignore

    f = RngFactory(20261022)
    with pytest.raises(ValueError):
        f.stream(123)  # type: ignore

    with pytest.raises(ValueError):
        f.entity_stream("customer", -1)

    with pytest.raises(ValueError):
        f.entity_stream("customer", "0")  # type: ignore
