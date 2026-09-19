"""User-space Ring Buffer for aggregating small host records into full NAND flash pages.

NAND flash memory can only be programmed in physical units of pages (e.g., 4 KiB).
When host applications issue small random updates (e.g., 128 bytes), writing directly
to flash forces a full 4 KiB page program for every 128-byte payload, resulting in
catastrophic Write Amplification (WAF >= 32.0).

The RingBuffer aggregates 128-byte records in volatile RAM until 4 KiB (32 records)
is accumulated, then flushes a single coalesced 4 KiB page to FlashSimulator.
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

from flash_sim.simulator import FlashSimulator


class RingBuffer:
    """Circular buffer in volatile RAM that batches small records into full flash pages.
    
    Attributes:
        flash_sim: The underlying FlashSimulator instance receiving page writes.
        capacity_records: Number of records before buffer is full and triggers a flush.
                          Default: 32 records (32 * 128 B = 4,096 B = 4 KiB page).
        record_size_bytes: Size of each record in bytes (default 128).
        page_size_bytes: Target flash page size in bytes (default 4096).
        count: Number of uncommitted records currently held in RAM.
        total_flushes: Count of full page flushes performed.
        total_records_pushed: Total number of records submitted by host.
    """

    def __init__(
        self,
        flash_sim: FlashSimulator,
        capacity_records: int = 32,
        record_size_bytes: int = 128,
        page_size_bytes: int = 4096,
        max_logical_pages: int = 1024,
    ) -> None:
        self.flash_sim = flash_sim
        self.capacity_records = capacity_records
        self.record_size_bytes = record_size_bytes
        self.page_size_bytes = page_size_bytes
        self.max_logical_pages = max_logical_pages

        # Internal buffer slots and circular queue state
        self._buffer: List[Optional[bytes]] = [None] * self.capacity_records
        self._head: int = 0  # Write pointer
        self._tail: int = 0  # Read pointer
        self.count: int = 0  # Active item count

        # Tracking metrics
        self.total_flushes: int = 0
        self.total_records_pushed: int = 0
        self._next_lba: int = 0

    @property
    def is_empty(self) -> bool:
        """True if the buffer holds 0 uncommitted records."""
        return self.count == 0

    @property
    def is_full(self) -> bool:
        """True if the buffer has reached capacity and is ready to flush."""
        return self.count >= self.capacity_records

    @property
    def buffered_bytes(self) -> int:
        """Total number of unwritten dirty bytes currently sitting in volatile RAM.
        
        This metric directly quantifies data at risk under sudden power loss.
        """
        return self.count * self.record_size_bytes

    def push(
        self,
        record: bytes,
        lba: Optional[int] = None,
    ) -> Optional[Tuple[int, int]]:
        """Append a record into the ring buffer.
        
        If the buffer reaches capacity (e.g., 32 records = 4 KiB), an automatic
        flush() is triggered immediately to write a full page to FlashSimulator.
        
        Args:
            record: Data bytes for the record (padded or truncated to record_size_bytes).
            lba: Optional target LBA to write to upon flushing. If None, round-robin LBA is used.
            
        Returns:
            Physical coordinate (block_idx, page_idx) if an automatic flush occurred,
            or None if the record was held in RAM.
        """
        # Ensure exact record size
        if len(record) < self.record_size_bytes:
            padded_record = record.ljust(self.record_size_bytes, b"\x00")
        else:
            padded_record = record[: self.record_size_bytes]

        self._buffer[self._head] = padded_record
        self._head = (self._head + 1) % self.capacity_records
        self.count += 1
        self.total_records_pushed += 1

        if self.is_full:
            return self.flush(target_lba=lba)

        return None

    def flush(self, target_lba: Optional[int] = None) -> Optional[Tuple[int, int]]:
        """Pack all uncommitted records into a 4 KiB page and write to flash.
        
        Args:
            target_lba: Target LBA for the flushed page. If None, assigns
                        sequential LBA within max_logical_pages.
                        
        Returns:
            Physical coordinate (block_idx, page_idx) if flushed, or None if buffer was empty.
        """
        if self.is_empty:
            return None

        # Drain uncommitted records in FIFO order
        drained_records: List[bytes] = []
        while self.count > 0:
            rec = self._buffer[self._tail]
            assert rec is not None
            drained_records.append(rec)
            self._buffer[self._tail] = None
            self._tail = (self._tail + 1) % self.capacity_records
            self.count -= 1

        # Reset pointers
        self._head = 0
        self._tail = 0

        # Pack into full page payload (4096 bytes)
        payload = b"".join(drained_records)
        if len(payload) < self.page_size_bytes:
            payload = payload.ljust(self.page_size_bytes, b"\x00")

        # Determine target LBA
        if target_lba is not None:
            lba_to_write = target_lba
        else:
            lba_to_write = self._next_lba
            self._next_lba = (self._next_lba + 1) % self.max_logical_pages

        coord = self.flash_sim.write_logical_page(lba=lba_to_write, data=payload)
        self.total_flushes += 1
        return coord

    def get_buffered_records(self) -> List[bytes]:
        """Return a copy of records currently queued in volatile memory without removing them."""
        records: List[bytes] = []
        idx = self._tail
        for _ in range(self.count):
            rec = self._buffer[idx]
            if rec is not None:
                records.append(rec)
            idx = (idx + 1) % self.capacity_records
        return records

    def clear(self) -> int:
        """Drop all uncommitted in-flight buffer data (simulates sudden power cut).
        
        Returns:
            Number of uncommitted bytes lost.
        """
        lost_bytes = self.buffered_bytes
        self._buffer = [None] * self.capacity_records
        self._head = 0
        self._tail = 0
        self.count = 0
        return lost_bytes

    def __repr__(self) -> str:
        return (
            f"RingBuffer(records={self.count}/{self.capacity_records}, "
            f"buffered_bytes={self.buffered_bytes}B, "
            f"total_flushes={self.total_flushes}, "
            f"records_pushed={self.total_records_pushed})"
        )

