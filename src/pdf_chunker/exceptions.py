class PDFChunkerError(Exception):
    """Base exception for pdf-chunker."""
    pass


class PDFAccessError(PDFChunkerError):
    """Raised when a PDF cannot be accessed (password-protected, permissions)."""
    def __init__(self, path, reason):
        self.path = path
        self.reason = reason
        super().__init__(f"Cannot access {path}: {reason}")


class PDFParseError(PDFChunkerError):
    """Raised when a PDF cannot be parsed (corrupted, invalid format)."""
    def __init__(self, path, reason):
        self.path = path
        self.reason = reason
        super().__init__(f"Cannot parse {path}: {reason}")
