"""Example 2: Out-of-Place Writes & Greedy Garbage Collection.

Demonstrates automated page allocation, Logical-to-Physical (L2P) address translation,
out-of-place updates, and greedy victim block selection during Garbage Collection.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flash_sim import FlashSimulator, PageState


def main() -> None:
    print("=" * 70)
    print("    OUT-OF-PLACE WRITES & GREEDY GARBAGE COLLECTION DEMO")
    print("=" * 70)

    # Small device: 3 blocks x 4 pages = 12 total pages
    sim = FlashSimulator(num_blocks=3, pages_per_block=4, page_size_bytes=4096)
    print(f"\n[+] Created FlashSimulator (3 blocks × 4 pages = {sim.total_pages} total pages):")
    print(f"    - Free pages: {sim.total_free_pages}")
    print(f"    - GC threshold: <= {sim.gc_threshold_free_pages} free pages")

    # 1. Fill Block 0 with initial data across LBAs 0, 1, 2, 3
    print("\n[+] Step 1: Performing initial host writes to LBAs 0, 1, 2, 3...")
    for lba in range(4):
        coord = sim.write_logical_page(lba=lba, data=f"initial_data_lba_{lba}")
        print(f"    - Written LBA {lba} -> Block {coord[0]}, Page {coord[1]}")

    print(f"    Current state: Free={sim.total_free_pages}, Valid={sim.total_valid_pages}, Invalid={sim.total_invalid_pages}")

    # 2. Overwrite LBAs 0, 1, 2 (creating 3 invalid pages in Block 0)
    print("\n[+] Step 2: Overwriting LBAs 0, 1, 2 (creates 3 INVALID pages in Block 0)...")
    for lba in range(3):
        coord = sim.write_logical_page(lba=lba, data=f"updated_data_lba_{lba}")
        print(f"    - Overwritten LBA {lba} -> Block {coord[0]}, Page {coord[1]}")

    print(f"\n[+] Block 0 Inspection:")
    b0 = sim.blocks[0]
    print(f"    - Valid pages: {b0.valid_page_count} (LBA 3 is still valid)")
    print(f"    - Invalid pages: {b0.invalid_page_count} (LBAs 0, 1, 2 superseded)")
    print(f"    - Free pages: {b0.free_page_count}")

    # 3. Write more data to consume free space down toward GC threshold
    print("\n[+] Step 3: Writing LBAs 4, 5, 6, 7 to trigger space reclamation...")
    for lba in range(4, 8):
        coord = sim.write_logical_page(lba=lba, data=f"data_lba_{lba}")
        print(f"    - Written LBA {lba} -> Block {coord[0]}, Page {coord[1]}")

    print(f"\n[+] Status Prior to Manual GC:")
    print(f"    - Free pages: {sim.total_free_pages}")
    print(f"    - Valid pages: {sim.total_valid_pages}")
    print(f"    - Invalid pages: {sim.total_invalid_pages}")
    print(f"    - Physical writes: {sim.physical_page_writes}")
    print(f"    - GC page copies: {sim.gc_page_copies}")
    print(f"    - Block erasures: {sim.block_erasures}")

    # 4. Trigger Greedy Garbage Collection
    print("\n[+] Step 4: Executing Greedy Garbage Collection cycle...")
    victim_id = sim.garbage_collect()
    print(f"    -> Erased victim block: Block {victim_id}")

    print(f"\n[+] Status After GC Cycle:")
    print(f"    - Free pages: {sim.total_free_pages}")
    print(f"    - Valid pages: {sim.total_valid_pages}")
    print(f"    - Invalid pages: {sim.total_invalid_pages}")
    print(f"    - Physical writes: {sim.physical_page_writes}")
    print(f"    - GC page copies: {sim.gc_page_copies} (surviving valid page was migrated)")
    print(f"    - Block erasures: {sim.block_erasures}")
    print(f"    - Block 0 erase count: {sim.blocks[0].erase_count}")

    # 5. Verify payload integrity for relocated page
    print("\n[+] Step 5: Verifying L2P data integrity for relocated LBA 3...")
    data_3 = sim.read_logical_page(lba=3)
    new_coord_3 = sim.get_physical_address(lba=3)
    print(f"    - Read LBA 3 payload: '{data_3}'")
    print(f"    - New physical location for LBA 3: Block {new_coord_3[0]}, Page {new_coord_3[1]}")
    assert data_3 == "initial_data_lba_3", "Payload integrity check failed!"
    print("    ✓ Payload verified successfully!")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
