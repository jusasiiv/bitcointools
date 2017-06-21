#
# Code for dumping a single transaction, given its ID
#

from bsddb.db import *
import logging
import os.path
import sys
import time
import traceback
import math
import plyvel
import bisect
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


def decode_utxo(db, value):
  # Version is extracted from the first varint of the serialized utxo
  vds = BCDataStream()
  vds.write(value)
  version = vds.read_var_int()
  code = vds.read_var_int()
  is_coinbase = code & 1
  vAvail = [False]*2
  vAvail[0] = (code & 2) != 0
  vAvail[1] = (code & 4) != 0
  nMaskCode = (code / 8) + (0 if (code & 6) != 0 else 1)
  #spentness bitmask
  while nMaskCode > 0:
    chAvail = ord(vds.read_bytes(1))
    for p in range(0,8):
      f = (chAvail & (1 << p)) != 0
      vAvail.append(f)
    if (chAvail != 0):
      nMaskCode-=1;

      

  utxos = dict(version=version, coinbase=is_coinbase, vout=dict())
  for (i,vout) in enumerate(vAvail):
    if (vout):
      value = vds.read_var_int()
      value = txout_decompress(value)
      utxos["vout"][i] = dict(value=value, script=gettxout_script(vds))
  return utxos    

def analyse_utxo(datadir):
  #Size of P2PKH input in bytes
  P2PKH_TXIN_SIZE = 180
  PROGESS_INTERVAL = 10**5
  fee_rates = [0, 50, 100, 200, 300, 500, 1000]
  ranges = [dict(count=0, satoshi=0) for x in range(0, len(fee_rates))]
  progress = 0
  db = _open_chainstate(datadir)
  obfuscate_key = get_obfuscation_key(db)
  cursor = db.iterator(prefix="c")
  for (key,value) in cursor: 
    try:
      value = decode_value(obfuscate_key, value)
      txid = long_hex(key[1:][::-1])
      utxos = decode_utxo(db, value)
      for utxo in utxos["vout"].values():
        if (utxo.get("script") and utxo["script"][0] == "Address"):
          rate = utxo["value"]/P2PKH_TXIN_SIZE
          insert_index = bisect.bisect(fee_rates, rate)
          ranges[insert_index-1]["count"] += 1 
          ranges[insert_index-1]["satoshi"] += utxo["value"]
          progress += 1
          if (not progress%PROGESS_INTERVAL):
            print_output(fee_rates, progress, ranges)
    except Exception as e:
      print traceback.format_exc()
      print "Could not process txouts for {}".format(txid)
  print_output(fee_rates, progress, ranges)

def print_output(fee_rates, progress, ranges):
  results = [dict(count=0, satoshi=0) for x in range(0, len(fee_rates))]
  
  #Consolidate ranges into cumulative results
  for i, r  in enumerate(ranges):
    results[i] = reduce(lambda x,y: dict(count=x["count"] + y["count"], 
                                         satoshi=x["satoshi"] + y["satoshi"]),
                        ranges[i:])
  print "Processed {} P2PKH txouts".format(progress)
  for i in range(0, len(fee_rates)):
    print ("Fee is {} satoshi/byte: {} txouts are spendable having total value {:.2f} BTC".
           format(fee_rates[i], results[i]["count"], results[i]["satoshi"]/1.0e8))



def dump_utxo(datadir, txid):
  db = _open_chainstate(datadir)
  key = "c"+ txid.decode('hex_codec')[::-1]
  value = db.get(key)
  obfuscate_key = get_obfuscation_key(db)
  value = decode_value(obfuscate_key, value)
  print decode_utxo(db, value)

def gettxout_script(vds):
  out_type = vds.read_var_int()
  # Depending on the type, the length of the following data will differ.  Types 0 and 1 refers to P2PKH and P2SH
  # encoded outputs. They are always followed 20 bytes of data, corresponding to the hash160 of the address (in
  # P2PKH outputs) or to the scriptHash (in P2PKH). Notice that the leading and tailing opcodes are not included.
  # If 2-5 is found, the following bytes encode a public key. The first by in this cases should be also included,
  # since it determines the format of the key.
  if out_type == 0:
    #Pass version = '\x6F' for testnet
    out=hash_160_to_bc_address(vds.read_bytes(20), version="\x00")
    otype = "Address"  
  elif out_type == 1:
    out = vds.read_bytes(20)
    otype = "P2SH"
  elif out_type in [2, 3, 4, 5]:
    # 33 bytes (1 byte for the type + 32 bytes of data)
    out = vds.read_bytes(32)
    otype = "P2PK"
    # Finally, if another value is found, it represents the length of the following data, which is uncompressed.
  else:
    out = vds.read_bytes(out_type - 6) 
    otype = "Custom"
  return (otype, out)

def txout_decompress(x):
  """ Decompresses the Satoshi amount of a UTXO stored in the LevelDB. Code is a port from the Bitcoin Core C++
  source:
  https://github.com/bitcoin/bitcoin/blob/v0.13.2/src/compressor.cpp#L161#L185
  :param x: Compressed amount to be decompressed.
  :type x: int
  :return: The decompressed amount of Satoshis.
  :rtype: int
  """

  if x == 0:
    return 0
  x -= 1
  e = x % 10
  x /= 10
  if e < 9:
    d = (x % 9) + 1
    x /= 9
    n = x * 10 + d
  else:
    n = x + 1
    while e > 0:
      n *= 10
      e -= 1
  return n

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

