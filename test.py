
import eel
#from flask import Flask
#app = Flask(__name__)
eel.init('web')


@eel.expose
#@app.route("/output")
def xor(str1,str2):

    str1=int.from_bytes(bytes.fromhex(str1),"big")
    str2=int.from_bytes(bytes.fromhex(str2),"big")
    return str1 ^ str2

#if __name__ == "__main__":
#	app.run()
eel.start('main.html')