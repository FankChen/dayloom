import ipaddress
import json
import re
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator
from pydantic import Field, SecretStr, field_validator
from referencing import Registry

from dayloom.schemas import StrictModel


def validate_device_endpoint(value, settings):
    address = value.strip().rstrip("/")
    parsed = urlsplit(address)
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Use a device service URL without credentials, query or fragment.")
    if parsed.port is not None and not 1 <= parsed.port <= 65535:
        raise ValueError("Invalid device service port")
    if parsed.scheme != "https":
        try:
            loopback = (
                parsed.hostname == "localhost" or ipaddress.ip_address(parsed.hostname).is_loopback
            )
        except ValueError:
            loopback = False
        if parsed.scheme != "http" or not loopback:
            raise ValueError(
                "Device services require HTTPS, except on the local loopback interface."
            )
    if address not in {item.rstrip("/") for item in settings.mcp_allowed_servers}:
        raise ValueError("This device service is not enabled on your Dayloom server yet.")
    return address


def validate_tool_arguments(schema, arguments):
    if len(json.dumps(arguments, allow_nan=False)) > 16000:
        raise ValueError("Device tool arguments are too large")
    Draft202012Validator(schema, registry=Registry()).validate(arguments)


class DeviceInput(StrictModel):
    label: str = Field(min_length=1, max_length=100)
    endpoint: str = Field(min_length=1, max_length=500)
    token: SecretStr | None = Field(default=None, max_length=4096)
    tools: list[str] = Field(default_factory=list, max_length=30)
    version: int = Field(default=0, ge=0)

    @field_validator("tools")
    @classmethod
    def tool_names(cls, names):
        if len(set(names)) != len(names) or any(
            not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", name) for name in names
        ):
            raise ValueError("Choose distinct valid device tool names")
        return names


class DeviceDiscoveryInput(StrictModel):
    version: int = Field(ge=1)
    allow_external: bool = False


def device_view(connection):
    return {
        "id": connection.id,
        "label": connection.label,
        "version": connection.version,
        "endpoint": connection.configuration["endpoint"],
        "authorized_tools": connection.configuration.get("tools", []),
        "catalog": list(connection.configuration.get("schemas", {}).values()),
    }
