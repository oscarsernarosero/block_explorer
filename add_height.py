from time import sleep
from neo4j import GraphDatabase
import logging
from logging.handlers import RotatingFileHandler

log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')

logFile = 'log/add_height.log'

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
    def _add_height(tx, block_id):
    
        for i in range(10000):
            result = tx.run("MATCH (b:block {id:$block_id})-[:LINKS]->(n:block)-[:LINKS]->(:block)"
                            "-[:LINKS]->(:block)-[:LINKS]->(:block) "
                            "WITH b.height AS height, n AS next_block "
                            "SET next_block.height = height+1 "
                            "RETURN next_block.id ",
                            block_id=block_id)
            
                
            block_id = result.single().value()
            print(block_id)
        return block_id
        
    def add_height_batch(self,block_id=None):
        with self._driver.session() as session:
            result = session.write_transaction(self._add_height, block_id)
            #print(result)
            return result
        
    def add_height(self, block_id=None):
        #If no specific block to start from, then we start with the genesis block.
        if block_id is None: block_id="000000000933ea01ad0ee984209779baaec3ced90fa3f408719526f8d77f4943"
            
        for i in range(2000):
            print(i)
            block_id = db.add_height_batch(block_id)
            app_log.info(f"Last block {block_id} with height {i*10000}")
            
        
def main(block_id=None):
    db = FixCoinbaseTx("neo4j://localhost:7687", "neo4j", "wallet")
    db.add_height(block_id)
        