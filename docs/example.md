# Example

## FastAPI

Continuing off the example in the [FastAPI](https://fastapi.tiangolo.com/tutorial/body/) documentation, we can generate
an api for tasks with custom task serialization and a little meta programming.

```python
import typing
from inspect import signature

import pydantic
from celery import Celery
from fastapi import FastAPI
from pydantic import BaseModel

import celery_typed_tasks


class TypedTask(celery_typed_tasks.TypedTask):
    def dump_obj(self, obj: typing.Any, annotation: typing.Any) -> typing.Any:
        if issubclass(annotation, pydantic.BaseModel):
            return obj.dict()
        return super().dump_obj(obj, annotation)

    def load_obj(self, obj: typing.Any, annotation: typing.Any) -> typing.Any:
        if issubclass(annotation, pydantic.BaseModel):
            return annotation(**obj)
        return super().load_obj(obj, annotation)


celery_app = Celery(
    "example",
    broker="pyamqp://guest@localhost//",
    task_cls=TypedTask,
)


class Item(BaseModel):
    name: str
    description: typing.Optional[str] = None
    price: float
    tax: typing.Optional[float] = None


@celery_app.task()
def create_item(item: Item):
    return item


fast_api_app = FastAPI()


def register_task_views(celery_app, fast_api_app):
    for task_name, task in celery_app.tasks.items():
        # Only create api endpoints for tasks defined in the celery_app skip built in celery tasks
        if task_name.startswith("celery"):
            continue

        # The view must be defined in a closure. Otherwise `task` will be passed by reference during the iteration.
        def view_factory(task):
            def task_view(*args, **kwargs):
                task.delay(*args, **kwargs)

            return task_view

        view = view_factory(task)

        # The view acts as proxy but we can copy the signature so fast api can automagically work.
        view.__signature__ = signature(task.run)
        fast_api_app.post(f"/tasks/{task_name}")(view)


register_task_views(celery_app, fast_api_app)
```

