import binascii
import sys
import traceback
from block import Block
from helper import read_varint, hash256
from tx import Tx
import subprocess
import os
from time import sleep
from subprocess import Popen, PIPE
import logging
from neo4j import GraphDatabase
from logging.handlers import RotatingFileHandler

log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')

logFile = 'log/parsing.log'

my_handler = RotatingFileHandler(logFile, mode='a', maxBytes=10*1024*1024,backupCount=6, encoding=None, delay=0)
my_handler.setFormatter(log_formatter)
my_handler.setLevel(logging.INFO)

app_log = logging.getLogger('root')
app_log.setLevel(logging.INFO)

app_log.addHandler(my_handler)

class BlockChainDB(object):

    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=False)#REVISE LATER FOR ENCRYPTION!!!

    def close(self):
        self._driver.close()
        
        
    @staticmethod
    def _new_address(tx, address,i,change_addr):
        if change_addr: addr_type = "change"
        else: addr_type = "recipient"
        result = tx.run("CREATE a = (:address {address:$address, acc_index:$index, type:$kind, created:timestamp()}) "
                        "RETURN a ", address=address, index = i, kind = addr_type)
        return result.single()
    
    
    @staticmethod
    def _new_output(tx,amount, script_pubkey,tx_id,out_index):
        result = tx.run("MATCH (n:transaction {id : $tx_id}) "
                        "CREATE p = (:output {out_index:$out_index, script_pubkey:$script_pubkey})<-[:CREATES]-(n) "
                        "RETURN p ", tx_id = tx_id, script_pubkey=script_pubkey, out_index=out_index, local_index=local_index)
        return result.single()
    
    @staticmethod
    def _spend_outputs(tx):
        new_txs = tx.run("MATCH (tx:transaction) WHERE NOT (tx)-[:SPENDS]->() RETURN tx.id, tx.inputs")
        print(new_txs.data())
        for tx in new_txs.data():
            for tx_input in tx["tx.inputs"]:
                tx_in = tx.input.split(":")
                prev_tx=tx_in[0]
                index = tx_in[1]
                if index == 4294967295 or prev_tx == (b'\x00'*32).hex():
                    app_log.info("Coinbase Transaction " + tx['tx.id'])
                                 
                else:
                    #app_log(f"input index = {tx_in.prev_index}, input prev tx = {tx_in.prev_tx}")
                    result = tx.run("MATCH (t:transaction {id:$tx_id}), (o:output {index:$index})<-[:CREATES]-(:transaction {id:$prev_tx}) "
                                "CREATE (t)-[r:SPENDS]->(o)"
                                "RETURN r",
                                tx_id=tx['tx.id'], index=index, prev_tx=prev_tx)
                    if result.single()  is not None: app_log.info(f"connected input: {index}")
                    else: app_log.error(f"Failed at connecting input: {index}")
                                 
        return True
        
    
    @staticmethod
    def _new_tx(tx,block_id, version, locktime, tx_id, _inputs, outputs, segwit):
        
        inputs = [str(tx_in) for tx_in in _inputs]
        print(inputs)
                                 
        result = tx.run("MATCH (b:block {id:$block_id})"
                        "CREATE (n:transaction {id:$tx_id, version:$version, segwit:$segwit, locktime:$locktime}, inputs:$inputs)<-[:CONTAINS]-(b) "
                        "RETURN n",
                        tx_id=tx_id, segwit=segwit, version=version, locktime=locktime, block_id=block_id, inputs=inputs)
        
        if result.single(): app_log.info(f"created tx: {tx_id}")
        else: app_log.error(f"FAILED AT CREATING TX {tx_id}")
        
        for index,tx_out in enumerate(outputs):
            result = tx.run("MATCH (n:transaction {id : $tx_id}) "
                        "CREATE p = (:output {amount:$amount, script_pubkey:$script_pubkey, output_index:$index})<-[:CREATES]-(n) "
                        "RETURN p ", 
                        tx_id = tx_id,amount=tx_out.amount,script_pubkey=str(tx_out.script_pubkey), index=index)
            if result.single() is not None: app_log.info(f"created output: {tx_out.amount}:{index}")
            else: app_log.error(f"FAILED AT CREATING OUTPUT {index}")  
        
        return True
    
    @staticmethod
    def _link_blocks(tx):
        new_blocks = tx.run("MATCH (blk:block) WHERE NOT (blk)<-[:LINKS]-() RETURN blk.id, blk.prev_block")
        for block in new_blocks.data():
            
            result = tx.run("MATCH (a:block {id:$block_id}) MATCH (b:block {id:$prev_block})"
                            "CREATE p = (a)<-[r:LINKS]-(b) RETURN p", 
                            block_id=block["blk.id"], prev_block=block["blk.prev_block"])
            if result.single() is not None: app_log.info(result.single())
            else: app_log.info(f"Failed linking block {block}")
        return True
    
    @staticmethod
    def _new_block(tx,block_id,version, prev_block,merkle_root,timestamp,bits,nonce,n_tx):
        #_height = tx.run( "MATCH (u:block) RETURN COUNT (u) ").single()[0] 
        #pblock = tx.run("MATCH (prev_block:block {id:$prev_block}) RETURN prev_block", prev_block=prev_block)
        #if not pblock.single():
         #   print(f"COULD NOT FIND PREVIOUS BLOCK {prev_block}.")
        result = tx.run("CREATE (n:block {id:$block_id, version:$version , prev_block:$prev_block, merkle_root:$merkle_root, timestamp:$timestamp, bits:$bits, nonce:$nonce, n_tx:$n_tx}) "
                        "RETURN n",
                        block_id=block_id, version=version, prev_block=prev_block, merkle_root=merkle_root, timestamp=timestamp, 
                        bits=bits, nonce=nonce, n_tx=n_tx)
        return result.single()

    def new_address(self, address,i,change_addr):
        with self._driver.session() as session:
            result = session.write_transaction(self._new_address, address,i,change_addr)
            print(result)
            
    def new_output(self, address,tx_id,out_index):
        with self._driver.session() as session:
            result = session.write_transaction(self._new_utxo, address,tx_id,out_index)
            print(result)
                                 
    def spend_outputs(self):
        with self._driver.session() as session:
            result = session.write_transaction(self._spend_outputs)
            
    def new_tx(self, block_id, version, locktime, tx_id, inputs, outputs, segwit):
        with self._driver.session() as session:
            result = session.write_transaction(self._new_tx, block_id, version, locktime, tx_id, inputs, outputs, segwit)
            
    def link_blocks(self):
        with self._driver.session() as session:
            result = session.write_transaction(self._link_blocks)
                  
    def new_block(self,block_id,version, prev_block,merkle_root,timestamp,bits,nonce,n_tx):
        with self._driver.session() as session:
            result = session.write_transaction(self._new_block,block_id,version, prev_block,merkle_root,timestamp,bits,nonce,n_tx)
            if result is not None: app_log.info(f"CREATED BLOCK {block_id}")
            else: app_log.error(f"FAILED AT CREATING BLOCK {block_id}")
            #print(result)
            
            



def parse_blockchain():
    for file in range(2040):
        with open(f"blocks_demo/blk{file:05}.dat","rb") as block_file:
            #for block_in_file in range(1000,1200):
            while ok:
                #try:
                this_block = Block.parse_from_blk(block_file)
                f.write(f"Block: \nversion:{this_block.version}\nPrevious block: {this_block.prev_block}\nMerkle: {this_block.merkle_root}")
                f.write(f"\nTimeStamp:{this_block.timestamp}\nNonce block: {this_block.nonce}\nBits: {this_block.bits}")
                f.write(f"\nNumber of Transactions: {this_block.tx_hashes}\n\nTransactions:")
                #for transaction in range(countOfTransactions):

                header = this_block.version.to_bytes(4,"little")+this_block.prev_block[::-1]+this_block.merkle_root[::-1]+this_block.timestamp.to_bytes(4,"little") + this_block.bits + this_block.nonce

                block_id = hash256(header)[::-1]
                #block_id = hex(int.from_bytes(block_id,"big"))[2:]
                #print(int.from_bytes(this_block.nonce,"big"))
                db.new_block(block_id.hex(),this_block.version, this_block.prev_block.hex(), 
                             this_block.merkle_root.hex(),this_block.timestamp, 
                             int.from_bytes(this_block.bits,"big"), 
                             int.from_bytes(this_block.nonce,"big"),
                             this_block.tx_hashes)

                for transaction in range(this_block.tx_hashes):
                    tx = Tx.parse(block_file)
                    db.new_tx(block_id.hex(), tx.version, tx.locktime, tx.id(), tx.tx_ins, tx.tx_outs, tx.segwit)
                """
                except Exception as e:
                    print(e.with_traceback)
                    break

                counter+=1
                if counter >=1000: ok=False
                """



    f.close()    
    
db = BlockChainDB( "neo4j://localhost:7687" ,"neo4j" ,"wallet" )
db.link_blocks()