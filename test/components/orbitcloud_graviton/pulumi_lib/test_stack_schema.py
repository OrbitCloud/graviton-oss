import json

from pydantic import BaseModel

from orbitcloud_graviton.pulumi_lib.stack_schema import generate_stack_schema


class _EmptyConfig(BaseModel):
    pass


def _schema(tmp_path) -> dict:
    out = tmp_path / "schema.json"
    generate_stack_schema(_EmptyConfig, str(out))
    return json.loads(out.read_text())


def test_secrets_fields_are_optional_root_properties(tmp_path) -> None:
    """secretsprovider and encryptedkey are Pulumi stack-file root keys, exposed
    as optional string fields so stacks that set them pass the extra=forbid check."""
    schema = _schema(tmp_path)
    props = schema["properties"]

    for field in ("secretsprovider", "encryptedkey"):
        assert field in props, f"{field} missing from root schema"
        # Optional string -> string | null with a null default.
        assert {"type": "string"} in props[field]["anyOf"]
        assert {"type": "null"} in props[field]["anyOf"]
        assert props[field]["default"] is None
        assert field not in schema.get("required", [])


def test_only_config_is_required_at_root(tmp_path) -> None:
    schema = _schema(tmp_path)
    assert schema.get("required") == ["config"]
