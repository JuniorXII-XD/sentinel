from typing import Literal
from ipaddress import ip_address, ip_network
from pydantic import BaseModel, Field, ConfigDict, field_validator

Role = Literal["admin", "analyst"]
Severity = Literal["low", "medium", "high", "critical"]
Status = Literal["open", "investigating", "resolved"]
Scope = Literal["live", "demo"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(StrictModel):
    username: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize(cls, value):
        return value.lower()


class NewUser(Login):
    password: str = Field(min_length=12, max_length=128)
    role: Role = "analyst"


class UserChange(StrictModel):
    role: Role
    is_active: bool


class AlertChange(StrictModel):
    status: Status
    note: str = Field(min_length=1, max_length=2000)
    expected_updated_at: str

    @field_validator("note")
    @classmethod
    def meaningful(cls, value):
        if not value.strip():
            raise ValueError("A note is required")
        return value.strip()


class RuleChange(StrictModel):
    enabled: bool


class DemoEvent(StrictModel):
    source_ip: str
    event_type: Literal["login_failed", "login_success"]
    account: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")

    @field_validator("source_ip")
    @classmethod
    def documentation_ip(cls, value):
        address = ip_address(value)
        if not any(
            address in ip_network(x)
            for x in ["192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24"]
        ):
            raise ValueError("Documentation IP range required")
        return str(address)
