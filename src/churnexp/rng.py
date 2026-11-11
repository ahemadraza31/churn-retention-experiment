"""Deterministic, order-independent seeded RNG streams based on numpy SeedSequence and PCG64."""

import hashlib
import numpy as np
from numpy.random import Generator, PCG64, SeedSequence


class RngFactory:
    """Factory for deterministic, order-independent random number generators."""

    def __init__(self, master_seed: int = 20261022) -> None:
        if not isinstance(master_seed, int) or isinstance(master_seed, bool):
            raise ValueError(f"master_seed must be an integer, got {type(master_seed).__name__}")
        self.master_seed = master_seed

    @staticmethod
    def _stable_hash_int(name: str) -> int:
        """Convert a name into a stable 32-bit unsigned integer using SHA-256."""
        if not isinstance(name, str):
            raise ValueError(f"name must be a string, got {type(name).__name__}")
        digest = hashlib.sha256(name.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], byteorder="big", signed=False)

    def stream(self, name: str) -> Generator:
        """Return an independent Generator derived deterministically from the master seed and name."""
        name_int = self._stable_hash_int(name)
        # Using spawn_key=(name_int,) produces a deterministic, order-independent seed sequence
        ss = SeedSequence(entropy=self.master_seed, spawn_key=(name_int,))
        return Generator(PCG64(ss))

    def entity_stream(self, domain: str, index: int) -> Generator:
        """Return an independent Generator for a specific entity within a domain.

        Uses SeedSequence(entropy=master_seed, spawn_key=(stable_domain_int, index)).
        The result is strictly independent of the order in which streams are generated.
        """
        if not isinstance(index, int) or isinstance(index, bool) or index < 0:
            raise ValueError(f"index must be a non-negative integer, got {index!r}")
        domain_int = self._stable_hash_int(domain)
        ss = SeedSequence(entropy=self.master_seed, spawn_key=(domain_int, index))
        return Generator(PCG64(ss))
