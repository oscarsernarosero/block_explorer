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

class DeleteDB(object):

    def __init__(self, uri=None, user=None, password=None, driver=None):
        if driver is None:
            self._driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=False)#REVISE LATER FOR ENCRYPTION!!!
        else:
            self._driver = driver

    def close(self):
        self._driver.close()
        
    @staticmethod    
    def _add_height(tx):
        result = tx.run("MATCH (b)-[a]-() WITH a,b LIMIT 1000 DETACH DELETE a,b")
        return True
        
    def add_height_batch(self):
        with self._driver.session() as session:
            result = session.write_transaction(self._add_height)
            #print(result)
            return result
        
    def add_height(self):
        while True:
            db.add_height_batch()
            app_log.info(f"deleted a batch.")
    return
        
def DeleteDB(block_id=None):
    answer = input("You are about to delete the entire database. Are you sure? (y/n): ")
    if answer in "yY":
        confirm = input("Are you sure? (y/n): ")
        if confirm in "yY":
            db = AddHeight("neo4j://localhost:7687", "neo4j", "wallet")
            db.add_height(block_id)
        else: return
    else: return
        
    
    
    