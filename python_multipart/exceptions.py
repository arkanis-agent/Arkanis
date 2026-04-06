from typing import Optional

class FormParserError(ValueError):
    """Base error class for our form parser."""
    pass


class ParseError(FormParserError):
    """This exception (or a subclass) is raised when there is an error while
    parsing something.
    """

    #: This is the offset in the input data chunk (*NOT* the overall stream) in
    #: which the parse error occurred.  It will be -1 if not specified.
    offset: int = -1

    def __init__(self, message: Optional[str] = None, offset: int = -1) -> None:
        self.offset = offset
        if message is None:
            message = f"Parse error at offset {offset}"
        super().__init__(message)


class MultipartParseError(ParseError):
    """This is a specific error that is raised when the MultipartParser detects
    an error while parsing.
    """
    pass


class QuerystringParseError(ParseError):
    """This is a specific error that is raised when the QuerystringParser
    detects an error while parsing.
    """
    pass


class DecodeError(ParseError):
    """This exception is raised when there is a decoding error - for example
    with the Base64Decoder or QuotedPrintableDecoder.
    """
    pass


class FileError(FormParserError, OSError):
    """Exception class for problems with the File class."""
    pass