import typing

import kombu.exceptions
import pytest

import celery_typed_tasks


class File:
    url: str

    def __init__(self, url):
        self.url = url


class MyTypedTask(celery_typed_tasks.TypedTask):
    def dump_obj(self, obj: typing.Any, annotation: typing.Any) -> typing.Any:
        if issubclass(annotation, File):
            return obj.url
        return super().dump_obj(obj, annotation)

    def load_obj(self, obj: typing.Any, annotation: typing.Any) -> typing.Any:
        if issubclass(annotation, File):
            return annotation(obj)
        return super().load_obj(obj, annotation)


class TestCustomSerialization:
    def test_dump_api_exists(self):
        obj = object()
        task = MyTypedTask()
        assert task.load_obj(obj, type) == obj

    def test_dump_api_is_used(self):
        obj = object()
        task = MyTypedTask()
        assert task._dump_obj(obj, type) == obj

    def test_load_api_exists(self):
        obj = object()
        task = MyTypedTask()
        assert task.load_obj(obj, type) == obj

    def test_load_api_is_used(self):
        obj = object()
        task = MyTypedTask()
        assert task._load_obj(obj, type) == obj

    def test_with_custom_serialization(self, test_app_factory):
        app = test_app_factory(task_cls=MyTypedTask)

        @app.task()
        def custom_serialization_task(file: File):
            return file.url

        file = File(url="https://example.com/example.jpg")
        assert custom_serialization_task.delay(file=file).get() == file.url

    def test_with_custom_serialization_from_generic(self, test_app_factory):
        app = test_app_factory(task_cls=MyTypedTask)

        @app.task()
        def custom_serialization_task(files: typing.List[File]):
            return [file.url for file in files]

        file = File(url="https://example.com/example.jpg")
        assert custom_serialization_task.delay(files=[file]).get() == [file.url]

    def test_no_custom_serialization_raises_encode_error(self, test_app_factory):
        app = test_app_factory(task_cls=MyTypedTask)

        @app.task(type_hint_serialization=False)
        def custom_serialization_task(file: File):
            return file.url

        file = File(url="https://example.com/example.jpg")
        with pytest.raises(kombu.exceptions.EncodeError):
            custom_serialization_task.delay(file=file).get()
