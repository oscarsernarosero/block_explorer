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

class AddHeight(object):

    def __init__(self, uri=None, user=None, password=None, driver=None):
        if driver is None:
            self._driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=False, max_connection_lifetime=600)#REVISE LATER FOR ENCRYPTION!!!
        else:
            self._driver = driver

    def close(self):
        self._driver.close()
        
    @staticmethod    
    def _add_height(tx, block_id,n):
    
        last_data=""
        for i in range(n):
            try:
                result = tx.run("MATCH (b:block {id:$block_id})-[:LINKS]->(n:block) "
                            "WITH b.height AS height, n AS next_block "
                            "SET next_block.height = height+1 "
                            "RETURN next_block.id ",
                            block_id=block_id)
                data=result.data()
                last_data=data
                print(f"data: {data}, i {i}")
            except:
                print("\x1b[1;31;43m"+"Found possible stale blocks..."+ "\x1b[0m")
                result = tx.run("MATCH (b:block {id:$block_id})-[:LINKS]->(next_block:block) "
                            "RETURN next_block.id ",
                            block_id=block_id)
                data=result.data()
                last_data=data
                print(data)
                break
            if len(data)>1:    break
            elif len(data)==0: return True
            block_id = data[0]["next_block.id"]
            print(block_id)
            if i==(n-1):
                app_log.info(f"Finished with block {block_id}!")    
                return block_id
        
        print("\x1b[1;31;43m"+"Dealing with stale block..."+ "\x1b[0m")
        block_ids = last_data
        print(f"candidate block ids {block_ids}")
        for j in reversed(range(15)):
            query = "MATCH (b:block {id:$block_id})-[:LINKS]->(x:block)"
            for k in range(j):
                query+="-[:LINKS]->(:block)"
            query+="\nRETURN x.id"
            scores = {}
            for candidate in block_ids:
                result = tx.run(query, block_id=candidate["next_block.id"])
                data = result.data()
                _score=0
                if len(data)>0: _score=1
                score = {candidate["next_block.id"]:_score}
                print(f"score {score}. _score: {_score} result.data(): {data}")
                scores.update(score)
            print(f"scores: {scores}")
            winner_block=""
            xor =  0
            for block,result in scores.items():
                xor+=result
                print(f"block: {block}. result: {result}. xor: {xor}")
            if xor == 1:
                for block,result in scores.items():
                    if result == 1:
                        winner_block=block
                        print(f"Found winner block {winner_block}")
                        break
                print("fixing the height conflict...")
                for candidate in block_ids:
                    if candidate["next_block.id"] != winner_block:
                        stale_blocks=[ candidate["next_block.id"] ]
                        for j in reversed(range(15)):
                            query = "MATCH (b:block {id:$block_id})"
                            for k in range(j):query+="-[:LINKS]->(:block)"
                            query+="-[:LINKS]->(x:block)\nRETURN x.id"
                            result = tx.run(query, block_id=candidate["next_block.id"])
                            data = result.data()
                            if len(data)>0:stale_blocks.append(data[0]["x.id"])
                        print(f"deleting block {candidate['next_block.id']} and its whole fork:{stale_blocks}")
                        for stale_block in stale_blocks:
                            result = tx.run("MATCH (o:output)-[x:CREATES]-(t:transaction)-[c]-(b:block {id:$block_id})-[r]-() \n"
                                            "WHERE NOT (b)-[:CONTAINS]->(t)<-[:CONTAINS]-(:block) "
                                            "OR (b)-[:COINBASE]->(t)<-[:COINBASE]-(:block) \n"
                                            "OPTIONAL MATCH (o)-[w]-(:address) \n"
                                            "OPTIONAL MATCH (:output)-[y:SPENDS]-(t) \n"
                                            "DETACH DELETE b,c,r,o,x,t,w,y  ", block_id=stale_block)
                            
                            result = tx.run("MATCH (b:block {id:$block_id}) RETURN b", block_id=stale_block)
                            data = result.data()
                            print(f"does the block still exists? result.data: {data}")
                            if len(data)>0:
                                print(f"It does. So detach deleting now...")
                                result = tx.run("MATCH (b:block {id:$block_id}) " 
                                                "OPTIONAL MATCH (b)-[w]-(t:transaction)-[x]-(o) \n"
                                                "WHERE NOT (b)-[:CONTAINS]->(t)<-[:CONTAINS]-(:block)"
                                                "OPTIONAL MATCH (:output)-[y:SPENDS]-(t)--(b) \n"
                                                "WHERE NOT (b)-[:CONTAINS]->(t)<-[:CONTAINS]-(:block)\n"
                                                "DETACH DELETE b,w,t,x,o,y", block_id=stale_block)
                            else: print("deleted successfully")
                    else:
                        result = tx.run("MATCH (b:block {id:$block_id})<-[:LINKS]-(prev_block:block) \n"
                                        "RETURN prev_block.id \n", block_id=candidate["next_block.id"])
                        
                        _blkid = result.single().value()
                        
                        print(f"_blkid: {_blkid}")
                        
                        block_id = _blkid
                        
                break
            if j==0:
                print("\x1b[1;31;43m"+"Couldn't find the longest chain yet."+ "\x1b[0m")
                return False
        app_log.info(f"Finished with block {block_id}!")    
        return block_id
        
        
    def add_height_batch(self,block_id=None,n=1000):
        with self._driver.session() as session:
            result = session.write_transaction(self._add_height, block_id,n)
            #print(result)
            return result
        
    def add_height(self, db,block_id=None):
        #If no specific block to start from, then we start with the genesis block.
        if block_id is None: block_id="0000000000000000000000000000000000000000000000000000000000000000"
            
        for i in range(400000):
            print(i)
            block_id = db.add_height_batch(block_id,n=5)
            if isinstance(block_id,bool): 
                print("finished!")
                break
            app_log.info(f"Last block {block_id} with height {i*10000}")
            
        
def main(block_id=None):
    db = AddHeight("neo4j://10.0.0.30:7687", "neo4j", "wallet")
    db.add_height(db,block_id)
