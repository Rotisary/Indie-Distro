import requests
from loguru import logger
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


class BaseService:
    """
    A base service class to handle external API requests.
    It takes in a base URL and an optional API key for authorization.
    Provides methods to make GET and POST requests.
    ```
    always wrap in a try-except block when calling methods to handle external api specific errors.
    """

    def __init__(
            self, 
            base_url: str, 
            api_key: str=None,
            *,
            retries: int=3, 
            backoff_factor: float=0.5
        ):
        self.base_url = base_url
        self.api_key = api_key

        self.session = requests.Session()
        retry = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET", "HEAD", "OPTIONS"]),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)      


    def get_headers(self) -> dict:
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


    def post(self, endpoint: str, data: dict, timeout: int=15):
        url = f"{self.base_url}/{endpoint}"
        headers = self.get_headers()
        try:
            response = self.session.post(
                url, headers=headers, json=data, timeout=timeout
            )
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise       
        return response


    def get(self, endpoint: str, params: dict=None, timeout: int=15):
        url = f"{self.base_url}/{endpoint}"
        headers = self.get_headers()
        try:
            response = self.session.get(url, headers=headers, params=params, timeout=timeout)
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise      
        return response


    def delete(self, endpoint: str, timeout: int=15):
        url = f"{self.base_url}/{endpoint}"
        headers = self.get_headers()
        try:
            response = self.session.delete(url, headers=headers, timeout=timeout)
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise      
        return response
