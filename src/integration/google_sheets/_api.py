from __future__ import annotations

from typing import TYPE_CHECKING

from aiogoogle import Aiogoogle
from aiogoogle.auth.creds import ServiceAccountCreds

from telemetry import client_span

if TYPE_CHECKING:
    from aiogoogle.resource import Resource


_GOOGLE_RPC_ATTRIBUTES = {
    "rpc.system": "google.sheets",
    "server.address": "sheets.googleapis.com",
}


class GoogleSheetsApiClient:
    """Async Google Sheets API client."""

    scopes = (
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    )

    def __init__(self, service_account_creds: dict[str, str], spreadsheet_id: str):
        creds = ServiceAccountCreds(scopes=self.scopes, **service_account_creds)
        self._aiogoogle = Aiogoogle(service_account_creds=creds)
        self._spreadsheet_id = spreadsheet_id
        self._sheets_service: Resource | None = None

    async def connect(self) -> None:
        with client_span(
            "google.sheets.connect",
            {**_GOOGLE_RPC_ATTRIBUTES, "rpc.method": "discover"},
        ):
            async with self._aiogoogle as aiogoogle:
                self._sheets_service = (await aiogoogle.discover("sheets", "v4")).spreadsheets

    async def _send_request(self, request):
        async with self._aiogoogle as aiogoogle:
            return await aiogoogle.as_service_account(request)

    @property
    def sheets_service(self) -> Resource:
        if self._sheets_service is None:
            msg = "SheetsApiClient not connected!"
            raise ConnectionError(msg)
        return self._sheets_service

    async def get_values(self, sheet_range: str) -> list[str | None]:
        with client_span(
            "google.sheets.get",
            {**_GOOGLE_RPC_ATTRIBUTES, "rpc.method": "values.get", "sheets.range_count": 1},
        ):
            request = self.sheets_service.values.get(
                spreadsheetId=self._spreadsheet_id, range=sheet_range
            )
            resp: dict = await self._send_request(request)
            values = resp.get("values", [])
            return values[-1] if values else []

    async def batch_get_values(self, sheet_ranges: list[str]) -> list[list[str]]:
        with client_span(
            "google.sheets.batch_get",
            {
                **_GOOGLE_RPC_ATTRIBUTES,
                "rpc.method": "values.batchGet",
                "sheets.range_count": len(sheet_ranges),
            },
        ):
            request = self.sheets_service.values.batchGet(
                spreadsheetId=self._spreadsheet_id, ranges=sheet_ranges
            )
            resp: dict = await self._send_request(request)
            return [item.get("values", [[]])[0] for item in resp.get("valueRanges", [])]

    async def update_values(
        self, sheet_range: str, values: list[str], range_type: str = "ROWS"
    ) -> None:
        with client_span(
            "google.sheets.update",
            {
                **_GOOGLE_RPC_ATTRIBUTES,
                "rpc.method": "values.update",
                "sheets.range_count": 1,
                "sheets.value_count": len(values),
            },
        ):
            body = {"values": [[value] for value in values], "majorDimension": range_type}
            request = self.sheets_service.values.update(
                spreadsheetId=self._spreadsheet_id,
                range=sheet_range,
                valueInputOption="USER_ENTERED",
                json=body,
            )
            await self._send_request(request)

    async def batch_update_values(self, sheet_ranges: list[str], values: list[list[str]]) -> None:
        with client_span(
            "google.sheets.batch_update",
            {
                **_GOOGLE_RPC_ATTRIBUTES,
                "rpc.method": "values.batchUpdate",
                "sheets.range_count": len(sheet_ranges),
            },
        ):
            body = {
                "valueInputOption": "USER_ENTERED",
                "data": [
                    {"range": sheet_range, "values": [value]}
                    for sheet_range, value in zip(sheet_ranges, values, strict=False)
                ],
            }
            request = self.sheets_service.values.batchUpdate(
                spreadsheetId=self._spreadsheet_id, json=body
            )
            await self._send_request(request)
