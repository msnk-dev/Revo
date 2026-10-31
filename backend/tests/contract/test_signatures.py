import importlib
import inspect
import json
from dataclasses import fields
from pathlib import Path
from typing import get_args, get_origin


SNAPSHOT_PATH = Path(__file__).with_name("signature_snapshot.json")


def _annotation_name(annotation: object) -> str:
    if annotation is inspect.Signature.empty:
        return ""
    if annotation is None or annotation is type(None):
        return "NoneType"
    if inspect.isclass(annotation):
        return annotation.__name__
    origin = get_origin(annotation)
    if origin is not None:
        origin_name = getattr(origin, "__name__", str(origin).rsplit(".", 1)[-1])
        args = get_args(annotation)
        if origin_name == "Callable" and args and args[0] is Ellipsis:
            return f"Callable[..., {_annotation_name(args[-1])}]"
        return f"{origin_name}[{', '.join(_annotation_name(arg) for arg in args)}]"
    return str(annotation).replace("app.schemas.contract.", "")


def _signature_snapshot(target: object) -> dict[str, object]:
    signature = inspect.signature(target)
    parameters = []
    for parameter in signature.parameters.values():
        if parameter.default is inspect.Signature.empty:
            default = "required"
        elif type(parameter.default).__name__ == "Depends":
            default = "Depends"
        else:
            default = repr(parameter.default)
        parameters.append([parameter.kind.name if parameter.kind is not inspect.Parameter.POSITIONAL_OR_KEYWORD else "", parameter.name, default])
    return {"parameters": parameters, "return": _annotation_name(signature.return_annotation)}


def test_frozen_contract_signatures_match_snapshot() -> None:
    expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    for dotted_path, snapshot in expected.items():
        module_name, target_name = dotted_path.rsplit(".", 1)
        target = getattr(importlib.import_module(module_name), target_name)
        if dotted_path == "app.deps.Actor":
            actual = {"fields": [field.name for field in fields(target)]}
        else:
            actual = _signature_snapshot(target)
        assert actual == snapshot, dotted_path

