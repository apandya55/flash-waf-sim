"""Targeted checks used by the research experiments."""

import pytest

from flash_sim.models import FlashOutOfSpaceError
from flash_sim.simulator import FlashSimulator


def test_page_updates_preserve_latest_data_through_gc() -> None:
    sim = FlashSimulator(num_blocks=4, pages_per_block=4, gc_threshold_free_pages=1)
    expected = {}
    for i in range(80):
        lba = i % 5
        expected[lba] = f"version-{i}".encode()
        sim.write_logical_page(lba, expected[lba])
        sim.check_invariants()
    assert {lba: sim.read_logical_page(lba) for lba in expected} == expected


def test_no_reclaimable_space_raises_without_corrupting_mapping() -> None:
    sim = FlashSimulator(num_blocks=1, pages_per_block=2, gc_threshold_free_pages=0)
    sim.write_logical_page(1, b"old")
    sim.write_logical_page(2, b"other")
    with pytest.raises(FlashOutOfSpaceError):
        sim.write_logical_page(3, b"third")
    assert sim.read_logical_page(1) == b"old"
    assert sim.read_logical_page(2) == b"other"
    sim.check_invariants()


def test_page_state_conservation_and_erase_accounting() -> None:
    sim = FlashSimulator(num_blocks=3, pages_per_block=4, gc_threshold_free_pages=1)
    for i in range(30):
        sim.write_logical_page(i % 3, bytes([i]))
        sim.check_invariants()
    assert sim.total_free_pages + sim.total_valid_pages + sim.total_invalid_pages == sim.total_pages
    assert sim.block_erasures == sum(block.erase_count for block in sim.blocks)
