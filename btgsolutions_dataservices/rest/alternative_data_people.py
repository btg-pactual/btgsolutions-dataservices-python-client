from typing import Optional
import requests
from ..exceptions import BadResponse
from ..config import url_api_v1
from .authenticator import Authenticator


class AlternativeDataPeople:
    """
    This class provides people-level alternative data: governance appointments
    for individuals across BR, US, and UK companies.

    * Main use case:

    >>> from btgsolutions_dataservices import AlternativeDataPeople
    >>> people = AlternativeDataPeople(api_key='YOUR_API_KEY')
    >>> people.get_appointments(person_id='slug:Jean Paul Lemann')

    Parameters
    ----------------
    api_key: str
        User identification key.
        Field is required.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.token = Authenticator(self.api_key).token
        self.headers = {"authorization": f"Bearer {self.token}"}

    def _get(self, path: str, params: dict) -> dict:
        url = f"{url_api_v1}/public-sources/{path}"
        params = {k: v for k, v in params.items() if v is not None and v != ""}
        response = requests.get(url, params=params, headers=self.headers, timeout=30)
        if response.status_code != 200:
            self._raise_error(response)
        return response.json()

    @staticmethod
    def _raise_error(response):
        try:
            body = response.json()
            detail = body.get("detail", body.get("error", body.get("ApiClientError", response.text)))
        except Exception:
            detail = response.text
        raise BadResponse(f"Error {response.status_code}: {detail}")

    def get_appointments(
        self,
        person_id: str,
        active_only: bool = False,
        body: Optional[str] = None,
        group_by: Optional[str] = None,
        name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        Governance appointments for a person across BR, US, and UK companies.

        Parameters
        ----------------
        person_id: str
            Person identifier. Accepts CPF, 'slug:name', 'cpf:CPF',
            'uk_officer:id', or SEC CIK.
            Field is required. Example: 'slug:Jean Paul Lemann'.
        active_only: bool
            If True, returns only current active appointments.
            Field is not required. Default: False.
        body: str
            Governance body filter: 'board', 'executive', or 'committee'.
            Field is not required.
        group_by: str
            Group results by 'company'.
            Field is not required.
        name: str
            Name search filter.
            Field is not required.
        limit: int
            Maximum number of results to return.
            Field is not required. Default: 100.
        offset: int
            Number of results to skip for pagination.
            Field is not required. Default: 0.
        """
        return self._get("people/appointments", {
            "person_id": person_id,
            "active_only": active_only,
            "body": body,
            "group_by": group_by,
            "name": name,
            "limit": limit,
            "offset": offset,
        })
