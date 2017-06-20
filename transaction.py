#
# Code for dumping a single transaction, given its ID
#

from bsddb.db import *
import logging
import os.path
import sys
import time
import math
import plyvel
from BCDataStream import *
from base58 import public_key_to_bc_address
from util import short_hex, _open_blkindex, _open_chainstate
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


def get_obfuscation_key(db):
  '''Decode value using the obfuscation key
  First key is the obfuscation key'''
  cursor = db.iterator()
  (x, obfuscate_key) = cursor.next()
  if (x != "0e00".decode("hex_codec") + "obfuscate_key"):
    raise Exception("Couldn't get obfuscation key")
  return obfuscate_key[1:]

def decode_value(key, value):
  '''Decode value using giving obfuscation key
  https://bitcoin.stackexchange.com/questions/51387/how-does-bitcoin-read-from-write-to-leveldb?answertab=active#tab-top'''
  #Repeated key to make both same length
  key = key* int(math.ceil(float(len(value))/len(key)))
  key = key[:len(value)]
  def xor_strings(xs, ys):
    return "".join(chr(ord(x) ^ ord(y)) for x, y in zip(xs, ys))
  
  return xor_strings(key, value)


def dump_utxo(datadir, txid):
  db = _open_chainstate(datadir)
  key = "c"+ txid.decode('hex_codec')[::-1]
  value = db.get(key)
  obfuscate_key = get_obfuscation_key(db)
  value = decode_value(obfuscate_key, value)
  # Version is extracted from the first varint of the serialized utxo
  vds = BCDataStream()
  vds.write(value)
  print long_hex(value)
  version = vds.read_var_int()
  code = vds.read_var_int()
  is_coinbase = code & 1
  vAvail = [False]*2
  vAvail[0] = (code & 2) != 0
  vAvail[1] = (code & 4) != 0
  nMaskCode = (code / 8) + 0 if (code & 6) != 0 else 1
  #spentness bitmask
  while nMaskCode > 0:
    chAvail = ord(vds.read_bytes(1))
    for p in range(0,8):
      f = (chAvail & (1 << p)) != 0
      vAvail.append(f)
    if (chAvail != 0):
      nMaskCode-=1;
  print("version is {}".format(version))
  print("is_coinbase {}".format(is_coinbase))
  print("Avail is {}".format(vAvail))

def dump_transaction(datadir, tx_id):
  """ Dump a transaction, given hexadecimal tx_id-- either the full ID
      OR a short_hex version of the id.
  """
  db=_open_blkindex(datadir)

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

