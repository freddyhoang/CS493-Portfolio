#--------------------------------------------- Application constants ---------------------------------------------#
CLIENT_ID = 'Pk3Bwvh8jJvhsCT7o3ForENlj6V79coY'
CLIENT_SECRET = 'd5fYvhUxUe_8beHGeHLDMcp6dI4Y4VL6ket22v-Btgw6h54Q9z1BGh02v-N3xXgq'
DOMAIN = 'fitnesstracker-332400.us.auth0.com'
ALGORITHMS = ["RS256"]
CALLBACK = "https://fitnesstracker-332400.wl.r.appspot.com/callback"
RETURN = "https://fitnesstracker-332400.wl.r.appspot.com/login"

# ---------------------------- # error messages as a JSON object + the failure response code -----------------------------------------
err = {
    "noHeader": ({"Error": "Authorization header is missing"}, 401),
    "invalidHeader": ({"Error": "Invalid header. Use an RS256 signed JWT Access Token"}, 401),
    "expiredToken": ({"Error": "token is expired"}, 401),
    "invalidClaims": ({"Error": "incorrect claims, please check the audience and issuer"}, 401),
    "badAuthentication": ({"Error": "Unable to parse authentication token."}, 401),
    "noRSA": ({"Error": "No RSA key in JWKS"}, 401)
}