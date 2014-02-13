#
# Code for parsing the blkindex.dat file
#

from bsddb.db import *
import logging
from operator import itemgetter
import sys
import time
import os
import plyvel
from BCDataStream import *
from base58 import public_key_to_bc_address
from util import short_hex
from deserialize import *

def dump_blkindex_summary(datadir):
  try:
    db=plyvel.DB(os.path.join(datadir, 'blocks','index'),compression=None)
  except:
    logging.error("Couldn't open blocks/index.  Try quitting any running Bitcoin apps.")
    sys.exit(1)

  kds = BCDataStream()
  vds = BCDataStream()

  n_tx = 0
  n_blockindex = 0

  print("blkindex file summary:")
  for (key, value) in db.iterator():
    kds.clear(); kds.write(key)
    vds.clear(); vds.write(value)

    type = kds.read_bytes(1)

    if type == "t":
      n_tx += 1
    elif type == "b":
      n_blockindex += 1
    elif type == "F":
      print(" Flag: %s %s"%(key, value))
    else:
      logging.warn("blkindex: unknown type '%s'"%(type,))
      continue

  print(" %d transactions, %d blocks."%(n_tx, n_blockindex))
  db.close()
