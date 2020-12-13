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

from script import Script
from io import BytesIO
from helper import (
    decode_base58,
    encode_base58_checksum,
    encode_varint,
    h160_to_p2pkh_address,
    h160_to_p2sh_address,
    int_to_little_endian,
    little_endian_to_int,
    read_varint,
    sha256,
)
import segwit_addr
import add_height

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
    def _new_coinbase_tx(tx,block_id, version, locktime, tx_id, inputs, outputs, segwit, i):
        
        witnesses = []
        for wit in inputs[0].witness:
            try: witness = wit.hex()
            except: witness = wit
            witnesses.append(witness)
        
        result = tx.run("MATCH (b:block {id:$block_id}) "
                        "MERGE (t:transaction {id:$tx_id}) "
                        "SET t.version = $version, t.locktime=$locktime, t.segwit = $segwit "
                        "MERGE (b)-[:CONTAINS]->(t) "
                        "MERGE (b)-[:COINBASE {witness:$wit, script_sig:$script_sig}]->(t) ",
                        block_id=block_id, tx_id=tx_id, wit=str(witnesses),
                        script_sig=inputs[0].script_sig.hex(),version=version, 
                        locktime=locktime,segwit=segwit)
        app_log.info(f"Coinbase transaction  {tx_id}")
        return
                
    @staticmethod
    def _new_tx(tx,block_id, version, locktime, tx_id, inputs, outputs, segwit, i,coinbase=False):
        _outputs = []
        _inputs = []
        
        def encode_address(_script_pubkey,testnet=True):
            address = ""
            addr_type = ""
            length = encode_varint(len(_script_pubkey))
            stream = BytesIO(length+_script_pubkey)
            #stream = BytesIO(_script_pubkey)
            try: 
                script_pubkey = Script.parse(stream)
                if script_pubkey.is_p2pkh_script_pubkey(): 
                    address= h160_to_p2pkh_address(script_pubkey.cmds[2], testnet)
                    addr_type ="P2PKH"
                elif script_pubkey.is_p2sh_script_pubkey():  
                    address= h160_to_p2sh_address(script_pubkey.cmds[1], testnet)
                    addr_type = "P2SH"
                elif script_pubkey.is_p2wpkh_script_pubkey() or script_pubkey.is_p2wsh_script_pubkey(): 
                    if testnet: address = segwit_addr.encode("tb",0,script_pubkey.cmds[1])
                    else: address = segwit_addr.encode("bc",0,script_pubkey.cmds[1]) 
                    if script_pubkey.is_p2wpkh_script_pubkey(): addr_type = "P2WPKH"
                    else: addr_type = "P2WSH"
                elif len(script_pubkey.cmds)==2 and script_pubkey.cmds[1]==0xac:
                    try: 
                        address = script_pubkey.cmds[0].hex()
                        addr_type = "P2PK"
                    except: app_log.info(f"P2PK failed {script_pubkey.cmds[0]} from tx: {output['t.id']}")

            except:
                app_log.info(f"script parsing failed.")
                
            
            return address, addr_type
        
        for index,output in enumerate(outputs):
            address, addr_type = encode_address(output.script_pubkey)
            output = {
                "index":index,
                "script_pubkey" : output.script_pubkey.hex(),
                "amount" : output.amount,
                "address" : address,
                "type" : addr_type
            }
            _outputs.append(output)
            
        for tx_in in inputs:
            witnesses = []
            for wit in tx_in.witness:
                try: witness = wit.hex()
                except: witness = wit
                witnesses.append(witness)
            
            _input = {
                "prev_tx" : tx_in.prev_tx.hex(),
                "script_sig" : tx_in.script_sig.hex(),
                "witness" : str(witnesses),
                "prev_index" : tx_in.prev_index
            }
            #We have to check if this is a coinbase transaction. If it is, it means it has no input. We only append no coinbase ins.
            #if _input["prev_index"] != 4294967295:
            _inputs.append(_input)
        
        query = "MERGE (b:block {id:$block_id}) \n"
        query+= "MERGE (t:transaction {id:$tx_id}) \n"
        query+= "SET t.version=$version, t.segwit=$segwit, t.locktime=$locktime \n"
        query+= "MERGE (t)<-[:CONTAINS {i:$i}]-(b) \n"
        query+= "WITH t,b \n"
        query+= "FOREACH (output in $outputs | \n"
        query+= "MERGE (o:output {index:output.index})<-[:CREATES]-(t) \n"
        query+= "SET o.amount=output.amount, o.script_pubkey=output.script_pubkey \n"
        query+= "FOREACH(ignoreMe IN CASE WHEN output.address <> '' THEN [1] ELSE [] END | \n"
        query+= "MERGE (a:address {address:output.address}) SET a.address_type=output.type \n "
        query+= "MERGE (a)<-[:RELATES]-(o)"
        query+= ") "
        query+= ") \n"
        
        if coinbase:
            query+= "FOREACH (input in $inputs | \n"
            query+= "MERGE (b)-[:COINBASE {witness:input.witness, script_sig:input.script_sig}]->(t)) "
            #query+= ")"
        else:    
            query+= "FOREACH (input in $inputs | \n"
            query+= "MERGE (prev_trans: transaction {id:input.prev_tx}) \n"
            query+= "MERGE (tx_in: output {index:input.prev_index})<-[:CREATES]-(prev_trans) \n"
            query+= "MERGE (tx_in)-[:SPENDS {script_sig:input.script_sig, witness:input.witness}]->(t) \n"
            query+= ")"
        
        result = tx.run(query,tx_id=tx_id, segwit=segwit, version=version, locktime=locktime, 
                        inputs=_inputs, outputs=_outputs, block_id=block_id, i=i)
        
        
        

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
                        "MERGE (block)<-[:LINKS]-(prevblock) "
                        "RETURN block ",
                        block_id=block_id, version=version, prev_block=prev_block, merkle_root=merkle_root, timestamp=timestamp, 
                        bits=bits, nonce=nonce, n_tx=n_tx)
        return result.data()
    

    @staticmethod    
    def _check_constrains(tx):
        
        print("checking constraints.")
        
        tx_id = False
        block_id = False
        address_address = False
        result = tx.run("CALL db.constraints")
        constraints = result.data()
        for constraint in constraints:
            if "transaction.id" in constraint["description"] and "UNIQUE" in constraint["description"]: tx_id = True
            elif "block.id" in constraint["description"] and "UNIQUE" in constraint["description"]: block_id = True
            elif "address.address" in constraint["description"] and "UNIQUE" in constraint["description"]: address_address = True
        if tx_id and block_id and address_address:
            print("CONSTRAINTS ALREADY EXISTS!")
            return True
        else:
            result = tx.run("MERGE (b:block {id:'0000000000000000000000000000000000000000000000000000000000000000'}) \n"
                             "SET b.height = -1 \n"
                             "MERGE (t:transaction {id:'CONFIG'}) \n"
                             "MERGE (a:address {address:'CONFIG'}) \n"
                             "RETURN b,t,a \n")
            return False
    
    @staticmethod    
    def _config_constrains(tx):
        
        result2 = tx.run("CREATE CONSTRAINT ON (t:transaction) ASSERT t.id IS UNIQUE \n")
        result3 = tx.run("CREATE CONSTRAINT ON (a:address) ASSERT a.address IS UNIQUE \n")
        result4 = tx.run( "CREATE CONSTRAINT ON (b:block) ASSERT b.id IS UNIQUE \n")
        result4 = tx.run( "CREATE CONSTRAINT ON (b:block) ASSERT b.height IS UNIQUE  \n")
        
        print("constraints created.")
        return 
    
    def config_constrains(self):
        checked = False
        with self._driver.session() as session:
            result = session.write_transaction(self._check_constrains)
            #print(result)
            checked = result
        if not checked:
            with self._driver.session() as session:
                result = session.write_transaction(self._config_constrains)
        print(result)
        return result
    
    @staticmethod    
    def _get_sixth_block_behind(tx):
        
        result = tx.run("MATCH (b:block) "
                        "WITH MAX(b.height) AS tip "
                        "MATCH (b:block {height:tip})<-[:LINKS]-(:block)<-[:LINKS]-(:block)"
                        "<-[:LINKS]-(:block)<-[:LINKS]-(:block)<-[:LINKS]-(:block)<-[:LINKS]"
                        "-(:block)<-[:LINKS]-(x:block) "
                        "RETURN x.id" )
        data = result.data()
        return data
        
            
    def new_tx(self, block_id, version, locktime, tx_id, inputs, outputs, segwit,i,coinbase):
        with self._driver.session() as session:
            result = session.write_transaction(self._new_tx, block_id, version, locktime, tx_id, inputs, outputs, segwit,i,coinbase)
            
    def new_coinbase_tx(self, block_id, version, locktime, tx_id, inputs, outputs, segwit,i):
        with self._driver.session() as session:
            result = session.write_transaction(self._new_coinbase_tx, block_id, version, locktime, tx_id, inputs, outputs, segwit,i)
                  
    def new_block(self,block_id,version, prev_block,merkle_root,timestamp,bits,nonce,n_tx):
        with self._driver.session() as session:
            result = session.write_transaction(self._new_block,block_id,version, prev_block,merkle_root,timestamp,bits,nonce,n_tx)
            if len(result) >0: app_log.info(f"CREATED BLOCK {block_id}")
            else: app_log.error(f"FAILED AT CREATING BLOCK {block_id}")
            #print(result)
            return
            
    def get_sixth_block_behind(self):
        with self._driver.session() as session:
            result = session.write_transaction(self._get_sixth_block_behind)
            return result
        
                     
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
    db = BlockChainDB("neo4j://10.0.0.30:7687", "neo4j", "wallet")
    db.config_constrains()
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
            app_log.info(f"cursor at {c} for file blk{file}.dat")
            coursor.close()
            return c
        except:
            if c == "finished":
                print(c)
                return True
            else:
                try: 
                    app_log.info(f"trying to recover file from backup for file blk{file}.dat.")
                    cursor = open(f"{file[:-4]}.txt.bck")
                    c = coursor.readline()
                    try:
                        c = int(c)
                        subprocess.call(f" cp cursors/cursor{file}.txt.bck cursors/cursor{file}.txt", shell=True)
                        app_log.info(f"succesfully recovered file from backup for file blk{file}.dat. Restored original file.")
                        coursor.close()
                        return c
                    except:
                        if c == "FINISHED!":
                            coursor.close()
                            print(c)
                            subprocess.call(f" cp cursors/cursor{file}.txt.bck cursors/cursor{file}.txt",shell=True)
                            app_log.info(f"Finished. Succesfully updated original file for file blk{file}.dat.")
                            return c
                        else:
                            app_log.info(f"Corrupted cursor files for file blk{file}.dat.")
                            raise Exception

                except:
                    app_log.info(f"No back-up file for file blk{file}.dat.")
                    raise Exception


    except:
        cursor  = open(f"cursors/cursor{file}.txt","w")
        app_log.info(f"No cursor file for file blk{file}.dat.")
        cursor.write(str(c))
        print(c)
        cursor.close()
        return c

     

def parse_blockchain(args):
    """
    args: ( file index (######),  database driver )
    """
    parsing_current=True
    continious_mode=False
    file = f"/home/pi/bitcoin/testnet3/blocks/blk{args[0]}.dat"
    db=args[1]
    print(f"parsing {file} on process {os.getpid()}")
    #print(f"driver {db}")
    
    while parsing_current:
        
        with open(file,"rb") as block_file:
            
            print(f"opened {file}")
            c = get_cursor(args[0])
            if c == "FINISHED!":
                print(f"We are done with file {file}")
                return
            if c !=0: 
                print(f"reading from {c} for file {file}.")
                block_file.read(c)

            #infinite loop to parse the blk#####.dat file. 
            #Only stops when an  error occures or the file is over.
            while True:
                

                try:
                    #parse the block using the class Block from the file block.py
                    this_block = Block.parse_from_blk(block_file)
                    #The last file is full of fake blocks that contains 0 transactions and bits =0. If we run into these
                    #fake blocks, we stop parsing to avoid filling the database with fake blocks and prevent from reading
                    #the up comming blocks.
                    if this_block.tx_hashes == 0 and int.from_bytes(this_block.bits,"big") == 0:
                        parsing_current=True   
                        continious_mode=True
                        print("No new blocks. Sleeping for a minute.")
                        sleep(60)
                        break
                    parsing_current=False   
                    #calculate the block id using the header of the parsed block:
                    #first the header is concatenated
                    header = this_block.version.to_bytes(4,"little")+this_block.prev_block[::-1]+this_block.merkle_root[::-1]+this_block.timestamp.to_bytes(4,"little") + this_block.bits + this_block.nonce
                    #then the concatenated header is hashed to get the block id.
                    block_id = hash256(header)[::-1]
                    app_log.info(f"new block from file: {file[-13:]}")
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
                        tx_id = tx.id()
                        coinbase = tx.is_coinbase()
                        #the parsed transaction is created in the database 
                        db.new_tx(block_id.hex(), tx.version, tx.locktime, tx_id, tx.tx_ins, tx.tx_outs, tx.segwit,transaction,coinbase)
                    
                    
                    if continious_mode:
                        continious_mode=False
                        sixth_block_behind = db.get_sixth_block_behind()
                        print(sixth_block_behind)
                        try: blk_id = sixth_block_behind[0]["x.id"]
                        except Exception as e:
                            print(e)
                            print(e.with_traceback)
                            print(f"couldn't get the sixth block behind for block {block_id.hex()}")
                            continue
                        try: add_height.main(blk_id)
                        except: print("A problem occured while adding the height to the last blocks.")
                        
                            
                    #the cursor is updated to start reading the next block. 8 bytes are added since some info comes before the flag. 
                    c += (this_block.size + 8)
                    print(f"cursor now at {c} for file {file}")
                    #print(c)
                    #the cursor file and its backup file are updated
                    cursor  = open(f"cursors/cursor{args[0]}.txt","w")
                    cursor.write(str(c))
                    cursor.close()
                    cursor  = open(f"cursors/cursor{args[0]}.txt.bck","w")
                    cursor.write(str(c))
                    cursor.close()


                except Exception as e:
                    size = os.stat(file).st_size
                    if c == size:
                        cursor  = open(f"cursors/cursor{args[0]}.txt","w")
                        cursor.write("FINISHED!")
                        cursor.close()
                        cursor  = open(f"cursors/cursor{args[0]}.txt.bck","w")
                        cursor.write("FINISHED!")
                        cursor.close()
                        
                        print(f"Finished {file} file. ")
                    else:
                        print(e)
                        print(e.with_traceback)
                    break




