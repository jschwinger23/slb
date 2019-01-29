import re
import nginx
import dataclasses
from typing import List, Set

from .lb import LB
from ..utils import URL


class Objects:

    def __init__(self, objects):
        self.objects = objects

    def filter(self, **kws) -> List:

        def cond(obj):
            for key, val in kws.items():
                match = getattr(obj, key, None) == val
                if key.endswith('__contains'):
                    match = val in getattr(obj, key[:-10], None)
                elif key.startswith('__'):
                    match = getattr(obj, key[2:])(val)
                if not match:
                    return False
            return True

        return list(filter(cond, self.objects))

    def get(self, **kws):
        filtered = self.filter(**kws)
        if len(filtered) != 1:
            import pdb ;pdb.set_trace()
            raise ValueError(f'expect one result but got {len(filtered)}')
        return filtered[0]


@dataclasses.dataclass
class NginxProject:
    conf: nginx.Conf
    _servers: List[nginx.Server] = dataclasses.field(init=False)

    @classmethod
    def get_by_url(cls, url: URL):
        lb = LB(env=url.env, cid=url.cid)
        return cls.from_raw(lb.get_conf(url))

    @classmethod
    def from_file(cls, filename):
        return cls.from_raw(open(filename).read())

    @classmethod
    def from_raw(cls, content):
        return cls(nginx.loads(content))

    def __post_init__(self):
        self._servers = [
            NginxServer(c) for c in self.conf.children if isinstance(c, nginx.Server)
        ]

    @property
    def servers(self):
        return Objects(self._servers)


@dataclasses.dataclass
class NginxServer:
    conf: nginx.Server
    _locations: List[nginx.Location] = dataclasses.field(init=False)

    def __post_init__(self):
        self._locations = [
            NginxLocation(c)
            for c in self.conf.children
            if isinstance(c, nginx.Location)
        ]

    @property
    def server_name(self):
        try:
            child = next(
                c for c in self.conf.children if c.name == 'server_name'
            )
        except StopIteration:
            return ''
        else:
            return child.value

    @property
    def ports(self) -> Set[int]:
        try:
            children = [
                c for c in self.conf.children
                if getattr(c, 'name', '') == 'listen'
            ]
        except StopIteration:
            return set()
        else:
            return set(int(c.value.split()[0]) for c in children)

    @property
    def locations(self) -> Objects:
        return Objects(self._locations)


@dataclasses.dataclass
class NginxLocation:
    conf: nginx.Location

    def match(self, path: str):
        return bool(re.match(self.path, path or '/'))

    @property
    def path(self):
        return self.conf.value

    @property
    def proxy_pass(self) -> 'ProxyPass':
        try:
            child = next(
                c for c in self.conf.children
                if getattr(c, 'name', '') == 'proxy_pass'
            )
        except StopIteration:
            return None
        else:
            return ProxyPass(child.value)


@dataclasses.dataclass
class ProxyPass:
    value: str
    protocol: str = dataclasses.field(init=False)
    url: str = dataclasses.field(init=False)

    def __post_init__(self):
        self.protocol, self.url = self.value.strip(';').split('://')

    @property
    def upstream(self):
        upstream = Upstream.from_raw(
            LB.get_instance().get_upstream(self.url)
        )
        return upstream.netloc


@dataclasses.dataclass
class Upstream:
    netloc: str

    @classmethod
    def from_raw(cls, raw: str):
        match = (
            re.search(r'\d+(:?\.\d+){3}:\d+', raw) or
            re.search(r'(?<=server\s+)[^;]+')
        )
        netloc = match.group(0)

        return cls(netloc)
