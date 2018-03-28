from flask import Flask

app = Flask(__name__)

if __name__ == '__main__':
    from endpoints import *
    app.run(host='0.0.0.0', port=9998, debug=True)
