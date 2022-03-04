import datetime
import decimal
import inspect
import typing
import uuid
from dataclasses import asdict
from dataclasses import is_dataclass

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
        annotations = get_annotations(self.run)
        if args:
            args_annotations = list(annotations.values())[: len(args)]
            for arg, annotation in zip(args, args_annotations):
                hinted_args.append(self._dump_obj(arg, annotation))
        if kwargs:
            for key, value in kwargs.items():
                hinted_kwargs[key] = self._dump_obj(value, annotations[key])
        return super().apply_async(
            args=tuple(hinted_args), kwargs=hinted_kwargs, **options
        )

    def dump_obj(self, obj: typing.Any, annotation: typing.Any) -> typing.Any:
        """
        Hook method for custom serialization
        """
        return obj

    def _dump_obj(self, obj: typing.Any, annotation: typing.Any) -> typing.Any:
        """
        Coerce an object into its raw serialized representation using its annotation.
        """
        args = _get_args(annotation)
        origin = _get_origin(annotation)
        if origin and origin in [list, set]:
            # Each nested object could be a complex type itself that requires serialization
            arg = next(iter(args), None)
            if not args or isinstance(arg, typing.TypeVar):
                # The nested object has no type specified
                # eg. obj: list or obj: typing.List
                if origin is set:
                    return list(obj)
                return obj
            return [self._dump_obj(item, args[0]) for item in obj]
        elif issubclass(annotation, uuid.UUID):
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
            # Each field could be a complex type itself that requires serialization
            field_types = typing.get_type_hints(annotation)
            return {
                key: self._dump_obj(value, field_types[key])
                for key, value in asdict(obj).items()
            }
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
            # fall back to any custom serialization if defined
            # or by default `dump_obj` returns the obj passed in
            return self.dump_obj(obj, annotation)

    def load_obj(self, obj: typing.Any, annotation: typing.Any) -> typing.Any:
        """
        Hook method for custom deserialization
        """
        return obj

    def _load_obj(self, obj: typing.Any, annotation: typing.Any) -> typing.Any:
        """
        Coerce a raw object to the object type via its type annotation.
        """
        args = _get_args(annotation)
        origin = _get_origin(annotation)
        if origin and origin in [list, set]:
            # Each nested object could be a complex type itself that requires deserialization
            arg = next(iter(args), None)
            if isinstance(arg, typing.TypeVar) or arg is None:
                # The nested object has no type specified
                # eg. obj: list or obj: typing.List
                objs = obj
            else:
                objs = (self._load_obj(item, annotation.__args__[0]) for item in obj)
            if annotation.__origin__ == list:
                return list(objs)
            else:
                return set(objs)
        elif issubclass(annotation, uuid.UUID):
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
            # Each field could be a complex type itself that requires deserialization
            field_types = typing.get_type_hints(annotation)
            return annotation(
                **{
                    key: self._load_obj(value, field_types[key])
                    for key, value in obj.items()
                }
            )
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
            # fall back to any custom serialization if defined
            # or by default `load_obj` returns the obj passed in
            return self.load_obj(obj, annotation)

    def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        if not self.type_hint_serialization:
            return super().__call__(*args, **kwargs)

        hinted_args = []
        hinted_kwargs = {}
        annotations = get_annotations(self.run)
        args_annotations = list(annotations.values())[: len(args)]
        for arg, annotation in zip(args, args_annotations):
            hinted_args.append(self._load_obj(arg, annotation))
        for key, value in kwargs.items():
            hinted_kwargs[key] = self._load_obj(value, annotations[key])
        return super().__call__(*hinted_args, **hinted_kwargs)


def _get_origin(annotation: typing.Any) -> typing.Optional[typing.Any]:
    """
    https://docs.python.org/3.9/library/stdtypes.html?highlight=__origin__#genericalias.__origin__

    All parameterized generics implement special read-only attributes.

    >>> list[int].__origin__
    <class 'list'>
    """
    return getattr(annotation, "__origin__", None)


def _get_args(annotation: typing.Any) -> typing.Tuple:
    """
    https://docs.python.org/3.9/library/stdtypes.html?highlight=__origin__#genericalias.__args__

    This attribute is a tuple (possibly of length 1) of generic types passed to the
    original __class_getitem__() of the generic class:
    >>> dict[str, list[int]].__args__
    (<class 'str'>, list[int])
    """
    return getattr(annotation, "__args__", tuple())


def get_annotations(fn: typing.Callable) -> typing.Dict[str, typing.Any]:
    annotations = {}
    for key, value in inspect.signature(fn).parameters.items():
        annotations[key] = value.annotation
    return annotations
