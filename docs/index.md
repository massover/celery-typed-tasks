# Introduction

[![codecov](https://codecov.io/gh/massover/celery-typed-tasks/branch/main/graph/badge.svg?token=IQN4K3GMAJ)](https://codecov.io/gh/massover/celery-typed-tasks)
[![PyPI version](https://badge.fury.io/py/celery-typed-tasks.svg)](https://badge.fury.io/py/celery-typed-tasks)

Celery Typed Tasks provides argument serialization for complex objects using [type hints](https://docs.python.org/3/library/typing.html).

## Requirements

- Python 3.7+
- Celery 5+

## Installation

```bash
pip install celery-typed-tasks
```

## Example

```python
from celery import Celery
from datetime import datetime
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

Run the application

```bash
celery -A example worker --loglevel=INFO
```

Then trigger some tasks in the REPL

```python
from datetime import datetime

alert.delay(timestamp=datetime(year=2022, month=1, day=1, hour=10))
alert.delay(timestamp=datetime(year=2022, month=1, day=1, hour=20))
```

In the worker logs, you should see

```
...
[2022-02-18 14:38:52,444: WARNING/ForkPoolWorker-8] Send a slack alert
...
[2022-02-18 14:39:16,927: WARNING/ForkPoolWorker-8] I'll deal with it tomorrow
...
```

If your next thought is

> I don't understand what this is doing. Isn't that what celery does?

Remove the `celery_typed_tasks.TypedTask` from the application initialization and re-run the code.

```python
app = Celery(
    "example",
    broker="pyamqp://guest@localhost//",
)
```

---
**Note**

Don't forget to restart your worker.

---

Run the tasks.

```python
from datetime import datetime

alert.delay(timestamp=datetime(year=2022, month=1, day=1, hour=10))
alert.delay(timestamp=datetime(year=2022, month=1, day=1, hour=20))
```

In the worker logs, you should see errors.

```
[2022-02-18 14:45:42,265: ERROR/ForkPoolWorker-8] Task example.alert[70b5fa16-bf0a-4a36-8b08-d6b575cecc13] raised unexpected: AttributeError("'str' object has no attribute 'hour'")
Traceback (most recent call last):
  File "/.../celery-typed-tasks-OhbqpMnr-py3.9/lib/python3.9/site-packages/celery/app/trace.py", line 451, in trace_task
    R = retval = fun(*args, **kwargs)
  File "/.../celery-typed-tasks-OhbqpMnr-py3.9/lib/python3.9/site-packages/celery/app/trace.py", line 734, in __protected_call__
    return self.run(*args, **kwargs)
  File "/.../celery-typed-tasks/example.py", line 79, in alert
    if 9 < timestamp.hour < 17:
AttributeError: 'str' object has no attribute 'hour'
```

## Summary

With type hints, we can have a secure, cross language solution and get complex arguments passed to our tasks. 
This package tries to bring run time type hinting meta programming that is becoming popular 
with libraries like [fastapi](https://fastapi.tiangolo.com/) to Celery. With the type hints that you use with your
tasks already, we can prevent some common serialization errors and build more things on top of task introspection.

## A note about pickle

By default, celery uses [json serialization](https://docs.celeryproject.org/en/stable/userguide/calling.html?highlight=json%20serialization#serializers) for task arguments.
A keen reader might say `just switch to pickle`!

```python 
app = Celery(
    "example",
    broker="pyamqp://guest@localhost//",
)

class Config:
    task_serializer = "pickle"
    accept_content = ["pickle", ]

app.config_from_object(Config)
```

While it fixes the issue, the architecture is open to [security concerns](https://docs.celeryproject.org/en/stable/userguide/security.html#guide-security) and it's limited to python producers only.
With just type hints that you're already using, we can have the robust object serialization our code needs with a secure data format over the wire.
