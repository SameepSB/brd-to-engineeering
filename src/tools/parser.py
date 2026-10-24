from src.ingestion.parser import parse_brd
from src.tools.contracts import ParseRequest, ParseResponse


def parse_request(request: ParseRequest) -> ParseResponse:
    normalized, uncertainties = parse_brd(request.content, request.filename)
    return ParseResponse(
        brd=normalized,
        uncertainties=uncertainties,
    )
