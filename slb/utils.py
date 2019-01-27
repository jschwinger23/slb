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
        if self.netloc.endswith('.tw'):
            cid = 'tw1'
        elif self.netloc.endswith('.co.id'):
            cid = 'id3'
        elif self.netloc.endswith('.co.th'):
            cid = 'th1'
        return cid

    @property
    def port(self):
        return '80' if self.schema == 'http' else '443'


class _UrlType(click.ParamType):
    name = 'URL'

    def convert(self, value, param, ctx):
        if not value.startswith('http'):
            value = 'https://' + value

        _sp = parse.urlsplit(value)
        return URL(*_sp)


UrlType = _UrlType()


@dataclasses.dataclass
class LB:
    env: str
    cid: str
    hostname: str = dataclasses.field(init=False)
    container_id: str = dataclasses.field(init=False)

    def __post_init__(self):
        res = requests.get(
            'https://smm.shopeemobile.com/api/service/get_info',
            params={
                'service_name': f'nginx-lb-{self.env}-{self.cid}',
                'env': self.env,
                'detail': True,
            },
            headers={'TOKEN': os.getenv('SMM_TOKEN')}
        )
        res.raise_for_status()
        rj = res.json()
        task = next(
            t for t in rj[0]['tasks'] if t['idc'] == self.cid and
            t['state'] == 'TASK_RUNNING' and t['id'].endswith('-1')
        )
        self.hostname = task['hostname']
        self.container_id = task['container_id']

    def run(self, command: str):
        return subprocess.check_output(
            f'docker -H {self.hostname}:7070 exec -i mesos-{self.container_id} {command}',
            shell=True
        ).decode()


class NginxConf:

    @classmethod
    def from_file(cls, filename):
        return cls(open(filename).read())

    def __init__(self, conf: str):
        self.conf = conf
        self.nconf = nginx.loads(conf)

    def find_location(self, url: URL) -> nginx.Location:
        server = self.find_server(url)
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
            bind = next(k for k in server.children if k.name == 'listen')
            if url.netloc in server_name.value and url.port in bind.value:
                break
        else:
            raise ValueError('server not found')

        return server

    def format(self):
        p = re.compile(r'^\s*(?:{|},?)\s*$\n', re.M)
        return p.sub('', json.dumps(self.nconf.as_dict, sort_keys=True, indent=4))
