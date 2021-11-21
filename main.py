from flask import Flask
import Blueprints.api.const as const

# import my blueprints
from Blueprints.api.views import api
from Blueprints.auth.views import auth

app = Flask(__name__)
app.secret_key = 'super1247SecretKey~!#!#(*&'

# register my blueprints
app.register_blueprint(api)
app.register_blueprint(auth)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)

@app.errorhandler(404)
def pageNotFound(error):
    return const.err["noPageFound"]

@app.errorhandler(500)
def genericFailure(error):
    return const.err["codeFail"]