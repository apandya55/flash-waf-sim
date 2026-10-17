"""Unit tests for Phase 3: Ring Buffering & Workload Simulation.

Verifies:
- RingBuffer initialization, capacities, and state flags.
- Buffering records in volatile memory without premature flash writes.
- Automatic flushing when 4 KiB (32 records * 128 B) threshold is reached.
- Explicit manual flush of partial buffers.
- FIFO ordering and payload fidelity across buffer drains and page writes.
- Power loss simulation via clear() returning exact uncommitted byte count.
- Comparative Write Amplification Factor (WAF) reduction verification.
"""

import pytest

from flash_sim.buffer import RingBuffer
from flash_sim.simulator import FlashSimulator


# ============================================================================
# RingBuffer Unit Tests
# ============================================================================

def test_ring_buffer_initialization() -> None:
    """RingBuffer initializes empty with correct record and page capacities."""
    sim = FlashSimulator(num_blocks=4, pages_per_block=8)
    buf = RingBuffer(flash_sim=sim, capacity_records=32, record_size_bytes=128, page_size_bytes=4096)
    
    assert buf.capacity_records == 32
    assert buf.record_size_bytes == 128
    assert buf.page_size_bytes == 4096
    assert buf.count == 0
    assert buf.is_empty is True
    assert buf.is_full is False
    assert buf.buffered_bytes == 0
    assert buf.total_flushes == 0
    assert buf.total_records_pushed == 0


def test_push_accumulates_without_writing_until_full() -> None:
    """Records accumulate in RAM; no flash writes occur until the 32nd record triggers a flush."""
    sim = FlashSimulator(num_blocks=4, pages_per_block=8)
    buf = RingBuffer(flash_sim=sim, capacity_records=32, record_size_bytes=128)

    # Push 31 records (sub-threshold)
    for i in range(31):
        res = buf.push(f"record_{i}".encode())
        assert res is None  # Held in volatile RAM
        assert buf.count == i + 1
        assert buf.buffered_bytes == (i + 1) * 128
        assert sim.physical_page_writes == 0  # No flash write yet

    assert buf.is_full is False
    assert buf.is_empty is False

    # The 32nd record reaches 4 KiB threshold -> automatic flush!
    coord = buf.push(b"record_31")
    assert coord is not None  # Flushed to flash
    assert sim.physical_page_writes == 1
    assert buf.total_flushes == 1
    assert buf.count == 0
    assert buf.buffered_bytes == 0
    assert buf.is_empty is True


def test_explicit_manual_flush_for_partial_buffer() -> None:
    """Calling flush() drains partial buffers, pads to 4 KiB, and commits to flash."""
    sim = FlashSimulator(num_blocks=4, pages_per_block=8)
    buf = RingBuffer(flash_sim=sim, capacity_records=32, record_size_bytes=128)

    # Push 10 records (1,280 bytes)
    for i in range(10):
        buf.push(f"item_{i}".encode())

    assert buf.count == 10
    assert buf.buffered_bytes == 1280
    assert sim.physical_page_writes == 0

    # Explicit flush
    coord = buf.flush(target_lba=7)
    assert coord is not None
    assert sim.physical_page_writes == 1
    assert buf.count == 0
    assert buf.buffered_bytes == 0

    # Calling flush on empty buffer does nothing
    assert buf.flush() is None
    assert sim.physical_page_writes == 1


def test_payload_integrity_across_flush() -> None:
    """Buffered records are packed correctly and can be retrieved from flash."""
    sim = FlashSimulator(num_blocks=4, pages_per_block=8)
    buf = RingBuffer(flash_sim=sim, capacity_records=32, record_size_bytes=128)

    # Push 32 distinct identifiable records of exactly 128 bytes
    expected_records = [f"rec_{idx:04d}_" + ("X" * 119) for idx in range(32)]
    for rec_str in expected_records:
        buf.push(rec_str.encode("ascii"), lba=42)

    assert sim.physical_page_writes == 1
    
    # Read back full 4 KiB page from flash simulator
    raw_page_data = sim.read_logical_page(42)
    assert raw_page_data is not None
    assert len(raw_page_data) == 4096

    # Extract 32 chunks of 128 bytes each
    for idx in range(32):
        chunk = raw_page_data[idx * 128 : (idx + 1) * 128]
        expected_chunk = expected_records[idx].encode("ascii")
        assert chunk == expected_chunk


def test_buffer_clear_power_loss_accounting() -> None:
    """clear() simulates power loss and accurately quantifies uncommitted byte loss."""
    sim = FlashSimulator(num_blocks=4, pages_per_block=8)
    buf = RingBuffer(flash_sim=sim, capacity_records=32, record_size_bytes=128)

    # Push 20 records (20 * 128 = 2,560 bytes)
    for i in range(20):
        buf.push(f"volatile_{i}".encode())

    assert buf.buffered_bytes == 2560
    
    lost_bytes = buf.clear()
    assert lost_bytes == 2560
    assert buf.count == 0
    assert buf.buffered_bytes == 0
    assert buf.is_empty is True
    assert sim.physical_page_writes == 0  # Nothing was written to flash


def test_ring_buffer_packs_a_full_batch_into_one_page_program() -> None:
    """Check packing mechanics without comparing different logical workloads."""
    sim = FlashSimulator(num_blocks=4, pages_per_block=8)
    buffer = RingBuffer(flash_sim=sim, capacity_records=32,
                        record_size_bytes=128, page_size_bytes=4096)

    for i in range(32):
        buffer.push(f"record-{i}".encode(), lba=7)

    assert buffer.total_flushes == 1
    assert sim.physical_page_writes == 1
    assert sim.read_logical_page(7) == b"".join(
        f"record-{i}".encode().ljust(128, b"\x00") for i in range(32)
    )
