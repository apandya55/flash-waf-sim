"""Unit tests for Phase 1: Storage Data Structures & State Model.

Verifies:
- Page dataclass initialization, states (free, valid, invalid), and reset behavior.
- Block dataclass page containment, erase count, state aggregations, and erase behavior.
- FlashSimulator initialization (64 blocks, 64 pages per block, all pages free).
- FlashSimulator L2P mapping dictionary and performance/hardware counters.
- Object independence (no shallow-copy/aliasing bugs across pages or blocks).
- Boundary checks and accessors.
"""

import pytest

from flash_sim.models import Block, Page, PageState
from flash_sim.simulator import FlashSimulator


# ============================================================================
# Page Tests
# ============================================================================

def test_page_initialization_defaults() -> None:
    """A fresh Page should initialize with FREE state and no metadata."""
    p = Page()
    assert p.state == PageState.FREE
    assert p.lba is None
    assert p.data is None
    assert p.is_free is True
    assert p.is_valid is False
    assert p.is_invalid is False


def test_page_state_transitions() -> None:
    """A page can be marked valid with LBA and data, then marked invalid."""
    p = Page()
    
    # Write data to page (making it valid)
    p.state = PageState.VALID
    p.lba = 42
    p.data = b"sample_data_payload"
    assert p.is_free is False
    assert p.is_valid is True
    assert p.is_invalid is False
    assert p.lba == 42
    assert p.data == b"sample_data_payload"

    # Invalidate page (e.g. after out-of-place update elsewhere)
    p.state = PageState.INVALID
    assert p.is_free is False
    assert p.is_valid is False
    assert p.is_invalid is True


def test_page_reset() -> None:
    """Resetting a page returns it to pristine FREE state with cleared metadata."""
    p = Page(state=PageState.INVALID, lba=10, data=b"obsolete")
    p.reset()
    assert p.state == PageState.FREE
    assert p.lba is None
    assert p.data is None
    assert p.is_free is True


# ============================================================================
# Block Tests
# ============================================================================

def test_block_initialization() -> None:
    """A Block should initialize with the given block_id, empty pages by default, and erase_count 0."""
    b = Block(block_id=0)
    assert b.block_id == 0
    assert b.pages == []
    assert b.erase_count == 0
    assert b.num_pages == 0
    assert b.free_page_count == 0
    assert b.valid_page_count == 0
    assert b.invalid_page_count == 0


def test_block_page_state_counts() -> None:
    """Block property counters should accurately reflect page state distributions."""
    pages = [
        Page(state=PageState.FREE),
        Page(state=PageState.FREE),
        Page(state=PageState.VALID, lba=1),
        Page(state=PageState.VALID, lba=2),
        Page(state=PageState.VALID, lba=3),
        Page(state=PageState.INVALID, lba=4),
    ]
    b = Block(block_id=1, pages=pages, erase_count=0)
    assert b.num_pages == 6
    assert b.free_page_count == 2
    assert b.valid_page_count == 3
    assert b.invalid_page_count == 1


def test_block_erase() -> None:
    """Erasing a block resets all its pages to FREE and increments erase_count."""
    pages = [
        Page(state=PageState.VALID, lba=10, data=b"data1"),
        Page(state=PageState.INVALID, lba=20, data=b"data2"),
        Page(state=PageState.FREE),
    ]
    b = Block(block_id=5, pages=pages, erase_count=3)
    
    b.erase()
    
    assert b.erase_count == 4
    assert b.num_pages == 3
    assert b.free_page_count == 3
    assert b.valid_page_count == 0
    assert b.invalid_page_count == 0
    for page in b.pages:
        assert page.is_free is True
        assert page.lba is None
        assert page.data is None


# ============================================================================
# FlashSimulator Tests
# ============================================================================

def test_simulator_default_dimensions() -> None:
    """Simulator should initialize with 64 blocks of 64 pages each (4096 pages total)."""
    sim = FlashSimulator()
    assert sim.num_blocks == 64
    assert sim.pages_per_block == 64
    assert sim.page_size_bytes == 4096
    assert sim.total_pages == 4096
    assert sim.total_capacity_bytes == 4096 * 4096  # 16 MiB
    assert len(sim.blocks) == 64
    for b_idx, block in enumerate(sim.blocks):
        assert block.block_id == b_idx
        assert block.num_pages == 64
        assert block.erase_count == 0


def test_all_pages_initialize_as_free() -> None:
    """Every single page across all blocks must initialize with state FREE."""
    sim = FlashSimulator(num_blocks=64, pages_per_block=64)
    
    # Check global aggregates
    assert sim.total_free_pages == 4096
    assert sim.total_valid_pages == 0
    assert sim.total_invalid_pages == 0

    # Explicitly inspect every page in every block
    for block in sim.blocks:
        assert block.free_page_count == 64
        assert block.valid_page_count == 0
        assert block.invalid_page_count == 0
        for page in block.pages:
            assert page.state == PageState.FREE
            assert page.is_free is True
            assert page.lba is None
            assert page.data is None


def test_hardware_counters_initialize_to_zero() -> None:
    """Write, GC copy, and erase counters must start at 0."""
    sim = FlashSimulator()
    assert sim.physical_page_writes == 0
    assert sim.gc_page_copies == 0
    assert sim.block_erasures == 0


def test_l2p_mapping_initializes_empty() -> None:
    """The Logical-to-Physical translation table must start empty."""
    sim = FlashSimulator()
    assert isinstance(sim.l2p, dict)
    assert len(sim.l2p) == 0
    assert sim.get_physical_address(0) is None
    assert sim.get_physical_address(999) is None


def test_page_object_independence() -> None:
    """Modifying one page must not affect any other page (guarantees no aliasing/shallow-copy issues)."""
    sim = FlashSimulator(num_blocks=4, pages_per_block=4)
    
    p00 = sim.get_page(0, 0)
    p00.state = PageState.VALID
    p00.lba = 100
    p00.data = b"unique"

    # Another page in the same block
    p01 = sim.get_page(0, 1)
    assert p01.is_free is True
    assert p01.lba is None

    # A page in another block
    p10 = sim.get_page(1, 0)
    assert p10.is_free is True
    assert p10.lba is None

    # Verify counts reflect only the single modified page
    assert sim.total_free_pages == 15
    assert sim.total_valid_pages == 1
    assert sim.total_invalid_pages == 0


def test_get_page_bounds_checking() -> None:
    """Out-of-range coordinates should raise IndexError."""
    sim = FlashSimulator(num_blocks=2, pages_per_block=4)
    
    # Valid bounds
    assert sim.get_page(0, 0) is not None
    assert sim.get_page(1, 3) is not None

    # Invalid block bounds
    with pytest.raises(IndexError):
        sim.get_page(-1, 0)
    with pytest.raises(IndexError):
        sim.get_page(2, 0)

    # Invalid page bounds
    with pytest.raises(IndexError):
        sim.get_page(0, -1)
    with pytest.raises(IndexError):
        sim.get_page(0, 4)


def test_custom_dimensions() -> None:
    """Simulator correctly handles non-default dimensions."""
    sim = FlashSimulator(num_blocks=8, pages_per_block=16, page_size_bytes=2048)
    assert sim.num_blocks == 8
    assert sim.pages_per_block == 16
    assert sim.page_size_bytes == 2048
    assert sim.total_pages == 128
    assert sim.total_capacity_bytes == 128 * 2048
    assert sim.total_free_pages == 128

