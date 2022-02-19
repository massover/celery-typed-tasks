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

    def issubclass(
        self, x: typing.Any, A_tuple: typing.Union[typing.Any, typing.Tuple]
    ) -> bool:
        """
        1. Allows check for subclass types
        2. Handles an error case on GenericAlias

        >>> issubclass("123", str)
            Traceback (most recent call last):
              File "<stdin>", line 1, in <module>
            TypeError: issubclass() arg 1 must be a class
        """
        try:
            return issubclass(x, A_tuple)
        except TypeError:
            return False

    def get_origin(self, annotation: typing.Any) -> typing.Optional[typing.Any]:
        """
        https://docs.python.org/3.9/library/stdtypes.html?highlight=__origin__#genericalias.__origin__

        All parameterized generics implement special read-only attributes.

        >>> list[int].__origin__
        <class 'list'>
        """
        return getattr(annotation, "__origin__", None)

    def get_args(self, annotation: typing.Any) -> typing.Tuple:
        """
        https://docs.python.org/3.9/library/stdtypes.html?highlight=__origin__#genericalias.__args__

        This attribute is a tuple (possibly of length 1) of generic types passed to the
        original __class_getitem__() of the generic class:
        >>> dict[str, list[int]].__args__
        (<class 'str'>, list[int])
        """
        return getattr(annotation, "__args__", tuple())

    def dump_obj(self, obj: typing.Any, annotation: typing.Any) -> typing.Any:
        args = self.get_args(annotation)
        origin = self.get_origin(annotation)
        if self.issubclass(annotation, uuid.UUID):
            return str(obj)
        elif self.issubclass(annotation, decimal.Decimal):
            return str(obj)
        elif self.issubclass(annotation, datetime.datetime):
            return obj.isoformat()
        elif self.issubclass(annotation, datetime.date):
            return obj.isoformat()
        elif self.issubclass(annotation, datetime.time):
            return obj.isoformat()
        elif self.issubclass(annotation, set):
            return list(obj)
        elif is_dataclass(annotation):
            # Each field could be a complex type itself that requires serialization
            field_types = typing.get_type_hints(annotation)
            return {
                key: self.dump_obj(value, field_types[key])
                for key, value in asdict(obj).items()
            }
        elif self.issubclass(annotation, (dict, list, int, str, bool, float)):
            # pass through normally json serializable structures
            return obj
        elif origin and origin in [list, set]:
            # Each nested object could be a complex type itself that requires serialization
            arg = next(iter(args), None)
            if not args or isinstance(arg, typing.TypeVar):
                # The nested object has no type specified
                # eg. obj: list or obj: typing.List
                if origin is set:
                    return list(obj)
                return obj

            return [self.dump_obj(item, annotation.__args__[0]) for item in obj]
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
        args = self.get_args(annotation)
        origin = self.get_origin(annotation)
        if self.issubclass(annotation, uuid.UUID):
            return uuid.UUID(obj)
        elif self.issubclass(annotation, decimal.Decimal):
            return decimal.Decimal(obj)
        elif self.issubclass(annotation, datetime.datetime):
            return datetime.datetime.fromisoformat(obj)
        elif self.issubclass(annotation, datetime.date):
            return datetime.date.fromisoformat(obj)
        elif self.issubclass(annotation, datetime.time):
            return datetime.time.fromisoformat(obj)
        elif self.issubclass(annotation, set):
            return set(obj)
        elif is_dataclass(annotation):
            # Each field could be a complex type itself that requires deserialization
            field_types = typing.get_type_hints(annotation)
            return annotation(
                **{
                    key: self.load_obj(value, field_types[key])
                    for key, value in obj.items()
                }
            )
        elif self.issubclass(annotation, (dict, list, int, str, bool, float)):
            # pass through normally json serializable structures
            return obj
        elif origin and origin in [list, set]:
            # Each nested object could be a complex type itself that requires deserialization
            arg = next(iter(args), None)
            if isinstance(arg, typing.TypeVar) or arg is None:
                # The nested object has no type specified
                # eg. obj: list or obj: typing.List
                objs = obj
            else:
                objs = (self.load_obj(item, annotation.__args__[0]) for item in obj)
            if annotation.__origin__ == list:
                return list(objs)
            else:
                return set(objs)
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
