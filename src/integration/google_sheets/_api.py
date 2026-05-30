from typing import TYPE_CHECKING

from aiogoogle import Aiogoogle
from aiogoogle.auth.creds import ServiceAccountCreds

from ._utils import get_service_account_creds_with_path

if TYPE_CHECKING:
    from pathlib import Path

    from aiogoogle.resource import Resource


class GoogleSheetsApiClient:

    """
    Класс для взаимодействия c Google Sheets посредством API Google и библиотеки aiogoogle.
    Создано на основе: https://github.com/omarryhan/aiogoogle/blob/3dc48d7a4a0da4c02b8bb21e82282a7b03a86c55/examples/google_sheets_client.py
    """

    scopes = ("https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive")

    def __init__(self, service_account_path: Path, spreadsheet_id: str):
        service_account_creds = get_service_account_creds_with_path(service_account_path)
        creds = ServiceAccountCreds(scopes=self.scopes, **service_account_creds)
        self._aiogoogle = Aiogoogle(service_account_creds=creds)
        self._spreadsheet_id = spreadsheet_id
        self._sheets_service: Resource | None = None

    async def connect(self) -> None:
        async with self._aiogoogle as aiogoogle:
            self._sheets_service = (await aiogoogle.discover("sheets", "v4")).spreadsheets

    async def _send_request(self, request):
        async with self._aiogoogle as aiogoogle:
            return await aiogoogle.as_service_account(request)

    @property
    def sheets_service(self) -> Resource:
        if hasattr(self, "_sheets_service"):
            return self._sheets_service
        msg = "SheetsApiClient not connected!"
        raise ConnectionError(msg)

    async def get_values(self, sheet_range: str) -> list[str | None]:
        """Получить значения по диапазону. Пример диапазонов: 'List!A1' или 'List!A1:A2'"""
        request = self.sheets_service.values.get(spreadsheetId=self._spreadsheet_id, range=sheet_range)
        resp: dict = await self._send_request(request)
        values = []
        if resp.get("values"):
            values = resp["values"].pop()
        return values

    async def batch_get_values(self, sheet_ranges: list[str]) -> list[list[str]]:
        """Получить значения по группе диапазонов. Пример диапазона: ['List!A1', 'List!B1:B2']"""
        request = self.sheets_service.values.batchGet(spreadsheetId=self._spreadsheet_id, ranges=sheet_ranges)
        resp: dict = await self._send_request(request)
        return [r.get("values", [[]])[0] for r in resp.get("valueRanges")]

    async def update_values(self, sheet_range: str, values: list[str], range_type: str = "ROWS") -> None:
        body = {"values": [[value] for value in values], "majorDimension": range_type}
        request = self.sheets_service.values.update(
            spreadsheetId=self._spreadsheet_id, range=sheet_range,
            valueInputOption="USER_ENTERED", json=body
        )
        await self._send_request(request)

    async def batch_update_values(self, sheet_ranges: list[str], values: list[list[str]]) -> None:
        body = {
            "valueInputOption": "USER_ENTERED",
            "data": [{"range": r, "values": [v]} for r, v in zip(sheet_ranges, values, strict=False)]
        }
        request = self.sheets_service.values.batchUpdate(spreadsheetId=self._spreadsheet_id, json=body)
        await self._send_request(request)



