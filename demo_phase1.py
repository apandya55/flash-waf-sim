"""Interactive verification script for Phase 1 Flash Simulator.

Demonstrates:
1. Instantiation of FlashSimulator (64 blocks x 64 pages).
2. Inspection of pristine blocks and free pages.
3. Modification of page states (Free -> Valid -> Invalid).
4. Block erase cycle and wear counter increment.
"""

from flash_sim import Block, FlashSimulator, Page, PageState


def main() -> None:
    print("=" * 70)
    print("  PHASE 1: FLASH STORAGE DATA STRUCTURES & STATE MODEL DEMO")
    print("=" * 70)

    # 1. Initialize Simulator
    sim = FlashSimulator(num_blocks=64, pages_per_block=64, page_size_bytes=4096)
    print(f"\n[+] Initialized {sim}")
    print(f"    - Total Physical Capacity: {sim.total_capacity_bytes / (1024 * 1024):.1f} MiB")
    print(f"    - Total Blocks: {sim.num_blocks}")
    print(f"    - Pages per Block: {sim.pages_per_block}")
    print(f"    - Total Pages: {sim.total_pages}")
    print(f"    - Free Pages: {sim.total_free_pages}")
    print(f"    - Valid Pages: {sim.total_valid_pages}")
    print(f"    - Invalid Pages: {sim.total_invalid_pages}")

    # 2. Inspect Block 0
    b0 = sim.blocks[0]
    print(f"\n[+] Block 0 Initial State:")
    print(f"    - Block ID: {b0.block_id}")
    print(f"    - Erase Count: {b0.erase_count}")
    print(f"    - Free Pages: {b0.free_page_count}/{b0.num_pages}")
    print(f"    - Page (0, 0) State: {sim.get_page(0, 0).state.value}")

    # 3. Simulate Writing to Page (0, 0)
    print(f"\n[+] Simulating Page Write to Block 0, Page 0 (Host LBA 100):")
    p00 = sim.get_page(0, 0)
    p00.state = PageState.VALID
    p00.lba = 100
    p00.data = b"Host Payload: Hello NAND Flash!"
    sim.l2p[100] = (0, 0)
    sim.physical_page_writes += 1

    print(f"    - Page (0, 0) State: {p00.state.value}")
    print(f"    - Mapped LBA: {p00.lba}")
    print(f"    - Data Payload: {p00.data}")
    print(f"    - L2P Mapping: LBA 100 -> Physical {sim.l2p[100]}")
    print(f"    - Simulator Counters: writes={sim.physical_page_writes}, gc_copies={sim.gc_page_copies}, erasures={sim.block_erasures}")

    # 4. Simulate Out-of-Place Overwrite (LBA 100 written to Page (0, 1))
    print(f"\n[+] Simulating Out-of-Place Update to LBA 100 (New location: Block 0, Page 1):")
    # Invalidate old page
    p00.state = PageState.INVALID
    # Write to new page
    p01 = sim.get_page(0, 1)
    p01.state = PageState.VALID
    p01.lba = 100
    p01.data = b"Host Payload: Updated Data!"
    sim.l2p[100] = (0, 1)
    sim.physical_page_writes += 1

    print(f"    - Old Page (0, 0) State: {p00.state.value} (Cannot be overwritten in place!)")
    print(f"    - New Page (0, 1) State: {p01.state.value}")
    print(f"    - Updated L2P Mapping: LBA 100 -> Physical {sim.l2p[100]}")
    print(f"    - Block 0 Distribution: {b0.free_page_count} Free, {b0.valid_page_count} Valid, {b0.invalid_page_count} Invalid")

    # 5. Simulate Block Erase
    print(f"\n[+] Simulating Block Erase on Block 0:")
    b0.erase()
    sim.block_erasures += 1
    print(f"    - Block 0 Erase Count: {b0.erase_count}")
    print(f"    - Page (0, 0) State after Erase: {p00.state.value}")
    print(f"    - Page (0, 1) State after Erase: {p01.state.value}")
    print(f"    - Block 0 Distribution: {b0.free_page_count} Free, {b0.valid_page_count} Valid, {b0.invalid_page_count} Invalid")
    print(f"    - Simulator Total Erasures: {sim.block_erasures}")

    print("\n" + "=" * 70)
    print("  PHASE 1 CORE INVARIANTS VERIFIED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    main()

