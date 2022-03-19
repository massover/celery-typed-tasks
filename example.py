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
    dob: datetime.datetime


NoneType = type(None)


@app.task
def all_objs_task(
    none_obj: NoneType = None,
    uuid_obj: uuid.UUID = None,
    decimal_obj: decimal.Decimal = None,
    datetime_obj: datetime.datetime = None,
    date_obj: datetime.date = None,
    time_obj: datetime.time = None,
    naive_set_obj: typing.Set = None,
    set_obj: typing.Set[datetime.datetime] = None,
    dataclass_obj: Dog = None,
    dict_obj: dict = None,
    naive_list_obj: typing.List = None,
    list_obj: typing.List[Dog] = None,
    literal_set_obj: set = None,
    int_obj: int = None,
    str_obj: str = None,
    bool_obj: bool = None,
    float_obj: float = None,
) -> dict:
    return {
        "uuid_obj": uuid_obj,
        "decimal_obj": decimal_obj,
        "datetime_obj": datetime_obj,
        "date_obj": date_obj,
        "time_obj": time_obj,
        "naive_set_obj": naive_set_obj,
        "literal_set_obj": literal_set_obj,
        "set_obj": set_obj,
        "dataclass_obj": dataclass_obj,
        "dict_obj": dict_obj,
        "list_obj": list_obj,
        "naive_list_obj": naive_list_obj,
        "int_obj": int_obj,
        "str_obj": str_obj,
        "bool_obj": bool_obj,
        "float_obj": float_obj,
        "none_obj": none_obj,
    }


@app.task()
def alert(timestamp: datetime.datetime) -> None:
    if 9 < timestamp.hour < 17:
        print("Send a slack alert")
    else:
        print("I'll deal with it tomorrow")
