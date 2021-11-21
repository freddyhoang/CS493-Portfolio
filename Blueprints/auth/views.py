import requests
from functools import wraps
import json
from six.moves.urllib.request import urlopen
from flask_cors import cross_origin
from jose import jwt
from os import environ as env
from werkzeug.exceptions import HTTPException
from dotenv import load_dotenv, find_dotenv
from flask import Flask, Blueprint, jsonify, redirect, render_template, session, url_for, request, _request_ctx_stack, current_app
from authlib.integrations.flask_client import OAuth
from six.moves.urllib.parse import urlencode

import Blueprints.auth.const as const

auth = Blueprint('auth', __name__, template_folder='templates')
# register the current app to apply oAuthentication
oauth = OAuth(current_app)
auth0 = oauth.register(
    'auth0',
    client_id= const.CLIENT_ID,
    client_secret= const.CLIENT_SECRET,
    api_base_url= f"https://{const.DOMAIN}",
    access_token_url= f"https://{const.DOMAIN}/oauth/token",
    authorize_url= f"https://{const.DOMAIN}/authorize",
    client_kwargs={'scope': 'openid profile email'}
)

# This code is adapted from https://auth0.com/docs/quickstart/backend/python/01-authorization?_ga=2.46956069.349333901.1589042886-466012638.1589042885#create-the-jwt-validation-decorator

def requires_auth(f):
  @wraps(f)
  def decorated(*args, **kwargs):
    if 'profile' not in session:
      # Redirect to Login page here
      return redirect('/')
    return f(*args, **kwargs)

  return decorated

def verify_jwt(request) -> dict:
    """
    Verify the JWT in the request's Authorization header
    If authorization given, returns a dictionary with all of the user's credentials
    if not valid, returns an error
    """

    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization'].split()
        token = auth_header[1]
    else:
        return const.err["noHeader"]
    
    jsonurl = urlopen("https://"+ const.DOMAIN+"/.well-known/jwks.json")
    jwks = json.loads(jsonurl.read())
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.JWTError:
        return const.err["invalidHeader"]
    if unverified_header["alg"] == "HS256":
        return const.err["invalidHeader"]

    rsa_key = {}
    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }
    if rsa_key:
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=const.ALGORITHMS,
                audience=const.CLIENT_ID,
                issuer="https://"+ const.DOMAIN+"/"
            )
        except jwt.ExpiredSignatureError:
            return const.err["expiredToken"]
        except jwt.JWTClaimsError:
            return const.err["invalidClaims"]
        except Exception:
            return const.err["badAuthentication"]
        return payload
    else:
        return const.err["noRSA"]

@auth.route('/home')
def index():
    """
    Simply return what is going on
    """
    return render_template('home.html')

@auth.route('/callback')
def callback_handling():
    """
    Handling the callback from auth0
    """
    # Handles response from token endpoint
    auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()

    # Store the user information in flask session.
    session['jwt_payload'] = userinfo
    session['profile'] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }
    return redirect('/dashboard')

@auth.route('/login')
def login():
    """
    directs user to account creation or login
    """
    return auth0.authorize_redirect(redirect_uri=const.CALLBACK)

@auth.route('/dashboard')
@requires_auth
def dashboard():
    """
    display the dashboard w/ the user's JWT info + more
    """
    return render_template('dashboard.html',
                           userinfo=session['profile'],
                           userinfo_pretty=json.dumps(session['jwt_payload'], indent=4))

@auth.route('/logout')
def logout():
    """
    allow the user to logout of the session
    """
    # Clear session stored data
    session.clear()
    # Redirect user to logout endpoint
    params = {'returnTo': const.RETURN, 'client_id': const.CLIENT_ID}
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))

@auth.route('/users', methods = ["GET"])
def getUsers():
    """
    Generate a JWT for the management access API from the Auth0 domain
    and make a call to return all user info
    """
    
    # Get a Management Access Token from Auth0
    base_url = f"https://{const.DOMAIN}"
    payload =  { 
        'grant_type': "client_credentials" ,
        'client_id': const.CLIENT_ID,
        'client_secret': const.CLIENT_SECRET,
        'audience': f'https://{const.DOMAIN}/api/v2/'
    }
    # make call to get the JWT for management API
    response = requests.post(f'{base_url}/oauth/token', data=payload)
    oauthCall = response.json()
    access_token = oauthCall.get('access_token')

    # Add the token to the Authorization header of the request
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # Get all users - call API with our token
    res = requests.get(f'{base_url}/api/v2/users', headers=headers)
    return res.text, 200, {'Content-Type':'application/json'}

@auth.route('/logintest', methods=['POST'])
def login_user():
    """
    Generate a JWT from the Auth0 domain and return it
    Request: JSON body with 2 properties with "username" and "password"
    of a user registered with this Auth0 domain
    Response: JSON with the JWT as the value of the property id_token
    """
    content = request.get_json()

    body = {'grant_type': 'password',
            'username': content["username"],
            'password': content["password"],
            'client_id': const.CLIENT_ID,
            'client_secret': const.CLIENT_SECRET
    }

    headers = {'content-type': 'application/json'}
    url = f"https://{const.DOMAIN}/oauth/token"
    r = requests.post(url, json=body, headers=headers)
    return r.text, 200, {'Content-Type':'application/json'}

@auth.route('/decode', methods=['GET'])
def decode_jwt():
    """
    Decode the JWT supplied in the Authorization header
    """
    payload = verify_jwt(request)
    return payload