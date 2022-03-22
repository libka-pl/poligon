# -*- coding: utf-8 -*-
"""
    VIKI Rakuten® addon Add-on

"""

from __future__ import absolute_import

import hashlib
import re
import time
import os
from ast import literal_eval as evaluate
#import six
import xbmcaddon, xbmcvfs
makeFile = xbmcvfs.mkdir
try:
    from sqlite3 import dbapi2 as db, OperationalError
except ImportError:
    from pysqlite2 import dbapi2 as db, OperationalError


str = unicode = basestring = str

cache_table = "cache"
my_addon = xbmcaddon.Addon()
DATA_PATH = xbmcvfs.translatePath(my_addon.getAddonInfo("profile")) or 'D:\drop'

def get(function_, duration, *args, **table):

    try:
        response = None

        f = repr(function_)
        f = re.sub(r".+\smethod\s|.+function\s|\sat\s.+|\sof\s.+", "", f)

        a = hashlib.md5()
        for i in args:
            a.update(ensure_binary(i, errors="replace"))
        a = str(a.hexdigest())
    except Exception:
        pass
    try:
        table = table["table"]
    except Exception:
        table = "rel_list"

    try:
        makeFile(DATA_PATH)
        dbcon = db.connect(os.path.join(DATA_PATH, "cache.db"))
        dbcur = dbcon.cursor()
        dbcur.execute(
            "SELECT * FROM {tn} WHERE func = '{f}' AND args = '{a}'".format(
                tn=table, f=f, a=a
            )
        )
        match = dbcur.fetchone()

        try:
            response = evaluate(match[2].encode("utf-8"))
        except AttributeError:
            response = evaluate(match[2])

        t1 = int(match[3])
        t2 = int(time.time())
        update = (abs(t2 - t1) / 3600) >= int(duration)
        if not update:
            return response
    except Exception:
        pass

    try:
        r = function_(*args)
        if (r is None or r == []) and response is not None:
            return response
        elif r is None or r == []:
            return r
    except Exception:
        return

    try:
        r = repr(r)
        t = int(time.time())
        dbcur.execute(
            "CREATE TABLE IF NOT EXISTS {} ("
            "func TEXT, "
            "args TEXT, "
            "response TEXT, "
            "added TEXT, "
            "UNIQUE(func, args)"
            ");".format(table)
        )
        dbcur.execute(
            "DELETE FROM {0} WHERE func = '{1}' AND args = '{2}'".format(table, f, a)
        )
        dbcur.execute("INSERT INTO {} Values (?, ?, ?, ?)".format(table), (f, a, r, t))
        dbcon.commit()
    except Exception:
        pass

    try:
        return evaluate(r.encode("utf-8"))
    except Exception:
        return evaluate(r)


def timeout(function_, *args):
    try:
        key = _hash_function(function_, args)
        result = cache_get(key)
        return int(result["date"])
    except Exception:
        return None


def cache_get(key):
    # type: (str, str) -> dict or None
    try:
        cursor = _get_connection_cursor()
        cursor.execute("SELECT * FROM %s WHERE key = ?" % cache_table, [key])
        return cursor.fetchone()
    except OperationalError:
        return None


def cache_insert(key, value):
    # type: (str, str) -> None
    cursor = _get_connection_cursor()
    now = int(time.time())
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS %s (key TEXT, value TEXT, date INTEGER, UNIQUE(key))"
        % cache_table
    )
    update_result = cursor.execute(
        "UPDATE %s SET value=?,date=? WHERE key=?" % cache_table, (value, now, key)
    )

    if update_result.rowcount is 0:
        cursor.execute(
            "INSERT INTO %s Values (?, ?, ?)" % cache_table, (key, value, now)
        )

    cursor.connection.commit()


def cache_clear():
    try:
        cursor = _get_connection_cursor()

        for t in [cache_table, "rel_list", "rel_lib"]:
            try:
                cursor.execute("DROP TABLE IF EXISTS %s" % t)
                cursor.execute("VACUUM")
                cursor.commit()
            except:
                pass
        cache_clear_meta()
    except:
        pass


def cache_clear_meta():
    try:
        cursor = _get_connection_cursor_meta()

        for t in ["meta"]:
            try:
                cursor.execute("DROP TABLE IF EXISTS %s" % t)
                cursor.execute("VACUUM")
                cursor.commit()
            except:
                pass
    except:
        pass


def cache_clear_providers():
    try:
        cursor = _get_connection_cursor_providers()

        for t in ["rel_src", "rel_url"]:
            try:
                cursor.execute("DROP TABLE IF EXISTS %s" % t)
                cursor.execute("VACUUM")
                cursor.commit()
            except:
                pass
    except:
        pass


def cache_clear_search():
    try:
        cursor = _get_connection_cursor_search()

        for t in ["tvshow", "movies"]:
            try:
                cursor.execute("DROP TABLE IF EXISTS %s" % t)
                cursor.execute("VACUUM")
                cursor.commit()
            except:
                pass
    except:
        pass


def cache_clear_all():
    cache_clear()
#   cache_clear_meta()
    cache_clear_providers()


def _get_connection_cursor():
    conn = _get_connection()
    return conn.cursor()


def _get_connection():
    makeFile(DATA_PATH)
    conn = db.connect(os.path.join(DATA_PATH, "cache.db"))
    conn.row_factory = _dict_factory
    return conn


def _get_connection_cursor_meta():
    conn = _get_connection_meta()
    return conn.cursor()


def _get_connection_meta():
    makeFile(DATA_PATH)
    conn = db.connect(os.path.join(DATA_PATH, "meta.5.db"))
    conn.row_factory = _dict_factory
    return conn


def _get_connection_cursor_providers():
    conn = _get_connection_providers()
    return conn.cursor()


def _get_connection_providers():
    makeFile(DATA_PATH)
    conn = db.connect(os.path.join(DATA_PATH, "providers.13.db"))
    conn.row_factory = _dict_factory
    return conn


def _get_connection_cursor_search():
    conn = _get_connection_search()
    return conn.cursor()


def _get_connection_search():
    makeFile(DATA_PATH)
    conn = db.connect(os.path.join(DATA_PATH, "search.1.db"))
    conn.row_factory = _dict_factory
    return conn


def _dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def _hash_function(function_instance, *args):
    return _get_function_name(function_instance) + _generate_md5(args)


def _get_function_name(function_instance):
    return re.sub(
        ".+\smethod\s|.+function\s|\sat\s.+|\sof\s.+", "", repr(function_instance)
    )


def _generate_md5(*args):
    md5_hash = hashlib.md5()
    [md5_hash.update(ensure_binary(arg, errors="replace")) for arg in args]
    return str(md5_hash.hexdigest())


def _is_cache_valid(cached_time, cache_timeout):
    now = int(time.time())
    diff = now - cached_time
    return (cache_timeout * 3600) > diff

def ensure_binary(s, encoding='utf-8', errors='strict'):
    """Coerce **s** to six.binary_type.

    For Python 2:
      - `unicode` -> encoded to `str`
      - `str` -> `str`

    For Python 3:
      - `str` -> encoded to `bytes`
      - `bytes` -> `bytes`
    """
    binary_type = bytes
    text_type = str
    if isinstance(s, binary_type):
        return s
    if isinstance(s, text_type):
        return s.encode(encoding, errors)
    raise TypeError("not expecting type '%s'" % type(s))
