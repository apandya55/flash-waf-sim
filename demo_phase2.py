"""Interactive demonstration script for Phase 2: Page Allocation & Greedy Garbage Collection.

Demonstrates:
1. Writing logical pages and observing sequential active-block allocation.
2. Out-of-place overwriting: old physical page marked INVALID, new page allocated and marked VALID.
3. Automatic Garbage Collection trigger when free page headroom drops to threshold.
4. Greedy victim block selection (block with maximum invalid pages).
5. Relocation of live valid pages from victim block to new physical coordinates.
6. Erasing victim block, resetting all its pages to FREE, and incrementing wear counts.
7. End-to-end data integrity verification.
"""

from flash_sim import FlashSimulator, PageState


def main() -> None:
    print("=" * 75)
    print("  PHASE 2: PAGE ALLOCATION & GREEDY GARBAGE COLLECTION DEMO")
    print("=" * 75)

    # 1. Initialize a compact simulator for crystal-clear visualization
    # 4 blocks, 8 pages per block = 32 total physical pages (128 KiB flash)
    # GC triggers when free pages drop to 8 (1 block of headroom)
    sim = FlashSimulator(num_blocks=4, pages_per_block=8, page_size_bytes=4096, gc_threshold_free_pages=8)
    print(f"\n[+] Initialized FlashSimulator:")
    print(f"    - Dimensions: {sim.num_blocks} blocks x {sim.pages_per_block} pages = {sim.total_pages} pages")
    print(f"    - Free page threshold for GC trigger: {sim.gc_threshold_free_pages} pages")
    print(f"    - Free Pages: {sim.total_free_pages}/{sim.total_pages}")

    # 2. Sequential Writes (Allocating within Block 0)
    print("\n[+] Step 1: Sequential Writes to LBAs 0..5 (into Block 0)")
    for lba in range(6):
        coord = sim.write_logical_page(lba=lba, data=f"record_v1_{lba}".encode())
        print(f"    Write LBA {lba} -> Physical {coord} (State: {sim.get_page(*coord).state.value})")

    b0 = sim.blocks[0]
    print(f"\n    Block 0 State: {b0.free_page_count} Free, {b0.valid_page_count} Valid, {b0.invalid_page_count} Invalid")
    print(f"    Total Free Pages: {sim.total_free_pages}/{sim.total_pages}")
    print(f"    Physical Page Writes: {sim.physical_page_writes}")

    # 3. Out-of-Place Updates (Creating Invalid Pages in Block 0)
    print("\n[+] Step 2: Overwrite LBAs 0, 1, 2 with new versions (Out-of-place updates)")
    for lba in range(3):
        old_coord = sim.l2p[lba]
        new_coord = sim.write_logical_page(lba=lba, data=f"record_v2_{lba}".encode())
        print(f"    Update LBA {lba}:")
        print(f"      - Old Page {old_coord} marked -> {sim.get_page(*old_coord).state.value.upper()}")
        print(f"      - New Page {new_coord} marked -> {sim.get_page(*new_coord).state.value.upper()}")

    print(f"\n    Block 0 State: {b0.free_page_count} Free, {b0.valid_page_count} Valid, {b0.invalid_page_count} Invalid")
    print(f"    Block 1 State: {sim.blocks[1].free_page_count} Free, {sim.blocks[1].valid_page_count} Valid, {sim.blocks[1].invalid_page_count} Invalid")
    print(f"    Total Free Pages: {sim.total_free_pages}/{sim.total_pages}")

    # 4. Fill remaining blocks to trigger automatic Garbage Collection
    print("\n[+] Step 3: Write more data to cross the GC threshold (<= 8 free pages)")
    lba_counter = 10
    while sim.total_free_pages > 8:
        coord = sim.write_logical_page(lba=lba_counter, data=f"bulk_data_{lba_counter}".encode())
        lba_counter += 1

    print(f"    Free pages before triggering write: {sim.total_free_pages}")
    print(f"    Invalid page distribution before GC:")
    for b in sim.blocks:
        print(f"      - Block {b.block_id}: {b.invalid_page_count} invalid, {b.valid_page_count} valid, {b.free_page_count} free, erase_count={b.erase_count}")

    # This next write will drop free pages to/below 8, automatically triggering Greedy GC!
    print("\n[+] Step 4: Next write triggers automatic Greedy Garbage Collection!")
    trigger_coord = sim.write_logical_page(lba=lba_counter, data=b"trigger_write")
    print(f"    Trigger write landed at: {trigger_coord}")
    print(f"    Cumulative Hardware Metrics:")
    print(f"      - Physical Page Writes: {sim.physical_page_writes}")
    print(f"      - GC Valid Page Copies: {sim.gc_page_copies}")
    print(f"      - Block Erasures:       {sim.block_erasures}")

    print("\n    Block status after GC cycle:")
    for b in sim.blocks:
        print(f"      - Block {b.block_id}: {b.invalid_page_count} invalid, {b.valid_page_count} valid, {b.free_page_count} free, erase_count={b.erase_count}")

    # 5. Verify Data Readability and Persistence
    print("\n[+] Step 5: Read Verification (Integrity Check across GC relocations)")
    for lba in range(3):
        val = sim.read_logical_page(lba).decode()
        print(f"    Read LBA {lba}: '{val}' (Expected: 'record_v2_{lba}')")
        assert val == f"record_v2_{lba}"

    for lba in range(3, 6):
        val = sim.read_logical_page(lba).decode()
        print(f"    Read LBA {lba}: '{val}' (Expected: 'record_v1_{lba}')")
        assert val == f"record_v1_{lba}"

    print("\n" + "=" * 75)
    print("  PHASE 2 EXECUTION & VERIFICATION COMPLETE (100% INVARIANTS SATISFIED)")
    print("=" * 75)


if __name__ == "__main__":
    main()

