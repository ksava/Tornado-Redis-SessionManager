#!/usr/bin/python
#
# File: __init__.py
# Author: Marco Dalla Stella
# Date: 28/05/2010

__author__="Marco Dalla Stella"

import redis
import cPickle as pickle
from datetime import datetime, timedelta
import hashlib
import os

settings = {
    "SESSION_EXPIRE_TIME": 7200,    # sessions are valid for 7200 seconds (2 hours)
    "REDIS_URL": {'ip': 'localhost', 'port': 6379, 'db': 0, },
}

class SessionManager(object):
    """
    Session manager class, used to manage the various session objects and talk with Redis.
    """

    class _instance_():
        def __init__(self, session_expire_time=settings["SESSION_EXPIRE_TIME"], redis_url=settings["REDIS_URL"], on_delete=None):
            self._rd = redis.Redis(host=redis_url['ip'], port=redis_url['port'], db=redis_url['db'])
            self._on_delete = on_delete
            self._session_expire_time = session_expire_time

        def get_session(self, cookie=None):
            try:
                data = self._rd.get(cookie)
                session = pickle.loads(data)
                if session.is_expired:
                    self.delete_session(session)
                    raise Exception
                else:
                    session.renew()
            except:
                session = Session(self._session_expire_time)

            return session


        def get_all_sessions(self):
            for sid in self._rd.keys('*'):
                session = self._rd.get(sid)
                session = pickle.loads(session)
                yield session

        def save_session(self, session):
            data = pickle.dumps(session)
            return self._rd.set(session.sid, data)

        def delete_session(self, session):
            if self._on_delete:
                self._on_delete(session.sid)
            return self._rd.delete(session.sid)

    instance = {}
    def __init__(self, *args):
        if self.__class__ not in SessionManager.instance:
            SessionManager.instance[self.__class__] = SessionManager._instance_(*args)
        else:
            return None

    def __getattr__(self, name):
        return getattr(self.instance[self.__class__], name)

    def __setattr__(self, name, value):
        return setattr(self.instance[self.__class__], name, value)


class Session(object):
    """
    Session object, works like a dict.
    """

    def __init__(self, session_expire):
        self.sid = self._generate_sid()
        self._expires_in = timedelta(seconds=session_expire)
        self._last_update = datetime.now()
        self.data = dict()

    def _generate_sid(self):
        return os.urandom(32).encode('hex') # 256 bits of entropy

    @property
    def is_expired(self):
         td = datetime.now() - self._last_update
         return td > self._expires_in

    def renew(self):
        self._last_update = datetime.now()
        self.save()

    def has_key(self, keyname):
        return self.__contains__(keyname)

    def save(self):
        return SessionManager().save_session(self)

    def delete(self):
        return SessionManager().delete_session(self)

    def __delitem__(self, key):
        del self.data[key]
        self.save()
        return True

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, val):
        self.data[key] = val
        self.save()
        return True

    def __len__(self):
        return len(self.data)

    def __contains__(self, key):
        return self.data.has_key(key)

    def __iter__(self):
        for key in self.data:
            yield key

    def __str__(self):
        return u"sid: %s, {%s}" % (self.sid, ', '.join(['"%s" = "%s"' % (k, self.data[k]) for k in self.data]))
