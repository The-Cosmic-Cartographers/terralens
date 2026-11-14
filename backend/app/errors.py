"""The doc 04 error format: {"error": {"code", "message", "details"}}."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.models import ErrorBody, ErrorResponse
from app.services.store import DatasetNotFound, DataUnavailable, RegionNotFound


def error_response(
    status_code: int, code: str, message: str, details: dict[str, Any] | None = None
) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message, details=details or {}))
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RegionNotFound)
    async def region_not_found(_: Request, error: RegionNotFound) -> JSONResponse:
        return error_response(
            404,
            "region_not_found",
            f"Unknown region_id '{error.region_id}'",
            {"region_id": error.region_id},
        )

    @app.exception_handler(DatasetNotFound)
    async def dataset_not_found(_: Request, error: DatasetNotFound) -> JSONResponse:
        return error_response(
            404,
            "dataset_not_found",
            f"Unknown dataset_id '{error.dataset_id}'",
            {"dataset_id": error.dataset_id},
        )

    @app.exception_handler(DataUnavailable)
    async def data_unavailable(_: Request, error: DataUnavailable) -> JSONResponse:
        return error_response(
            503,
            "data_unavailable",
            "Processed data is not available yet",
            {"file": error.relative_path, "reason": error.reason},
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_parameter(_: Request, error: RequestValidationError) -> JSONResponse:
        problems = [
            {"parameter": ".".join(str(part) for part in e["loc"][1:]), "problem": e["msg"]}
            for e in error.errors()
        ]
        return error_response(
            422,
            "invalid_parameter",
            "A query parameter is missing or invalid",
            {"errors": problems},
        )
