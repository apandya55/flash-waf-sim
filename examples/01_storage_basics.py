"""Example 1: Flash Storage Basics & State Machine.

Demonstrates the core physical hierarchy of NAND flash memory:
- Blocks (erase units) and Pages (program units)
- 3-state page lifecycle: FREE -> VALID -> INVALID -> FREE
- Out-of-bounds LBA reverse mapping
- Device capacity calculation and hardware counters
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flash_sim import FlashSimulator, PageState


def main() -> None:
    print("=" * 70)
    print("      FLASH STORAGE BASICS & THREE-STATE PAGE LIFECYCLE DEMO")
    print("=" * 70)

    # 1. Initialize a small 4-block simulator for clear inspection
    sim = FlashSimulator(num_blocks=4, pages_per_block=8, page_size_bytes=4096)
    print(f"\n[+] Initialized FlashSimulator:")
    print(f"    - Blocks: {sim.num_blocks}")
    print(f"    - Pages per block: {sim.pages_per_block}")
    print(f"    - Total physical pages: {sim.total_pages}")
    print(f"    - Raw physical capacity: {sim.total_capacity_bytes / 1024:.1f} KiB")
    print(f"    - Free pages: {sim.total_free_pages}/{sim.total_pages}")

    # 2. Inspect an initial page (must be FREE)
    page_0_0 = sim.get_page(block_idx=0, page_idx=0)
    print(f"\n[+] Initial Page State (Block 0, Page 0):")
    print(f"    - State: {page_0_0.state.name} (is_free={page_0_0.is_free})")
    print(f"    - LBA: {page_0_0.lba}")
    print(f"    - Data: {page_0_0.data}")

    # 3. Simulate programming a page (FREE -> VALID)
    print("\n[+] Programming Page (Block 0, Page 0) with LBA 101...")
    page_0_0.state = PageState.VALID
    page_0_0.lba = 101
    page_0_0.data = b"Hello NAND Flash!"
    sim.physical_page_writes += 1
    sim.l2p[101] = (0, 0)

    print(f"    - State: {page_0_0.state.name} (is_valid={page_0_0.is_valid})")
    print(f"    - LBA: {page_0_0.lba}")
    print(f"    - Payload: {page_0_0.data.decode('ascii')}")
    print(f"    - L2P Mapping: LBA 101 -> {sim.get_physical_address(101)}")

    # 4. Simulate an out-of-place overwrite (Block 0, Page 0 -> INVALID, new write -> VALID)
    print("\n[+] Overwriting LBA 101 (Out-of-place update to Block 0, Page 1)...")
    # Old location marked INVALID (stale)
    page_0_0.state = PageState.INVALID

    # New location programmed
    page_0_1 = sim.get_page(block_idx=0, page_idx=1)
    page_0_1.state = PageState.VALID
    page_0_1.lba = 101
    page_0_1.data = b"Updated NAND Data!"
    sim.physical_page_writes += 1
    sim.l2p[101] = (0, 1)

    print(f"    - Old Page (0, 0) State: {page_0_0.state.name} (is_invalid={page_0_0.is_invalid})")
    print(f"    - New Page (0, 1) State: {page_0_1.state.name} (is_valid={page_0_1.is_valid})")
    print(f"    - Updated L2P: LBA 101 -> {sim.get_physical_address(101)}")

    # 5. Check Block 0 health and stats
    b0 = sim.blocks[0]
    print(f"\n[+] Block 0 Statistics:")
    print(f"    - Total Pages: {b0.num_pages}")
    print(f"    - Free Pages: {b0.free_page_count}")
    print(f"    - Valid Pages: {b0.valid_page_count}")
    print(f"    - Invalid Pages (Garbage): {b0.invalid_page_count}")
    print(f"    - Erase Count: {b0.erase_count}")

    # 6. Simulate a block erase
    print("\n[+] Erasing Block 0...")
    b0.erase()
    sim.block_erasures += 1

    print(f"    - Erase Count: {b0.erase_count}")
    print(f"    - Free Pages: {b0.free_page_count}/{b0.num_pages}")
    print(f"    - Page (0, 0) Reset State: {sim.get_page(0, 0).state.name}")
    print(f"    - Page (0, 1) Reset State: {sim.get_page(0, 1).state.name}")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
