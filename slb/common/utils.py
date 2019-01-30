import dataclasses


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
