"""Storage Data Structures and State Model for Flash Memory Simulation.

This module defines the basic physical storage units of NAND Flash:
- PageState: The discrete lifecycle states of a flash page (free, valid, invalid).
- Page: The fundamental unit of reading and programming (writing).
- Block: The fundamental unit of erasure, composed of an array of pages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class PageState(str, Enum):
    """Lifecycle states of a physical NAND flash page.
    
    Attributes:
        FREE: The page is cleanly erased and ready to be programmed (written).
              In physical NAND, floating gates are in an uncharged / erased state.
        VALID: The page contains current, active data mapped to a host Logical
               Block Address (LBA).
        INVALID: The page contains stale or superseded data. In NAND flash, cells
                 cannot be overwritten in place; when the host rewrites an LBA,
                 new data is written to a FREE page and the old page becomes INVALID.
                 An INVALID page cannot be written again until the parent Block is erased.
    """
    FREE = "free"
    VALID = "valid"
    INVALID = "invalid"


@dataclass
class Page:
    """Represents a single physical page within a NAND flash block.
    
    A page is the smallest granularity for read and write (program) operations
    (typically 4 KiB in real hardware).
    
    Attributes:
        state: Current PageState ('free', 'valid', or 'invalid'). Defaults to 'free'.
        lba: Logical Block Address (LBA) from the host system currently mapped to
             this physical page. Stored in flash 'Out-Of-Band' (OOB) spare area in real
             hardware for reverse address translation during Garbage Collection.
        data: Arbitrary payload data stored in the page (or None if unwritten).
    """
    state: PageState = PageState.FREE
    lba: Optional[int] = None
    data: Optional[Any] = None

    @property
    def is_free(self) -> bool:
        """Check if the page is free (erased and ready for programming)."""
        return self.state == PageState.FREE

    @property
    def is_valid(self) -> bool:
        """Check if the page holds live, valid host data."""
        return self.state == PageState.VALID

    @property
    def is_invalid(self) -> bool:
        """Check if the page holds obsolete/stale data awaiting erasure."""
        return self.state == PageState.INVALID

    def reset(self) -> None:
        """Physically reset the page state to FREE, clearing metadata and payload.
        
        This occurs only during a block-level erasure.
        """
        self.state = PageState.FREE
        self.lba = None
        self.data = None


@dataclass
class Block:
    """Represents an erase block containing an array of pages.
    
    In NAND flash, while programming occurs at the page level (e.g., 4 KiB),
    erasing can only be performed across an entire block (e.g., 64 pages = 256 KiB).
    
    Attributes:
        block_id: Physical identifier index of the block.
        pages: List of Page objects contained within this block.
        erase_count: Total number of times this block has undergone physical erasure.
                     Tracks Program/Erase (P/E) cycles to model wear and endurance.
    """
    block_id: int
    pages: list[Page] = field(default_factory=list)
    erase_count: int = 0

    @property
    def num_pages(self) -> int:
        """Return total number of pages in this block."""
        return len(self.pages)

    @property
    def free_page_count(self) -> int:
        """Count of pages in FREE state."""
        return sum(1 for p in self.pages if p.is_free)

    @property
    def valid_page_count(self) -> int:
        """Count of pages in VALID state."""
        return sum(1 for p in self.pages if p.is_valid)

    @property
    def invalid_page_count(self) -> int:
        """Count of pages in INVALID state (primary metric for greedy GC victim selection)."""
        return sum(1 for p in self.pages if p.is_invalid)

    def erase(self) -> None:
        """Perform physical block erasure.
        
        Resets all pages to FREE and increments the block's erase counter.
        """
        for page in self.pages:
            page.reset()
        self.erase_count += 1

