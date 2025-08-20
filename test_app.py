from flask import Flask
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'test-secret-key')

@app.route('/')
def hello():
    return 'Hello World! Flask is working on Heroku.'

@app.route('/health')
def health():
    return {'status': 'ok', 'message': 'Application is running'}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)