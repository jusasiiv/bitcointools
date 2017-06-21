## Script to Analyse Distribution of bitcoin txouts

### Usage


Requires plyvel library for reading leveldb
```
pip install plyvel
```


Point to bitcoin datadirectory testnet/mainnet

```
$ python dbdump.py --analyse_utxo --datadir=/home/enigma/.bitcoin/testnet3
Processed 100000 P2PKH txouts
Fee is 0 satoshi/byte: 100000 txouts are spendable having total value 305967.04 BTC
Fee is 50 satoshi/byte: 20603 txouts are spendable having total value 305966.51 BTC
Fee is 100 satoshi/byte: 19582 txouts are spendable having total value 305966.38 BTC
Fee is 200 satoshi/byte: 19326 txouts are spendable having total value 305966.32 BTC
Fee is 300 satoshi/byte: 9307 txouts are spendable having total value 305961.73 BTC
Fee is 500 satoshi/byte: 9087 txouts are spendable having total value 305961.58 BTC
Fee is 1000 satoshi/byte: 6541 txouts are spendable having total value 305958.95 BTC
```
