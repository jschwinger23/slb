import click
from urllib import parse

from .utils import URL


class _UrlType(click.ParamType):
    name = 'URL'

    def convert(self, value, param, ctx):
        if not value.startswith('http'):
            value = 'https://' + value

        _sp = parse.urlsplit(value)
        return URL(*_sp)


UrlType = _UrlType()
