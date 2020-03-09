#To use this test run in the terminal:
#                 $:     python3 test_rpc.py 
from slickrpc import Proxy

rpc_user="RobertPaulson"
rpc_password="FuckTheBanks"
rpc_host="127.0.0.1"
rpc_port="8332"

bitcoin = Proxy("http://%s:%s@127.0.0.1:8332"%(rpc_user, rpc_password))
hex = bitcoin.getrawtransaction ("a9a9db6b085df091ea1491e57df9177d128f6650ec9405148c9c2b64a835e88e", False,
                                 #"00000000e6f2148b04603d41257bb25b984787f6e5d0aadbfcda1b517806f9df"
                                 )
decoded_tx = bitcoin.decoderawtransaction (hex)
print(decoded_tx)

transactions = bitcoin.listtransactions("bc1qfm5repssqrnx9twvzw4glkcmk4z0gha5lnaeyp")
print(transactions)




