from time import sleep
from neo4j import GraphDatabase

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

import logging
from logging.handlers import RotatingFileHandler

log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')

logFile = 'log/add_address.log'

my_handler = RotatingFileHandler(logFile, mode='a', maxBytes=10*1024*1024,backupCount=6, encoding=None, delay=0)
my_handler.setFormatter(log_formatter)
my_handler.setLevel(logging.INFO)

app_log = logging.getLogger('root')
app_log.setLevel(logging.INFO)

app_log.addHandler(my_handler)

class AddAddresses(object):

    def __init__(self, uri=None, user=None, password=None, driver=None):
        if driver is None:
            self._driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=False)#REVISE LATER FOR ENCRYPTION!!!
        else:
            self._driver = driver

    def close(self):
        self._driver.close()
        
    @staticmethod    
    def _create_addresses(tx,batch,testnet=True):
        """
        testnet is TRUE always. Change this for mainnet later.
        """
        batch_size = 5
        app_log.info(f" batch size {batch_size}. Represents the amount of blocks whose outputs are being encoded to addresses.")
        for height in range(batch*batch_size, batch_size*(batch + 1)):

            result = tx.run("MATCH (b:block {height:$height}) "
                             "MATCH (x)<-[:CREATES]-(t:transaction)<-[:CONTAINS]-(b) "
                             "RETURN x.script_pubkey, x.index, t.id", height=height)

            addresses = []
            for output in result.data():
                address = None
                addr_type = None
                raw_script_pubkey = output["x.script_pubkey"]
                b_sp = bytes.fromhex(raw_script_pubkey)
                length = encode_varint(len(b_sp))
                stream = BytesIO(length+b_sp)
                
                try: 
                    script_pubkey = Script.parse(stream)
                
                    if script_pubkey.is_p2pkh_script_pubkey(): 
                        address= h160_to_p2pkh_address(script_pubkey.cmds[2], testnet)
                        addr_type = "P2PKH"
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

                except: app_log.info(f"script parsing failed in tx {output['t.id']} index {output['x.index']} ")
                    
                if address is not None:
                    address_dict = {
                        "address":address,
                        "type": addr_type,
                        "tx_id":output["t.id"],
                        "index":output["x.index"]
                    }
                    addresses.append(address_dict)

            if len(addresses)>0:
                result = tx.run("FOREACH (address in $addresses | \n"
                                "MERGE (o:output {index:address.index})<-[:CREATES]-(:transaction {id:address.tx_id}) \n"
                                "MERGE (a:address {address:address.address}) SET a.type=address.type \n"
                                "MERGE (a)-[:HAS]->(o) )", addresses=addresses)

        
        return
    def create_address_batch(self,batch):
        with self._driver.session() as session:
            result = session.write_transaction(self._create_addresses,batch)
            #print(result)
            return result
        
        
    def create_addresses(self,node,core):
        nodes=4
        cores=4
        for batch in range(1800000//(nodes*cores)):
            batch = (node-1)*cores + nodes*cores*i + (core-1)
            self.create_address_batch(batch)
            app_log.info(f"batch {batch} from node {node}, core {core}")
        
def main(node,core):
    db = AddAddresses("neo4j://localhost:7687", "neo4j", "wallet")
    db.create_addresses(node=1,core=1)