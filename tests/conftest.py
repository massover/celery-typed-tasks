import datetime
import decimal
import uuid

import pytest
from celery import Celery

import celery_typed_tasks
from example import app, CustomObj, Dog


class TestConfig:
    task_always_eager = True


def pytest_configure():
    app.config_from_object(TestConfig)


@pytest.fixture
def test_app():
    app = Celery(
        "no-type-hint-serialization",
        broker="pyamqp://guest@localhost//",
        task_cls=celery_typed_tasks.core.TypedTask,
    )

    class Config:
        task_always_eager = True

    app.config_from_object(Config)
    return app


@pytest.fixture
def type_hint_serialization_disabled_task(test_app):
    NoneType = type(None)

    @test_app.task(type_hint_serialization=False)
    def type_hint_serialization_disabled(
        none_obj: NoneType = None,
        uuid_obj: uuid.UUID = None,
        decimal_obj: decimal.Decimal = None,
        datetime_obj: datetime.datetime = None,
        date_obj: datetime.date = None,
        time_obj: datetime.time = None,
        set_obj: set = None,
        dataclass_obj: Dog = None,
        dict_obj: dict = None,
        list_obj: list = None,
        int_obj: int = None,
        str_obj: str = None,
        bool_obj: bool = None,
        float_obj: float = None,
        dumps_obj: CustomObj = None,
    ) -> dict:
        return {
            "uuid_obj": uuid_obj,
            "decimal_obj": decimal_obj,
            "datetime_obj": datetime_obj,
            "date_obj": date_obj,
            "time_obj": time_obj,
            "set_obj": set_obj,
            "dataclass_obj": dataclass_obj,
            "dict_obj": dict_obj,
            "list_obj": list_obj,
            "int_obj": int_obj,
            "str_obj": str_obj,
            "bool_obj": bool_obj,
            "float_obj": float_obj,
            "none_obj": none_obj,
            "dumps_obj": dumps_obj,
        }

    return type_hint_serialization_disabled
