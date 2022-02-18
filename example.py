import datetime
import decimal
import typing
import uuid
from dataclasses import dataclass

from celery import Celery

import celery_typed_tasks

app = Celery(
    "example",
    broker="pyamqp://guest@localhost//",
    task_cls=celery_typed_tasks.TypedTask,
)


@dataclass
class Dog:
    name: str


class CustomObj:
    def __init__(self, s: str):
        self.s = s

    def dump(self) -> str:
        return self.s

    @classmethod
    def load(cls, s: str) -> "CustomObj":
        return cls(s=s)

    def __eq__(self, other: typing.Any) -> bool:
        return self.s == other.s


NoneType = type(None)


@app.task
def all_objs_task(
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


@app.task()
def alert(timestamp: datetime.datetime) -> None:
    if 9 < timestamp.hour < 17:
        print("Send a slack alert")
    else:
        print("I'll deal with it tomorrow")
