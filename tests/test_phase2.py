"""Unit tests for Phase 2: Page Allocation & Greedy Garbage Collection.

Verifies:
- Logical page writing (out-of-place writes, L2P updates, physical writes counter).
- Out-of-place overwrite invalidation of previous physical page.
- Logical page reading and data persistence across updates and relocations.
- Greedy Garbage Collection victim selection (highest invalid page count).
- Valid page relocation during GC (updating L2P, gc_page_copies counter).
- Block erasure during GC resetting page states to FREE and incrementing erase counters.
- Automatic GC triggering when free pages cross the threshold.
- Capacity exhaustion handling (FlashOutOfSpaceError).
"""

import pytest

from flash_sim.models import Block, FlashOutOfSpaceError, Page, PageState
from flash_sim.simulator import FlashSimulator


# ============================================================================
# Write and Read Tests
# ============================================================================

def test_write_logical_page_single() -> None:
    """Writing a single logical page allocates a free physical page and maps L2P."""
    sim = FlashSimulator(num_blocks=4, pages_per_block=8)
    
    b_idx, p_idx = sim.write_logical_page(lba=10, data=b"payload_10")
    
    # Verify physical page state
    page = sim.get_page(b_idx, p_idx)
    assert page.state == PageState.VALID
    assert page.lba == 10
    assert page.data == b"payload_10"
    
    # Verify L2P and counters
    assert sim.l2p[10] == (b_idx, p_idx)
    assert sim.physical_page_writes == 1
    assert sim.gc_page_copies == 0
    assert sim.block_erasures == 0


def test_write_logical_page_overwrite_invalidates_old() -> None:
    """Rewriting the same LBA invalidates the previous physical page and writes to a new page."""
    sim = FlashSimulator(num_blocks=4, pages_per_block=8)
    
    first_b, first_p = sim.write_logical_page(lba=5, data=b"version_1")
    second_b, second_p = sim.write_logical_page(lba=5, data=b"version_2")
    
    # Physical coordinates must differ (out-of-place update)
    assert (first_b, first_p) != (second_b, second_p)
    
    # Old page must be INVALID
    old_page = sim.get_page(first_b, first_p)
    assert old_page.state == PageState.INVALID
    assert old_page.is_invalid is True
    
    # New page must be VALID with new data
    new_page = sim.get_page(second_b, second_p)
    assert new_page.state == PageState.VALID
    assert new_page.is_valid is True
    assert new_page.data == b"version_2"
    
    # L2P must point to new page
    assert sim.l2p[5] == (second_b, second_p)
    assert sim.physical_page_writes == 2


def test_read_logical_page() -> None:
    """read_logical_page returns stored payload or None if unmapped."""
    sim = FlashSimulator(num_blocks=4, pages_per_block=8)
    
    # Unmapped LBA returns None
    assert sim.read_logical_page(99) is None
    
    # Write and read
    sim.write_logical_page(lba=1, data=b"data_one")
    assert sim.read_logical_page(1) == b"data_one"
    
    # Overwrite and read updated version
    sim.write_logical_page(lba=1, data=b"data_one_updated")
    assert sim.read_logical_page(1) == b"data_one_updated"


# ============================================================================
# Garbage Collection Tests
# ============================================================================

def test_greedy_victim_selection() -> None:
    """Greedy GC must select the block with the highest count of invalid pages."""
    sim = FlashSimulator(num_blocks=4, pages_per_block=8, gc_threshold_free_pages=0)
    
    # Manually configure blocks to test victim selection deterministically:
    # Block 0: 2 invalid pages, 6 valid pages
    for p in range(2):
        sim.blocks[0].pages[p].state = PageState.INVALID
    for p in range(2, 8):
        sim.blocks[0].pages[p].state = PageState.VALID
        sim.blocks[0].pages[p].lba = 100 + p
        sim.l2p[100 + p] = (0, p)
        
    # Block 1: 5 invalid pages, 3 valid pages (highest invalid count!)
    for p in range(5):
        sim.blocks[1].pages[p].state = PageState.INVALID
    for p in range(5, 8):
        sim.blocks[1].pages[p].state = PageState.VALID
        sim.blocks[1].pages[p].lba = 200 + p
        sim.l2p[200 + p] = (1, p)
        
    # Block 2: 1 invalid page, 7 valid pages
    sim.blocks[2].pages[0].state = PageState.INVALID
    for p in range(1, 8):
        sim.blocks[2].pages[p].state = PageState.VALID
        sim.blocks[2].pages[p].lba = 300 + p
        sim.l2p[300 + p] = (2, p)
        
    # Block 3 is pristine free (destination for relocations)
    assert sim.blocks[3].free_page_count == 8
    
    # Run GC
    victim_id = sim.garbage_collect()
    
    # Block 1 had 5 invalid pages vs 2 in Block 0 and 1 in Block 2 -> Block 1 must be victim
    assert victim_id == 1


def test_valid_page_relocation_and_l2p_update() -> None:
    """Valid pages in victim block are relocated to another block and L2P is updated."""
    sim = FlashSimulator(num_blocks=3, pages_per_block=4, gc_threshold_free_pages=0)
    
    # Configure Block 0: 3 invalid pages, 1 valid page (LBA 42)
    sim.blocks[0].pages[0].state = PageState.INVALID
    sim.blocks[0].pages[1].state = PageState.INVALID
    sim.blocks[0].pages[2].state = PageState.INVALID
    sim.blocks[0].pages[3].state = PageState.VALID
    sim.blocks[0].pages[3].lba = 42
    sim.blocks[0].pages[3].data = b"important_data"
    sim.l2p[42] = (0, 3)
    
    # Run GC
    victim_id = sim.garbage_collect()
    assert victim_id == 0
    
    # Verify relocation metrics
    assert sim.gc_page_copies == 1
    assert sim.block_erasures == 1
    
    # Verify L2P for LBA 42 was updated to a new location
    new_coord = sim.l2p[42]
    assert new_coord != (0, 3)
    new_b, new_p = new_coord
    
    # Check relocated page content
    relocated_page = sim.get_page(new_b, new_p)
    assert relocated_page.state == PageState.VALID
    assert relocated_page.lba == 42
    assert relocated_page.data == b"important_data"
    
    # Confirm readability via logical interface
    assert sim.read_logical_page(42) == b"important_data"


def test_block_erasures_reset_page_states_to_free() -> None:
    """Erasing a block resets all its pages to FREE, clears metadata, and increments erase_count."""
    sim = FlashSimulator(num_blocks=3, pages_per_block=4, gc_threshold_free_pages=0)
    
    # Block 0 has 2 invalid and 2 valid pages
    sim.blocks[0].pages[0].state = PageState.INVALID
    sim.blocks[0].pages[1].state = PageState.INVALID
    sim.blocks[0].pages[2].state = PageState.VALID
    sim.blocks[0].pages[2].lba = 10
    sim.blocks[0].pages[2].data = b"d1"
    sim.l2p[10] = (0, 2)
    sim.blocks[0].pages[3].state = PageState.VALID
    sim.blocks[0].pages[3].lba = 11
    sim.blocks[0].pages[3].data = b"d2"
    sim.l2p[11] = (0, 3)
    
    initial_erase_count = sim.blocks[0].erase_count
    
    # Trigger GC
    erased_block_id = sim.garbage_collect()
    assert erased_block_id == 0
    
    erased_block = sim.blocks[0]
    assert erased_block.erase_count == initial_erase_count + 1
    assert sim.block_erasures == 1
    
    # ALL pages in the victim block MUST reset to FREE
    assert erased_block.free_page_count == 4
    assert erased_block.valid_page_count == 0
    assert erased_block.invalid_page_count == 0
    
    for page in erased_block.pages:
        assert page.state == PageState.FREE
        assert page.is_free is True
        assert page.lba is None
        assert page.data is None


def test_automatic_gc_triggered_by_write_threshold() -> None:
    """When free pages drop to/below gc_threshold_free_pages, write_logical_page automatically triggers GC."""
    # Simulator with 3 blocks of 4 pages = 12 total pages
    # Set GC threshold to 4 free pages (1 block's worth)
    sim = FlashSimulator(num_blocks=3, pages_per_block=4, gc_threshold_free_pages=4)
    
    # Write cold data that remains valid in Block 0
    sim.write_logical_page(lba=999, data=b"cold_data")

    # Fill remaining pages and repeatedly overwrite a hot set of LBAs (0, 1, 2)
    for cycle in range(6):
        for lba in range(3):
            sim.write_logical_page(lba, f"cycle_{cycle}_{lba}".encode())
            
    # GC must have automatically fired and relocated valid pages
    assert sim.block_erasures > 0
    assert sim.gc_page_copies > 0
    
    # Verify cold data survived GC relocation intact
    assert sim.read_logical_page(999) == b"cold_data"
    
    # Hot LBAs must also be correctly readable with their latest data
    for lba in range(3):
        assert sim.read_logical_page(lba) == f"cycle_5_{lba}".encode()


def test_flash_out_of_space_error() -> None:
    """When raw physical capacity is completely exhausted with no invalid pages to reclaim, raise error."""
    # Tiny simulator: 2 blocks of 2 pages each = 4 total pages
    sim = FlashSimulator(num_blocks=2, pages_per_block=2, gc_threshold_free_pages=0)
    
    # Write 4 distinct LBAs (all become VALID, 0 INVALID pages exist)
    for lba in range(4):
        sim.write_logical_page(lba, f"unique_{lba}".encode())
        
    assert sim.total_free_pages == 0
    assert sim.total_invalid_pages == 0
    
    # Attempting to write a 5th distinct LBA must raise FlashOutOfSpaceError
    with pytest.raises(FlashOutOfSpaceError):
        sim.write_logical_page(lba=99, data=b"cannot_fit")
