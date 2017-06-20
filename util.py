#
# Misc util routines
#
import plyvel
import os
try:
  from bsddb.db import *
except:
  pass

def _open_blkindex(datadir):
  try:
    db=plyvel.DB(os.path.join(datadir, 'blocks','index'),compression=None)
  except Exception as e:
        raise Exception("Couldn't open blocks/index.  Try quitting any running "
                        "Bitcoin apps \n{}".format(str(e)))
  return db

def _open_chainstate(datadir):
  try:
    db=plyvel.DB(os.path.join(datadir, 'chainstate'), compression=None)
  except Exception as e:
    raise Exception("Couldn't open blocks/index.  Try quitting any running "
                    "Bitcoin apps \n{}".format(str(e)))
  return db

def long_hex(bytes):
  return bytes.encode('hex_codec')

def short_hex(bytes):
  t = bytes.encode('hex_codec')
  if len(t) < 11:
    return t
  return t[0:4]+"..."+t[-4:]

def determine_db_dir():
  import os
  import os.path
  import platform
  if platform.system() == "Darwin":
    return os.path.expanduser("~/Library/Application Support/Bitcoin/")
  elif platform.system() == "Windows":
    return os.path.join(os.environ['APPDATA'], "Bitcoin")
  return os.path.expanduser("~/.bitcoin")

def create_env(db_dir=None):
  if db_dir is None:
    db_dir = determine_db_dir()
  db_env = DBEnv(0)
  r = db_env.open(db_dir,
                  (DB_CREATE|DB_INIT_LOCK|DB_INIT_LOG|DB_INIT_MPOOL|
                   DB_INIT_TXN|DB_THREAD|DB_RECOVER))
  return db_env
