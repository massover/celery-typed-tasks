# Usage

## TypedTask

### Celery App Initialization

To use celery typed tasks for all tasks in your application, initialize your Celery app with
the `celery_typed_task.TypedTask` task class.

```python
from celery import Celery
import celery_typed_tasks

app = Celery(
    "example",
    broker="pyamqp://guest@localhost//",
    task_cls=celery_typed_tasks.TypedTask,
)

@app.task()
def alert(timestamp: datetime):
    if 9 < timestamp.hour < 17:
        print("Send a slack alert")
    else:
        print("I'll deal with it tomorrow")
```

### Disable type hint serialization

If you need to disable serialization for an individual task, `type_hint_serialization=False` will skip
any custom serialization.

```python
@app.task(type_hint_serialization=False)
def alert(timestamp: datetime | str):
    if timestamp is str:
        timestamp = datetime.fromisoformat(timestamp)
    if 9 < timestamp.hour < 17:
        print("Send a slack alert")
    else:
        print("I'll deal with it tomorrow")
```

### Task with TypedTask base

If you prefer to not set the `TypedTask` as the base task for the entire application,
celery allows customization on a per task basis.

```python
from celery import Celery
import celery_typed_tasks

app = Celery(
    "example",
    broker="pyamqp://guest@localhost//",
)

@app.task(base=celery_typed_task.TypedTask)
def alert(timestamp: datetime):
    if 9 < timestamp.hour < 17:
        print("Send a slack alert")
    else:
        print("I'll deal with it tomorrow")
```

## Argument Types

### Standard Library Types

celery_typed_tasks supports the following standard library types:

- bool
- int
- float
- str
- dict
- set
- list  
- dataclass
- Decimal  
- datetime
- date
- time
- uuid
- None

### Generic Types

celery_typed_tasks supports some generic types.

- list[T]
- set[T]

## Serialization

### Custom object dump and load

To serialize out custom objects, you can use the `dump_obj` and `load_obj` methods
on the task.

```python
import celery_typed_tasks
import typing

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
```

## Celery Configuration

### task_type_hint_serialization

**Default** False

If you need to disable type hint serialization globally for an application that is using `TypedTasks`,
you can set the `task_type_hint_serialization` config setting.

