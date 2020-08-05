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
import concurrent.futures
from multiprocessing import Pool

from neo4j import GraphDatabase

from logging.handlers import RotatingFileHandler

log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')

#location of the loging folder
logFile = 'log/parsing.log'

my_handler = RotatingFileHandler(logFile, mode='a', maxBytes=10*1024*1024,backupCount=6, encoding=None, delay=0)
my_handler.setFormatter(log_formatter)
my_handler.setLevel(logging.INFO)

app_log = logging.getLogger('root')
app_log.setLevel(logging.INFO)

app_log.addHandler(my_handler)

class BlockChainDB(object):

    def __init__(self, uri=None, user=None, password=None, driver=None):
        if driver is None:
            self._driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=False)#REVISE LATER FOR ENCRYPTION!!!
        else:
            self._driver = driver

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
    def _new_tx(tx,block_id, version, locktime, tx_id, inputs, outputs, segwit, i):
                    
        result = tx.run("MATCH (b:block {id:$block_id}) "
                        "MERGE (t:transaction {id:$tx_id}) "
                        "SET t.version=$version, t.segwit=$segwit, t.locktime=$locktime "
                        "MERGE (t)<-[:CONTAINS {i:$i}]-(b) "
                        "RETURN t ",
                        tx_id=tx_id, segwit=segwit, version=version, locktime=locktime, block_id=block_id,i=i)
        
        if len(result.data()) >0: app_log.info(f"created tx: {tx_id}\n{result.data()}")
        else: app_log.error(f"FAILED AT CREATING TX {tx_id}")
        
        for index,tx_out in enumerate(outputs):
            result = tx.run("MATCH (t:transaction {id : $tx_id}) "
                        "MERGE (o:output {index:$index})<-[:CREATES]-(t) "
                        "SET o.amount=$amount, o.script_pubkey=$script_pubkey "
                        "RETURN o ", 
                        tx_id = tx_id,amount=tx_out.amount,script_pubkey=tx_out.script_pubkey.hex(), index=index)
            if len(result.data()) > 0: app_log.info(f"created output: {tx_out.amount}:{index} for tx {tx_id}")
            else: app_log.error(f"FAILED AT CREATING OUTPUT {index}")  
                
        for tx_in in inputs:
            if tx_in.prev_index == 4294967295 or tx_in.prev_tx == (b'\x00'*32).hex():
                    app_log.info("Coinbase Transaction " + tx_id)
            else: 
                result = tx.run("MERGE (t:transaction {id : $tx_id}) "
                            #"MERGE (p:transaction {id:$prev_tx})"
                            "MERGE (tx_in :output {index:$prev_index})<-[:CREATES]-(:transaction {id:$prev_tx}) "
                            "MERGE (tx_in)<-[r:SPENDS {script_sig:$script_sig, witness:$witness}]-(t) "
                            "RETURN r",
                            tx_id=tx_id, prev_index=tx_in.prev_index, prev_tx=tx_in.prev_tx.hex(), 
                            script_sig=tx_in.script_sig.hex(), witness=tx_in.witness.hex() )
                if len(result.data()) > 0: app_log.info(f"created input for transaction {tx_id} spending from {tx_in.prev_tx.hex()} index {tx_in.prev_index}")
                else: app_log.error(f"FAILED AT CREATING INPUT {tx_in.prev_tx}:{tx_in.prev_index}")  

        return True
    
    @staticmethod
    def _new_block(tx,block_id,version, prev_block,merkle_root,timestamp,bits,nonce,n_tx):
        #_height = tx.run( "MATCH (u:block) RETURN COUNT (u) ").single()[0] 
        #pblock = tx.run("MATCH (prev_block:block {id:$prev_block}) RETURN prev_block", prev_block=prev_block)
        #if not pblock.single():
         #   print(f"COULD NOT FIND PREVIOUS BLOCK {prev_block}.")
        result = tx.run("MERGE (block:block {id:$block_id}) "
                        "SET block.n_tx=$n_tx, block.nonce=$nonce, block.merkle_root=$merkle_root, block.bits=$bits, block.timestamp=$timestamp, block.version=$version "
                        "MERGE (prevblock:block {id:$prev_block}) "
                        "MERGE (block)<-[:chain]-(prevblock) "
                        "RETURN block ",
                        block_id=block_id, version=version, prev_block=prev_block, merkle_root=merkle_root, timestamp=timestamp, 
                        bits=bits, nonce=nonce, n_tx=n_tx)
        return result.data()

    def new_address(self, address,i,change_addr):
        with self._driver.session() as session:
            result = session.write_transaction(self._new_address, address,i,change_addr)
            print(result)
            
    def new_tx(self, block_id, version, locktime, tx_id, inputs, outputs, segwit,i):
        with self._driver.session() as session:
            result = session.write_transaction(self._new_tx, block_id, version, locktime, tx_id, inputs, outputs, segwit,i)
                  
    def new_block(self,block_id,version, prev_block,merkle_root,timestamp,bits,nonce,n_tx):
        with self._driver.session() as session:
            result = session.write_transaction(self._new_block,block_id,version, prev_block,merkle_root,timestamp,bits,nonce,n_tx)
            if len(result) >0: app_log.info(f"CREATED BLOCK {block_id}")
            else: app_log.error(f"FAILED AT CREATING BLOCK {block_id}")
            #print(result)
            
            
                     
def manager(args):
    """
    args is a touple of 2 arguments: (arg1, arg2)
    arg1 is the index of the first blk#####.dat file that the parser will work on.
    arg2 is the number of threats, and therefore the number of files the parser will work on.
    For example, if the arguments are (2,2), this means that the parser will work on files
    blk00002.dat and blk00003.dat at the same time.
    arg2 should never be more than 3 for efficiency reasons.
    """
    #n_threads should be 3 or 2 to get maximum efficiency.
    n_threads = args[1]
    n = args[0]
    #db = BlockChainDB(driver = args[2])
    db = BlockChainDB("neo4j://localhost:7687", "neo4j", "wallet")
    file_list = [(f"{i:05}",db) for i in range( n , n + n_threads )]
    with concurrent.futures.ThreadPoolExecutor(max_workers=n_threads) as executor:
        executor.map(parse_blockchain, file_list)   
    return True    

def get_cursor(file):
    c = 0
    print(f"checking for cursors {file}")
    try:
        cursor = open(f"cursors/cursor{file}.txt")
        c = cursor.readline()
        try:
            c = int(c)
            print(f"cursor at {c} for file blk{file}.dat")
            coursor.close()
            return c
        except:
            if c == "finished":
                print(c)
                return True
            else:
                try: 
                    print(f"trying to recover file from backup for file blk{file}.dat.")
                    cursor = open(f"{file[:-4]}.txt.bck")
                    c = coursor.readline()
                    try:
                        c = int(c)
                        subprocess.call(f" cp cursors/cursor{file}.txt.bck cursors/cursor{file}.txt", shell=True)
                        print(f"succesfully recovered file from backup for file blk{file}.dat. Restored original file.")
                        coursor.close()
                        return c
                    except:
                        if c == "finished":
                            coursor.close()
                            print(c)
                            subprocess.call(f" cp cursors/cursor{file}.txt.bck cursors/cursor{file}.txt",shell=True)
                            print(f"Finished. Succesfully updated original file for file blk{file}.dat.")
                            return c
                        else:
                            print(f"Corrupted cursor files for file blk{file}.dat.")
                            raise Exception

                except:
                    print(f"No back-up file for file blk{file}.dat.")
                    raise Exception


    except:
        cursor  = open(f"cursors/cursor{file}.txt","w")
        print(f"No cursor file for file blk{file}.dat.")
        cursor.write(str(c))
        print(c)
        cursor.close()
        return c

def parse_blockchain(args):
    """
    args: ( file index (######),  database driver )
    """
    file = f"blocks_demo/blk{args[0]}.dat"
    db=args[1]
    print(f"parsing {file}")
    #print(f"driver {db}")

    with open(file,"rb") as block_file:
        print(f"opened {file}")
        c = get_cursor(args[0])
        if c !=0: 
            print(f"reading from {c} for file {file}.")
            block_file.read(c)

        #infinite loop to parse the blk#####.dat file. 
        #Only stops when an  error occures or the file is over.
        while True:

            try:
                #parse the block using the class Block from the file block.py
                this_block = Block.parse_from_blk(block_file)

                #calculate the block id using the header of the parsed block:
                #first the header is concatenated
                header = this_block.version.to_bytes(4,"little")+this_block.prev_block[::-1]+this_block.merkle_root[::-1]+this_block.timestamp.to_bytes(4,"little") + this_block.bits + this_block.nonce
                #then the concatenated header is hashed to get the block id.
                block_id = hash256(header)[::-1]

                #A new block is created in the database using the parsed block and its id.
                db.new_block(block_id.hex(),this_block.version, this_block.prev_block.hex(), 
                             this_block.merkle_root.hex(),this_block.timestamp, 
                             int.from_bytes(this_block.bits,"big"), 
                             int.from_bytes(this_block.nonce,"big"),
                             this_block.tx_hashes)

                #Every transaction in the block is parsed using the Tx class from the file tx.py
                for transaction in range(this_block.tx_hashes):
                    #the current transaction is parsed 
                    tx = Tx.parse(block_file)
                    #the parsed transaction is created in the database 
                    db.new_tx(block_id.hex(), tx.version, tx.locktime, tx.id(), tx.tx_ins, tx.tx_outs, tx.segwit,transaction)

                #the cursor is updated to start reading the next block. 8 bytes are added since some info comes before the flag. 
                c += (this_block.size + 8)
                #print(c)
                #the cursor file and its backup file are updated
                cursor  = open(f"cursors/cursor{args[0]}.txt","w")
                cursor.write(str(c))
                cursor.close()
                cursor  = open(f"cursors/cursor{args[0]}.txt.bck","w")
                cursor.write(str(c))
                cursor.close()


            except Exception as e:
                print(f"Finished {file} file. ")
                print(e)
                print(e.with_traceback)
                break












