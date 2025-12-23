# app/arbormind/learning/signal_extractor.py
"""
ArborMind Signal Extractor - Dumb Tokenization Only

REQUIREMENT 4: Signal Extraction Without Interpretation

This module extracts ATOMIC SIGNALS from raw failure data.

Rules:
- No LLM
- No heuristics with intent
- No collapsing
- No summarization
- If a human would argue about it → it's illegal

Signals must be:
- Small
- Countable
- Repeatable

INVARIANT: This module must be purely mechanical.
INVARIANT: Same input ALWAYS produces same output.
INVARIANT: No interpretation, only tokenization.
"""

import re
import hashlib
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple
from enum import Enum, unique


@unique
class SignalType(Enum):
    """
    Types of atomic signals that can be extracted.
    
    Each type has exactly one extraction rule.
    """
    # Error message tokens
    ERROR_TOKEN = "error_token"
    
    # File path mentioned
    FILE_PATH = "file_path"
    
    # Line number mentioned
    LINE_NUMBER = "line_number"
    
    # Python exception type
    EXCEPTION_TYPE = "exception_type"
    
    # Missing identifier (variable, function, class)
    MISSING_IDENTIFIER = "missing_identifier"
    
    # Expected vs actual type mismatch
    TYPE_MISMATCH = "type_mismatch"
    
    # Import that failed
    FAILED_IMPORT = "failed_import"
    
    # HTTP status code
    HTTP_STATUS = "http_status"
    
    # Timeout value
    TIMEOUT_VALUE = "timeout_value"
    
    # File diff line (added/removed)
    DIFF_LINE = "diff_line"


@dataclass(frozen=True)
class AtomicSignal:
    """
    A single, atomic, immutable signal.
    
    Properties:
    - Hashable (can be counted)
    - Immutable (frozen dataclass)
    - Small (just type + value + optional context)
    """
    signal_type: SignalType
    value: str
    context: Optional[str] = None  # e.g., filename for line number
    
    def __hash__(self):
        return hash((self.signal_type, self.value, self.context))
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "type": self.signal_type.value,
            "value": self.value,
            "context": self.context,
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "AtomicSignal":
        """Reconstruct from dict."""
        return cls(
            signal_type=SignalType(d["type"]),
            value=d["value"],
            context=d.get("context"),
        )


@dataclass
class SignalExtractionResult:
    """
    Result of signal extraction.
    
    Contains:
    - List of atomic signals (ordered by extraction)
    - Deduped set for counting
    - Hash of the input for reproducibility check
    """
    signals: List[AtomicSignal] = field(default_factory=list)
    input_hash: str = ""
    
    @property
    def unique_signals(self) -> Set[AtomicSignal]:
        """Get deduplicated set of signals."""
        return set(self.signals)
    
    @property
    def signal_count(self) -> int:
        """Total signals extracted (including duplicates)."""
        return len(self.signals)
    
    @property
    def unique_count(self) -> int:
        """Unique signals extracted."""
        return len(self.unique_signals)
    
    def to_list(self) -> List[dict]:
        """Convert all signals to JSON-serializable list."""
        return [s.to_dict() for s in self.signals]


class SignalExtractor:
    """
    Dumb signal extractor.
    
    No heuristics. No interpretation. Just pattern matching.
    
    Same input → same output. Always.
    """
    
    # ═══════════════════════════════════════════════════════════════════════════
    # REGEX PATTERNS - Mechanical, no interpretation
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Python exception type: "TypeError:", "ValueError:", etc.
    EXCEPTION_PATTERN = re.compile(r"\b([A-Z][a-zA-Z]*(?:Error|Exception|Warning))\b")
    
    # File path: /path/to/file.py or C:\path\to\file.py
    FILE_PATH_PATTERN = re.compile(
        r"(?:[A-Za-z]:\\|/)?(?:[\w\-\.]+[/\\])+[\w\-\.]+\.\w+"
    )
    
    # Line number: "line 42", "Line: 42", ":42:"
    LINE_NUMBER_PATTERN = re.compile(r"(?:line\s*:?\s*|:)(\d+)(?::|,|\s|$)", re.IGNORECASE)
    
    # Missing identifier: "name 'foo' is not defined", "undefined variable 'bar'"
    MISSING_IDENT_PATTERN = re.compile(
        r"(?:name|variable|identifier)\s+['\"]?(\w+)['\"]?\s+(?:is\s+)?(?:not\s+)?(?:defined|found)",
        re.IGNORECASE
    )
    
    # Failed import: "No module named 'foo'", "cannot import 'bar'"
    FAILED_IMPORT_PATTERN = re.compile(
        r"(?:no\s+module\s+named|cannot\s+import\s+name?)\s+['\"]?(\w+(?:\.\w+)*)['\"]?",
        re.IGNORECASE
    )
    
    # Type mismatch: "expected str, got int"
    TYPE_MISMATCH_PATTERN = re.compile(
        r"expected\s+(\w+).*?got\s+(\w+)",
        re.IGNORECASE
    )
    
    # HTTP status: "404", "500", "HTTP 403"
    HTTP_STATUS_PATTERN = re.compile(r"\b(?:HTTP\s*)?([4-5]\d{2})\b")
    
    # Timeout: "timeout: 30s", "timed out after 5000ms"
    TIMEOUT_PATTERN = re.compile(r"(?:timeout|timed?\s*out).*?(\d+)\s*(s|ms|seconds?|milliseconds?)?", re.IGNORECASE)
    
    # Diff lines: "+added line", "-removed line"
    DIFF_LINE_PATTERN = re.compile(r"^([+-])(.+)$", re.MULTILINE)
    
    def extract_from_error(self, error_text: str) -> SignalExtractionResult:
        """
        Extract signals from an error message.
        
        Pure function: same input → same output.
        """
        if not error_text:
            return SignalExtractionResult(signals=[], input_hash="")
        
        # Compute input hash for reproducibility verification
        input_hash = hashlib.sha256(error_text.encode("utf-8")).hexdigest()[:16]
        
        signals: List[AtomicSignal] = []
        
        # Extract exception types
        for match in self.EXCEPTION_PATTERN.finditer(error_text):
            signals.append(AtomicSignal(
                signal_type=SignalType.EXCEPTION_TYPE,
                value=match.group(1),
            ))
        
        # Extract file paths
        for match in self.FILE_PATH_PATTERN.finditer(error_text):
            signals.append(AtomicSignal(
                signal_type=SignalType.FILE_PATH,
                value=match.group(0),
            ))
        
        # Extract line numbers (with context of nearby file if found)
        file_paths = self.FILE_PATH_PATTERN.findall(error_text)
        for match in self.LINE_NUMBER_PATTERN.finditer(error_text):
            # Find the closest preceding file path
            context = None
            match_start = match.start()
            for fp_match in self.FILE_PATH_PATTERN.finditer(error_text):
                if fp_match.end() < match_start:
                    context = fp_match.group(0)
            
            signals.append(AtomicSignal(
                signal_type=SignalType.LINE_NUMBER,
                value=match.group(1),
                context=context,
            ))
        
        # Extract missing identifiers
        for match in self.MISSING_IDENT_PATTERN.finditer(error_text):
            signals.append(AtomicSignal(
                signal_type=SignalType.MISSING_IDENTIFIER,
                value=match.group(1),
            ))
        
        # Extract failed imports
        for match in self.FAILED_IMPORT_PATTERN.finditer(error_text):
            signals.append(AtomicSignal(
                signal_type=SignalType.FAILED_IMPORT,
                value=match.group(1),
            ))
        
        # Extract type mismatches
        for match in self.TYPE_MISMATCH_PATTERN.finditer(error_text):
            signals.append(AtomicSignal(
                signal_type=SignalType.TYPE_MISMATCH,
                value=f"{match.group(1)}→{match.group(2)}",
            ))
        
        # Extract HTTP status codes
        for match in self.HTTP_STATUS_PATTERN.finditer(error_text):
            signals.append(AtomicSignal(
                signal_type=SignalType.HTTP_STATUS,
                value=match.group(1),
            ))
        
        # Extract timeout values
        for match in self.TIMEOUT_PATTERN.finditer(error_text):
            value = match.group(1)
            unit = match.group(2) or "s"
            signals.append(AtomicSignal(
                signal_type=SignalType.TIMEOUT_VALUE,
                value=f"{value}{unit}",
            ))
        
        return SignalExtractionResult(signals=signals, input_hash=input_hash)
    
    def extract_from_diff(self, diff_text: str) -> SignalExtractionResult:
        """
        Extract signals from a file diff.
        
        Only extracts added (+) and removed (-) lines.
        No interpretation of what changed.
        """
        if not diff_text:
            return SignalExtractionResult(signals=[], input_hash="")
        
        input_hash = hashlib.sha256(diff_text.encode("utf-8")).hexdigest()[:16]
        
        signals: List[AtomicSignal] = []
        
        for match in self.DIFF_LINE_PATTERN.finditer(diff_text):
            prefix = match.group(1)
            content = match.group(2).strip()
            
            # Skip empty lines and diff metadata
            if not content or content.startswith("@@") or content.startswith("diff "):
                continue
            
            signals.append(AtomicSignal(
                signal_type=SignalType.DIFF_LINE,
                value=prefix,  # Just "+" or "-"
                context=content[:100],  # Truncate for storage
            ))
        
        return SignalExtractionResult(signals=signals, input_hash=input_hash)
    
    def extract_error_tokens(self, error_text: str, max_tokens: int = 20) -> List[str]:
        """
        Tokenize error message into countable tokens.
        
        Rules:
        - Lowercase
        - Split on whitespace and punctuation
        - Remove pure numbers
        - Remove very short tokens (< 3 chars)
        - Cap at max_tokens
        
        This is the most "dumb" extraction possible.
        """
        if not error_text:
            return []
        
        # Normalize
        text = error_text.lower()
        
        # Split on non-alphanumeric
        tokens = re.split(r"[^a-z0-9_]+", text)
        
        # Filter
        tokens = [
            t for t in tokens
            if len(t) >= 3 and not t.isdigit()
        ]
        
        # Dedupe while preserving order
        seen = set()
        unique_tokens = []
        for t in tokens:
            if t not in seen:
                seen.add(t)
                unique_tokens.append(t)
        
        return unique_tokens[:max_tokens]


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════
_extractor = SignalExtractor()


def extract_signals(error_text: str) -> SignalExtractionResult:
    """Convenience function for error signal extraction."""
    return _extractor.extract_from_error(error_text)


def extract_diff_signals(diff_text: str) -> SignalExtractionResult:
    """Convenience function for diff signal extraction."""
    return _extractor.extract_from_diff(diff_text)


def tokenize_error(error_text: str) -> List[str]:
    """Convenience function for error tokenization."""
    return _extractor.extract_error_tokens(error_text)
