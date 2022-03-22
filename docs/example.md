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

## Django

The following is a single module example of a django and celery application. Since there's no magic
to convert type hints to forms, the meta programming here is incomplete.

```python
import os
import sys

from celery import Celery
from django import forms
from django.conf import settings
from django.core.wsgi import get_wsgi_application
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.template import Context
from django.template import Template
from django.urls import path
from django.utils.crypto import get_random_string
from django.views.generic import RedirectView

import celery_typed_tasks

settings.configure(
    DEBUG=(os.environ.get("DEBUG", "") == "1"),
    ALLOWED_HOSTS=["*"],
    ROOT_URLCONF=__name__,
    SECRET_KEY=get_random_string(50),
    TEMPLATES=[{'BACKEND': 'django.template.backends.django.DjangoTemplates',}],
)


class TaskForm(forms.Form):
    field_lookup = {
        str: forms.CharField(),
        int: forms.IntegerField(),
    }

    def __init__(self, *args, **kwargs):
        task = kwargs.pop("task", None)
        super().__init__(*args, **kwargs)

        for key, annotation in celery_typed_tasks.get_annotations(task.run).items():
            try:
                field = self.field_lookup[annotation]
            except KeyError:
                field = forms.CharField()
            self.fields[key] = field


def register_task_views(celery_app, urlpatterns):
    url_names = []
    for task_name, task in celery_app.tasks.items():
        # Only create api endpoints for tasks defined in the celery_app skip built in celery tasks
        if task_name.startswith("celery"):
            continue

        # The view must be defined in a closure. Otherwise `task` will be passed by reference during the iteration.
        def view_factory(task):
            def task_view(request):
                if request.method == 'POST':
                    form = TaskForm(request.POST, task=task)
                    if form.is_valid():
                        task.delay(**form.cleaned_data)
                        return HttpResponseRedirect(request.path)
                else:
                    form = TaskForm(task=task)

                html = """
                <h1> {{ task_name }} </h1>
                <form method="post">
                {{ form.as_p }}
                <input type="submit" value="Submit">
                </form>
                """
                template = Template(html)
                context = Context({"form": form, "task_name": task.name})
                return HttpResponse(template.render(context))

            return task_view

        view = view_factory(task)
        url_name = f"tasks-{task_name}"
        urlpatterns.append(path(f"tasks/{task_name}", view, name=url_name))
        url_names.append(url_name)

    def task_list_view(request):
        html = """
        <h1>Tasks</h1>
        <ul>
        {% for url_name in url_names %}
            <li><a href="{% url url_name %}">{{ url_name }}</a></li>
        {% endfor %}
        </ul>
        """
        template = Template(html)
        context = Context({"url_names": url_names})
        return HttpResponse(template.render(context))

    urlpatterns.append(path(f"tasks", task_list_view, name="task-list"))


urlpatterns = [
    path("", RedirectView.as_view(pattern_name="task-list")),
]

celery_app = Celery(
    "djangoexample",
    broker="pyamqp://guest@localhost//",
    task_cls=celery_typed_tasks.TypedTask,
)


@celery_app.task
def add(x: int, y: int):
    return x + y


register_task_views(celery_app, urlpatterns)

app = get_wsgi_application()

if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
```

