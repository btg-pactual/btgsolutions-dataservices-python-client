import uuid
import requests
import json
import jwt
import time
from ..config import url_apis
from ..exceptions import BadResponse
from .. import __version__

class Authenticator:
    def __init__(self, api_key) -> None:
        self.api_key = api_key

        self._id = uuid.uuid4().hex[:8]
        self._token = self.get_new_token()
        self._expiration = self._get_expiration()

    def get_new_token(self):
        url = f"{url_apis}/authenticate"
        headersList = {
            "Content-Type": "application/json" 
        }
        payload = json.dumps({
            "api_key": self.api_key,
            "client_id": f"btgsolutions-client-python/{__version__}/{self._id}"
        })
        response = requests.request("POST", url, data=payload,  headers=headersList)
        if response.status_code == 200:
            token =  json.loads(response.text).get('AccessToken')
            if not token:
                raise Exception('Something has gone wrong while authenticating: No token as response.')
        else:
            response = json.loads(response.text)
            raise BadResponse(f'Error: {response.get("ApiClientError")}.\n{response.get("SuggestedAction")}')
        
        return token
    
    def _get_expiration(self):
        token_decoded = jwt.decode(self._token, options={"verify_signature": False})
        exp = token_decoded.get("exp")
        return exp

    @property
    def token(self):
        if int(time.time()) - 5 >= self._expiration: ## Subtracting 5 seconds to avoid edge cases of token expiration during request processing.
            self._token = self.get_new_token()
            self._expiration = self._get_expiration()
        
        return self._token
    
