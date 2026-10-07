class SovereignRAGError(Exception):
    """Base exception for SovereignRAG."""
    def __init__(self, message: str = "An error occurred in SovereignRAG"):
        super().__init__(message)
        self.message = message


class DocumentParseError(SovereignRAGError):
    """Raised when a document cannot be parsed or decoded."""
    pass


class EmptyDocumentError(SovereignRAGError):
    """Raised when an ingested document has zero extractable text."""
    pass


class UnsupportedFileTypeError(SovereignRAGError):
    """Raised when an unsupported file extension is provided."""
    pass


class FileTooLargeError(SovereignRAGError):
    """Raised when file or extracted content exceeds maximum allowed limits."""
    pass


class IndexNotReadyError(SovereignRAGError):
    """Raised when the vector index is not ready or uninitialized."""
    pass


class LLMUnavailableError(SovereignRAGError):
    """Raised when the selected LLM provider is offline, unreachable, or missing credentials."""
    pass


class InvalidModeError(SovereignRAGError):
    """Raised when an invalid engine mode is selected."""
    pass


class RedactionFailureError(SovereignRAGError):
    """Raised when PII redaction or restoration fails."""
    pass


class AuditIntegrityError(SovereignRAGError):
    """Raised when audit ledger cryptographic hash integrity verification fails."""
    pass


class SensitiveDataCloudBlockedError(SovereignRAGError):
    """Raised when sensitive data is queried against cloud mode."""
    pass
