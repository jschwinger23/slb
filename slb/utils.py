import os
import re
import json
import nginx
import click
import requests
import subprocess
import dataclasses
from urllib import parse


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
        if 'test' in self.netloc or 'uat' in self.netloc or 'staging' in self.netloc:
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


class _UrlType(click.ParamType):
    name = 'URL'

    def convert(self, value, param, ctx):
        if not value.startswith('http'):
            value = 'https://' + value

        _sp = parse.urlsplit(value)
        return URL(*_sp)


UrlType = _UrlType()


class NginxConf:

    @classmethod
    def from_file(cls, filename):
        return cls(open(filename).read())

    def __init__(self, conf: str):
        self.conf = conf
        self.nconf = nginx.loads(conf)

    def find_location(self, url: URL) -> nginx.Location:
        server = self.find_server(url)
        #import pdb; pdb.set_trace()
        location = type('', (), {'value': ''})
        for l in (l for l in server.children if isinstance(l, nginx.Location)):
            if re.match(l.value, url.path or
                        '/') and len(l.value) > len(location.value):
                location = l

        if not location.value:
            raise ValueError('location not found')
        return location

    def find_server(self, url: URL) -> nginx.Server:
        for server in (
            s for s in self.nconf.children if isinstance(s, nginx.Server)
        ):
            server_name = next(
                k for k in server.children if k.name == 'server_name'
            )
            bind = ''.join(
                [
                    k.value
                    for k in server.children
                    if getattr(k, 'name', '') == 'listen'
                ]
            )
            if url.netloc == server_name.value and url.port in bind:
                break
        else:
            raise ValueError('server not found')

        return server

    def format(self):
        jconf = self.nconf.as_dict

        def keyfunc(x):
            if 'server' not in x:
                return sorted(x.keys()), ''
            server_name = next(d for d in x['server'] if 'server_name' in d
                              )['server_name']
            listen = next(d for d in x['server'] if 'listen' in d)['listen']
            return sorted(x.keys()), f'{server_name}:{listen}'

        jconf['conf'].sort(key=keyfunc)
        for c in jconf['conf']:
            for v in c.values():
                if isinstance(v, list):
                    v.sort(key=lambda x: sorted(x.keys()) + sorted(x.values()))
                    for l in v:
                        for d in l.values():
                            if isinstance(d, list):
                                d.sort(key=lambda x: sorted(x.keys()) + sorted(x.values()))

        p = re.compile(r'^\s*(?:{|},?)\s*$\n', re.M)
        return p.sub('', json.dumps(jconf, sort_keys=True, indent=4))


class NginxLocation:
    location: nginx.Location

    @property
    def path(self) -> str:
        return self.location.value

    @property
    def proxy_pass(self) -> str:
        try:
            proxy_pass = next(
                d for d in self.location.children if d.name == 'proxy_pass'
            )
        except StopIteration:
            return ''
        else:
            proxy_pass = re.search('://(.+)', proxy_pass.value).group(1)
            return proxy_pass
