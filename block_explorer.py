from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import time
from time import localtime, strftime

from flask import Flask
app = Flask(__name__)


@app.route("/")
def get_block():
    rpc_user="ceazer"
    rpc_password="Lcctest1234"
    rpc_host="127.0.0.1"
    rpc_port="42069"
    Active = True
    last_block = {"hash":""}
    rpc_connection = AuthServiceProxy("http://%s:%s@%s:%s"%(rpc_user, rpc_password, rpc_host, rpc_port),timeout=15)
    best_block_hash = rpc_connection.getbestblockhash()
    new_block = rpc_connection.getblock(best_block_hash)

    return str(new_block)




if __name__ == "__main__":
    app.run()
    
