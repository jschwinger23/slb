import inspect
import dataclasses
from typing import Callable
from functools import singledispatch as _singledispatch


@dataclasses.dataclass
class URL:
    schema: str
    netloc: str
    path: str
    query: str
    fragment: str

    @property
    def env(self):
        env = 'live'
        if '.test.' in self.netloc:
            env = 'test'
        elif '.staging.' in self.netloc or '.uat.' in self.netloc:
            env = 'staging'
        return env

    @property
    def cid(self):
        cid = 'sg'
        if (
            'test' in self.netloc or 'uat' in self.netloc or
            'staging' in self.netloc
        ):
            return cid
        if self.netloc.endswith('.tw'):
            cid = 'tw1'
        elif self.netloc.endswith('.co.id'):
            cid = 'id3'
        elif self.netloc.endswith('.co.th'):
            cid = 'th1'
        return cid

    @property
    def port(self):
        return 80 if self.schema == 'http' else 443


class SingleDispatch:

    def __init__(self, func):
        self.func = _singledispatch(self.exchange_first_two_params(func))

    def __get__(self, instance, owner):

        def bound(arg, *args, **kws):
            return self.func(arg, instance, *args, **kws)

        return bound

    @staticmethod
    def exchange_first_two_params(func):

        def exchanged(arg, self, *args, **kws):
            return func(self, arg, *args, **kws)

        sig = inspect.signature(func)
        second_param = list(sig.parameters.values())[1]
        exchanged.__annotations__ = {'arg': second_param.annotation}
        return exchanged

    def register(self, func):
        self.func.register(self.exchange_first_two_params(func))


class SingleDispatchDict(dict):

    def __setitem__(self, key: str, value: Callable):
        if callable(value):
            dispatch = self.get(key)
            if dispatch:
                dispatch.register(value)
                return

            value = SingleDispatch(value)
        super().__setitem__(key, value)


class SingleDispatchMeta(type):

    @classmethod
    def __prepare__(meta, name, bases):
        return SingleDispatchDict()


class Visitor(metaclass=SingleDispatchMeta):
    pass
