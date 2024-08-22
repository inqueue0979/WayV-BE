from flask import Flask
app = Flask(__name__)

@app.route('/')
def Hello():
    return 'WayV WA Server | 0822:0940'

if __name__ == '__main__':
    app.run(host='0.0.0.0')