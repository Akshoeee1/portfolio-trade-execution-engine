from pydantic import BaseModel


class LoginUrlResponse(BaseModel):
    broker: str
    login_url: str | None  # None for credential-based brokers (AngelOne, Groww)


class CallbackRequest(BaseModel):
    """
    Generic callback payload. Which fields are required depends on the
    broker's auth shape:
      - zerodha: request_token
      - fyers / upstox: auth_code
      - angelone: client_code, password, totp
      - groww: api_key, totp
    Unused fields for a given broker are simply ignored by that adapter.
    """

    request_token: str | None = None
    auth_code: str | None = None
    client_code: str | None = None
    password: str | None = None
    totp: str | None = None
    api_key: str | None = None


class CallbackResponse(BaseModel):
    broker: str
    connected: bool


class BrokerStatus(BaseModel):
    broker: str
    connected: bool


class HoldingsResponse(BaseModel):
    broker: str
    holdings: list[dict]
