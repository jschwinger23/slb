from typing import List


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
            raise ValueError(f'expect one result but got {len(filtered)}')
        return filtered[0]
