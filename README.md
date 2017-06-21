## Script to Analyse Distribution of bitcoin txouts

### Usage


Requires plyvel library for reading leveldb
```
pip install plyvel
```


Point of bitcoin datadirectory testnet/mainnet

```
$ python dbdump.py --analyse_utxo --datadir=/home/enigma/.bitcoin/testnet3
Processed 100000 P2PKH txouts
0-50 satoshi/byte: 79397 txouts with total value 0.53 BTC
50-100 satoshi/byte: 1021 txouts with total value 0.13 BTC
100-200 satoshi/byte: 256 txouts with total value 0.06 BTC
200-300 satoshi/byte: 10019 txouts with total value 4.58 BTC
300-500 satoshi/byte: 220 txouts with total value 0.16 BTC
500-1000 satoshi/byte: 2546 txouts with total value 2.63 BTC
1000-Inf satoshi/byte: 6541 txouts with total value 305958.95 BTC
```
