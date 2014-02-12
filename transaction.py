#
# Code for dumping a single transaction, given its ID
#

from bsddb.db import *
import logging
import os.path
import sys
import time
import plyvel
from BCDataStream import *
from base58 import public_key_to_bc_address
from util import short_hex
from deserialize import *
BLOCK_HEADER_SIZE = 80
def _read_CDiskTxPos(stream):
  n_file = stream.read_var_int()
  n_block_pos = stream.read_var_int()
  n_tx_pos = stream.read_var_int()
  return (n_file, n_block_pos, n_tx_pos)

def _dump_tx(datadir, tx_hash, tx_pos):
  blockfile = open(os.path.join(datadir, "blocks","blk%05d.dat"%(tx_pos[0],)), "rb")
  ds = BCDataStream()
  ds.map_file(blockfile, tx_pos[1]+BLOCK_HEADER_SIZE+tx_pos[2])
  d = parse_Transaction(ds)
  print deserialize_Transaction(d)
  ds.close_file()
  blockfile.close()

def dump_transaction(datadir, tx_id):
  """ Dump a transaction, given hexadecimal tx_id-- either the full ID
      OR a short_hex version of the id.
  """
  try:
    db=plyvel.DB(os.path.join(datadir, 'blocks','index'),compression=None)
  except:
    logging.error("Couldn't open blocks/index.  Try quitting any running Bitcoin apps.")
    sys.exit(1)

  kds = BCDataStream()
  vds = BCDataStream()

  n_tx = 0
  n_blockindex = 0

  key_prefix = "t"+(tx_id[-4:].decode('hex_codec')[::-1])
  cursor = db.iterator(prefix=key_prefix)
  for (key,value) in cursor: 
    kds.clear(); kds.write(key)
    vds.clear(); vds.write(value)

    # Skip the t prefix
    kds.read_bytes(1)
    hash256 = (kds.read_bytes(32))
    hash_hex = long_hex(hash256[::-1])
    if (hash_hex.startswith(tx_id) or short_hex(hash256[::-1]).startswith(tx_id)):
      tx_pos = _read_CDiskTxPos(vds)
      _dump_tx(datadir, hash256, tx_pos)
      break

  db.close()

