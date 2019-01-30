import os
import requests
import subprocess
import dataclasses

from ..utils import URL


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
                'service_name': f'nginx-lb-{self.env}-sg',
                'env': self.env,
                'detail': True,
            },
            headers={'TOKEN': os.getenv('SMM_TOKEN')}
        )
        res.raise_for_status()
        rj = res.json()
        task = next(
            t for t in rj[0]['tasks'] if t['idc'].lower() == self.cid and
            t['state'] == 'TASK_RUNNING' and t['id'].endswith('-1')
        )
        self.hostname = task['hostname']
        self.container_id = task['container_id']
        self.__class__._instance = self

    @classmethod
    def get_instance(cls):
        if not getattr(cls, '_instance', None):
            raise ValueError('LB not initiated')
        return cls._instance

    def get_conf(self, url: URL) -> str:
        conf_filename = self.run(
            f'grep -P "server_name\s+{url.netloc}" -r /etc/nginx/http-enabled/ -l | grep -v dyupstream | head -1'
        )
        print(f'get config: {conf_filename}')
        return self.run(f'cat {conf_filename}')

    def run(self, command: str):
        return subprocess.check_output(
            f'docker -H {self.hostname}:7070 exec -i mesos-{self.container_id} {command}',
            shell=True
        ).decode()

    def get_upstream(self, url: str) -> str:
        try:
            upstream_raw = self.run(
                f'grep {url} -r /etc/nginx/service_deps/services.json -A8 | grep addr'
            )
        except subprocess.CalledProcessError:
            upstream_raw = self.run(
                f'grep {url} -r /etc/nginx/http-enabled/dyupstream* -A5'
            )
        return upstream_raw
