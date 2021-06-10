import sqlite3

class State(object):
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.execute("""create table if not exists state1 (key text primary key, token text)""")
        # TODO: migrations. e.g. https://github.com/clutchski/caribou

    def close(self):
        self.conn.commit()
        self.conn.close()

    def __setitem__(self, key, value):
        self.conn.execute("""insert into state1 (key, token) values (:key, :token) on conflict(key) do update set token=:token""", dict(key=str(key), token=str(value)))

    def __getitem__(self, key):
        return self.get_by_key(key, None, True)

    def get_by_key(self, key, default, raise_exception):
        for tuple in self.conn.execute("""select token from state1 where key=:key""", dict(key=str(key))):
            return tuple[0]
        if raise_exception:
            raise KeyError(key)
        else:
            return default

    def get(self, key, default = None):
        return self.get_by_key(key, default, False)

    def __delitem__(self, key):
        self.conn.execute("""delete from `state1` where `key`=?""", (str(key),))

    def __len__(self):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError

    def copy(self):
        raise NotImplementedError

    def has_key(self, k):
        raise NotImplementedError

    def keys(self):
        raise NotImplementedError

    def values(self):
        raise NotImplementedError

    def items(self):
        raise NotImplementedError

    def pop(self, *args):
        raise NotImplementedError

    def __cmp__(self, dict_):
        raise NotImplementedError

    def __contains__(self, item):
        raise NotImplementedError

    def __iter__(self):
        raise NotImplementedError

