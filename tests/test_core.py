import datetime
import decimal
import uuid

import pytest
from celery import Celery
from kombu.exceptions import EncodeError

import celery_typed_tasks.core
from example import Dog
from example import all_objs_task

now = datetime.datetime.now()


def DogFactory(name, dob=None):
    if dob is None:
        dob = datetime.datetime.now()
    return Dog(name=name, dob=dob)


class TestSerde:
    @pytest.mark.parametrize(
        "obj, value",
        dict(
            none_obj=None,
            uuid_obj=uuid.uuid4(),
            decimal_obj=decimal.Decimal(1),
            datetime_obj=datetime.datetime(year=2022, month=1, day=20),
            date_obj=datetime.date(year=2022, month=1, day=20),
            time_obj=datetime.time(hour=1, minute=1, second=1),
            dict_obj={"hello": "world!"},
            int_obj=1,
            str_obj="hello world!",
            bool_obj=True,
            float_obj=3.14,
        ).items(),
    )
    def test_with_kwargs(self, mocker, obj, value):
        load_obj_spy = mocker.spy(celery_typed_tasks.core.TypedTask, "_load_obj")
        dump_obj_spy = mocker.spy(celery_typed_tasks.core.TypedTask, "_dump_obj")
        kwargs = {}
        kwargs[obj] = value
        all_objs = all_objs_task.delay(**kwargs).get()
        assert all_objs[obj] == value
        assert load_obj_spy.call_count == 1
        assert dump_obj_spy.call_count == 1

    @pytest.mark.parametrize(
        "obj, value",
        dict(
            dataclass_obj=DogFactory(name="Bruce"),
        ).items(),
    )
    def test_dataclass_serialization(self, mocker, obj, value):
        load_obj_spy = mocker.spy(celery_typed_tasks.core.TypedTask, "_load_obj")
        dump_obj_spy = mocker.spy(celery_typed_tasks.core.TypedTask, "_dump_obj")
        kwargs = {}
        kwargs[obj] = value
        all_objs = all_objs_task.delay(**kwargs).get()
        assert all_objs[obj] == value
        # 1 to get the whole payload
        # 2 for deserializing the 2 fields on the Dog class
        # 3 total
        assert load_obj_spy.call_count == 3
        assert dump_obj_spy.call_count == 3

    @pytest.mark.parametrize(
        "obj, value",
        dict(
            list_obj=[DogFactory(name="Bruce"), DogFactory(name="Gus")],
        ).items(),
    )
    def test_list_with_complex_types(self, mocker, obj, value):
        load_obj_spy = mocker.spy(celery_typed_tasks.core.TypedTask, "_load_obj")
        dump_obj_spy = mocker.spy(celery_typed_tasks.core.TypedTask, "_dump_obj")
        kwargs = {}
        kwargs[obj] = value
        all_objs = all_objs_task.delay(**kwargs).get()
        assert all_objs[obj] == value
        # 1 to get the whole payload
        # 3 for each dog
        #   1 for the dog obj
        #   2 for each field
        # 7 total
        assert load_obj_spy.call_count == 7
        assert dump_obj_spy.call_count == 7

    @pytest.mark.parametrize(
        "obj, value",
        dict(
            naive_set_obj={1, 2, 3}, literal_set_obj={1, 2, 3}, naive_list_obj=[1, 2, 3]
        ).items(),
    )
    def test_naive_objs(self, mocker, obj, value):
        load_obj_spy = mocker.spy(celery_typed_tasks.core.TypedTask, "_load_obj")
        dump_obj_spy = mocker.spy(celery_typed_tasks.core.TypedTask, "_dump_obj")
        kwargs = {}
        kwargs[obj] = value
        all_objs = all_objs_task.delay(**kwargs).get()
        assert all_objs[obj] == value
        assert load_obj_spy.call_count == 1
        assert dump_obj_spy.call_count == 1

    @pytest.mark.parametrize(
        "obj, value",
        dict(
            set_obj={datetime.datetime(2020, 6, 6), datetime.datetime(2022, 1, 1)},
        ).items(),
    )
    def test_set_with_complex_types(self, mocker, obj, value):
        load_obj_spy = mocker.spy(celery_typed_tasks.core.TypedTask, "_load_obj")
        dump_obj_spy = mocker.spy(celery_typed_tasks.core.TypedTask, "_dump_obj")
        kwargs = {}
        kwargs[obj] = value
        all_objs = all_objs_task.delay(**kwargs).get()
        assert all_objs[obj] == value
        # 1 to get the whole payload
        # 2 for deserializing each set item in the list and set
        # 3 total
        assert load_obj_spy.call_count == 3
        assert dump_obj_spy.call_count == 3


class TestAllObjsTypeHintSerializationDisabled:
    @pytest.mark.parametrize(
        "obj, value",
        dict(
            datetime_obj=datetime.datetime(year=2022, month=1, day=20),
            time_obj=datetime.time(hour=1, minute=1, second=1),
        ).items(),
    )
    def test_datetime_objs(self, type_hint_serialization_disabled_task, obj, value):
        kwargs = {}
        kwargs[obj] = value
        all_objs = type_hint_serialization_disabled_task.delay(**kwargs).get()
        assert all_objs[obj] == value.isoformat()

    @pytest.mark.parametrize(
        "obj, value",
        dict(
            uuid_obj=uuid.uuid4(),
            decimal_obj=decimal.Decimal(1),
        ).items(),
    )
    def test_textual_objs(self, type_hint_serialization_disabled_task, obj, value):
        kwargs = {}
        kwargs[obj] = value
        all_objs = type_hint_serialization_disabled_task.delay(**kwargs).get()
        assert all_objs[obj] == str(value)

    def test_date_obj(self, type_hint_serialization_disabled_task):
        all_objs = type_hint_serialization_disabled_task.delay(
            date_obj=datetime.date(year=2022, month=1, day=20)
        ).get()
        assert (
            all_objs["date_obj"]
            == datetime.datetime(year=2022, month=1, day=20).isoformat()
        )

    @pytest.mark.parametrize(
        "obj, value",
        dict(
            set_obj={1, 2, 3},
            dataclass_obj=Dog(name="Bruce", dob=datetime.datetime.now()),
        ).items(),
    )
    def test_encoding_error_objs(
        self, type_hint_serialization_disabled_task, obj, value
    ):
        kwargs = {}
        kwargs[obj] = value
        with pytest.raises(EncodeError):
            all_objs = type_hint_serialization_disabled_task.delay(**kwargs).get()

    @pytest.mark.parametrize(
        "obj, value",
        dict(
            none_obj=None,
            dict_obj={"hello": "world!"},
            list_obj=[1, 2, 3],
            int_obj=1,
            str_obj="hello world!",
            bool_obj=True,
            float_obj=3.14,
        ).items(),
    )
    def test_serializable_objs(self, type_hint_serialization_disabled_task, obj, value):
        kwargs = {}
        kwargs[obj] = value
        all_objs = type_hint_serialization_disabled_task.delay(**kwargs).get()
        assert all_objs[obj] == value


class TestWithNoHints:
    def test_no_hint_args(self, test_app):
        @test_app.task()
        def args(id):
            return id

        id = uuid.uuid4()
        assert args.delay(id).get() == str(id)

    def test_no_hint_positional_kwargs(self, test_app):
        @test_app.task
        def kwargs(id=None):
            return id

        id = uuid.uuid4()
        assert kwargs.delay(id).get() == str(id)

    def test_no_hint_kwargs(self, test_app):
        @test_app.task
        def kwargs(id=None):
            return id

        id = uuid.uuid4()
        assert kwargs.delay(id=id).get() == str(id)

    def test_no_hint_kwarg_default(self, test_app):
        @test_app.task
        def kwargs(id=None):
            return id

        id = uuid.uuid4()
        assert kwargs.delay().get() is None


class TestWithHintedArgsAndKwargs:
    def test_no_args_kwargs(self, test_app):
        @test_app.task
        def no_args_kwargs() -> str:
            return "Success"

        assert no_args_kwargs.delay().get() == "Success"

    def test_args(self, test_app):
        @test_app.task
        def args(id: uuid.UUID):
            return id

        id = uuid.uuid4()
        assert args.delay(id).get() == id

    def test_kwargs(self, test_app):
        @test_app.task
        def kwargs(id: uuid.UUID = None, now: datetime = "lol"):
            return id

        id = uuid.uuid4()
        assert kwargs.delay(id=id).get() == id

    def test_kwargs_passed_in_positionally(self, test_app):
        @test_app.task
        def positional_kwargs(id: uuid.UUID = None, now: datetime.datetime = None):
            return id, now

        id = uuid.uuid4()
        now = datetime.datetime.now()
        assert positional_kwargs.delay(id, now=now).get() == (id, now)
        assert positional_kwargs.delay(id).get() == (id, None)

    def test_keyword_only(self, test_app):
        @test_app.task
        def args(*, id: uuid.UUID):
            return id

        id = uuid.uuid4()
        assert args.delay(id=id).get() == id

    # This does not work with python 3.7 and breaks pytest ast code
    # def test_positional_only(self, test_app):
    #     @test_app.task
    #     def args(id: uuid.UUID, /):
    #         return id
    #
    #     id = uuid.uuid4()
    #     assert args.delay(id).get() == id


def test_with_task_type_hint_serialization_setting_false():
    app = Celery(
        "no-type-hint-serialization",
        broker="pyamqp://guest@localhost//",
        task_cls=celery_typed_tasks.core.TypedTask,
    )

    class Config:
        task_always_eager = True
        task_type_hint_serialization = False

    app.config_from_object(Config)

    @app.task
    def no_type_hint_serialization(id: uuid.UUID):
        return {"id": id}

    @app.task(type_hint_serialization=True)
    def type_hint_serialization(id: uuid.UUID):
        return {"id": id}

    id = uuid.uuid4()
    assert no_type_hint_serialization.delay(id=id).get() == {"id": str(id)}
    assert type_hint_serialization.delay(id=id).get() == {"id": id}
