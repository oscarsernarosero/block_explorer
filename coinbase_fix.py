from time import sleep
from neo4j import GraphDatabase
import logging
from logging.handlers import RotatingFileHandler

log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')

logFile = 'log/coinbase_fix.log'

my_handler = RotatingFileHandler(logFile, mode='a', maxBytes=10*1024*1024,backupCount=6, encoding=None, delay=0)
my_handler.setFormatter(log_formatter)
my_handler.setLevel(logging.INFO)

app_log = logging.getLogger('root')
app_log.setLevel(logging.INFO)

app_log.addHandler(my_handler)

class FixCoinbaseTx(object):

    def __init__(self, uri=None, user=None, password=None, driver=None):
        if driver is None:
            self._driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=False)#REVISE LATER FOR ENCRYPTION!!!
        else:
            self._driver = driver

    def close(self):
        self._driver.close()
        
    @staticmethod    
    def _fix_block(tx,batch):
        for height in range(5000*batch, 5000*batch + 5000):
            
            result = tx.run("MATCH (b:block {height:$height})-[:CONTAINS]->(coinbase:transaction)"
                             "-[s:SPENDS]->(o:output {index:4294967295}) "
                            "WITH s.witness as wit, s.script_sig as script_sig,b,coinbase,s "
                            "MERGE (b)-[c:COINBASE {witness:wit, script_sig:script_sig}]->(coinbase) "
                            "DELETE s",height=height)
            app_log.info(f"Fixed coinbase transaction for block with heigh {height}")
            return
        
    def fix_blocks_batch(self,batch):
        with self._driver.session() as session:
            result = session.write_transaction(self._fix_block,batch)
            #print(result)
            return 
        
    def fix_blocks(self,db,node, core):
        nodes=1
        cores=1
        for i in range(400):
            print(f"batch {i} for core {core} in node {node}.")
            batch = (node-1)*cores + nodes*cores*i + (core-1)
            self.fix_blocks_batch(batch)
        return 
        
def main(node,core):
    db = FixCoinbaseTx("neo4j://localhost:7687", "neo4j", "wallet")
    db.fix_blocks(db,node,core)
        