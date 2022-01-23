from __future__ import annotations
import datetime
import decimal
import inspect
import typing
import uuid
from dataclasses import is_dataclass, asdict
import celery
from celery.result import AsyncResult


class TypedTask(celery.Task):
    type_hint_serialization: bool

    def __init__(self, *args, **kwargs) -> None:  # type: ignore
        super().__init__(*args, **kwargs)
        type_hint_serialization = getattr(self, "type_hint_serialization", None)
        if type_hint_serialization is None:
            self.type_hint_serialization = self.app.conf.get(
                "task_type_hint_serialization", True
            )

    def apply_async(self, args=None, kwargs=None, serializer=None, **options) -> AsyncResult:  # type: ignore
        if not self.type_hint_serialization:
            return super().apply_async(args=args, kwargs=kwargs, **options)

        hinted_args = []
        hinted_kwargs = {}
        annotations = self.get_annotations()
        if args:
            args_annotations = list(annotations.values())[: len(args)]
            for arg, annotation in zip(args, args_annotations):
                hinted_args.append(self.dump_obj(arg, annotation))
        if kwargs:
            for key, value in kwargs.items():
                hinted_kwargs[key] = self.dump_obj(value, annotations[key])
        return super().apply_async(
            args=tuple(hinted_args), kwargs=hinted_kwargs, **options
        )

    def get_annotations(self) -> typing.Dict[str, typing.Any]:
        annotations = {}
        for key, value in inspect.signature(self.run).parameters.items():
            annotations[key] = value.annotation
        return annotations

    def dump_obj(self, obj: typing.Any, annotation: typing.Any) -> typing.Any:
        if issubclass(annotation, uuid.UUID):
            return str(obj)
        elif issubclass(annotation, decimal.Decimal):
            return str(obj)
        elif issubclass(annotation, datetime.datetime):
            return obj.isoformat()
        elif issubclass(annotation, datetime.date):
            return obj.isoformat()
        elif issubclass(annotation, datetime.time):
            return obj.isoformat()
        elif issubclass(annotation, set):
            return list(obj)
        elif is_dataclass(annotation):
            return asdict(obj)
        elif issubclass(annotation, (dict, list, int, str, bool, float)):
            # pass through normally json serializable structures
            return obj
        elif annotation is inspect._empty:
            # if type hint serialization is enabled but the type hint is empty,
            # pass the item through as is
            return obj
        elif obj is None:
            # pass through normally json serializable structures
            return obj
        else:
            return obj.dump()

    def load_obj(self, obj: typing.Any, annotation: typing.Any) -> typing.Any:
        if issubclass(annotation, uuid.UUID):
            return uuid.UUID(obj)
        elif issubclass(annotation, decimal.Decimal):
            return decimal.Decimal(obj)
        elif issubclass(annotation, datetime.datetime):
            return datetime.datetime.fromisoformat(obj)
        elif issubclass(annotation, datetime.date):
            return datetime.date.fromisoformat(obj)
        elif issubclass(annotation, datetime.time):
            return datetime.time.fromisoformat(obj)
        elif issubclass(annotation, set):
            return set(obj)
        elif is_dataclass(annotation):
            return annotation(**obj)
        elif issubclass(annotation, (dict, list, int, str, bool, float)):
            # pass through normally json serializable structures
            return obj
        elif annotation is inspect._empty:
            # if type hint serialization is enabled but the type hint is empty,
            # pass the item through as is
            return obj
        elif obj is None:
            # pass through normally json serializable structures
            return obj
        else:
            return annotation.load(obj)

    def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        if not self.type_hint_serialization:
            return super().__call__(*args, **kwargs)

        hinted_args = []
        hinted_kwargs = {}
        annotations = self.get_annotations()
        args_annotations = list(annotations.values())[: len(args)]
        for arg, annotation in zip(args, args_annotations):
            hinted_args.append(self.load_obj(arg, annotation))
        for key, value in kwargs.items():
            hinted_kwargs[key] = self.load_obj(value, annotations[key])
        return super().__call__(*hinted_args, **hinted_kwargs)
