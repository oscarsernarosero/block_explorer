from time import sleep
from neo4j import GraphDatabase
import logging
from logging.handlers import RotatingFileHandler

log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')

logFile = 'log/delete_db.log'

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
    def _delete_batch(tx):
        for i in range(4):
            result = tx.run("MATCH (b:block)-[a]-(c)-[d]-(e) WITH a,b,c,d LIMIT 100000 DETACH DELETE a,b,c,d")
        return True
    
    @staticmethod
    def _delete_outputs_relationships(tx):
        result = tx.run("MATCH (b:output)-[a]-() WITH a,b LIMIT 10000 DETACH DELETE a,b")
        return True
    
    @staticmethod
    def _delete_addresses(tx):
        result = tx.run("MATCH (a:address) WITH a LIMIT 10000 DETACH DELETE a")
        return True
    
    @staticmethod
    def _delete_left_nodes_relationships(tx):
        result = tx.run("MATCH (a)-[b]-() WITH a,b LIMIT 100 DETACH DELETE a,b")
        return True
    
    @staticmethod
    def _delete_left_nodes(tx):
        result = tx.run("MATCH (a) WITH a LIMIT 100 DETACH DELETE a")
        return True
        
    def delete_batch(self):
        with self._driver.session() as session:
            result = session.write_transaction(self._delete_batch)
            #print(result)
            return result
    
    def delete_outputs_relationships(self):
        with self._driver.session() as session:
            result = session.write_transaction(self._delete_outputs_relationships)
            #print(result)
            return result
    
    def delete_addresses(self):
        with self._driver.session() as session:
            result = session.write_transaction(self._delete_addresses)
            #print(result)
            return result
        
    def delete_left_nodes_relationships(self):
        with self._driver.session() as session:
            result = session.write_transaction(self._delete_left_nodes_relationships)
            #print(result)
            return result
        
    def _delete_left_nodes(self):
        with self._driver.session() as session:
            result = session.write_transaction(self.delete_left_nodes)
            #print(result)
            return result
        
    def delete_all(self):
        while True:
            try:
                self.delete_batch()
                app_log.info(f"deleted a batch of blocks-tx-output.")
            except: break
                
        while True:
            try:
                self.delete_outputs_relationships()
                app_log.info(f"deleted a batch of outputs-relationships.")
            except: break
                
        while True:
            try:
                self.delete_addresses()
                app_log.info(f"deleted a batch of addresses.")
            except: break
                
        while True:
            try:
                self._delete_left_nodes_relationships()
                app_log.info(f"deleted a batch of nodes-relationships.")
            except: break
        return
    
        while True:
            try:
                self._delete_left_nodes()
                app_log.info(f"deleted a batch of nodes.")
            except: break
        return
        
def main():
    answer = input("You are about to delete the entire database. Are you sure? (y/n): ")
    if answer in "yY":
        confirm = input("Are you sure? (y/n): ")
        if confirm in "yY":
            db = DeleteDB("neo4j://localhost:7687", "neo4j", "wallet")
            sleep(1)
            db.delete_all()
        else: return
    else: return
    
if __name__ == "__main__": main()
        
    
    
    