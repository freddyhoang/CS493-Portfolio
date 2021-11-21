# ---------------------------------------------------------- # Default constants ---------------------------------------------------------------
# variable to determine the default pagination limit
defaultPagination = 5

# ------------------------------------------------- # CalorieNinja request API + foods API parameters-------------------------------------------
# calorieNinjas API key
calNinjaKey = "PTmd4hCgvmMoONE3rrpTGw==U5IVgutqkmuBP4ot"
# allowed units for foods
allowedUnits = ['grams', 'oz']
# interested information from api results
info = ["carbohydrates_total_g", "fat_total_g", "protein_g", "calories"]
updateInfo = ["carbohydrates_g", "fats_g", "protein_g", "calories"]

# ---------------------------------------------- # Validity checks --------------------------------------------------------------------
# list that determines what objects are valid for individual creation and modification
objects = ["dates", "meals", "foods"]

# list that determines what objects can have relationships
objRel = ["dates", "meals"]
objCombo = [("dates", "meals"), ("meals", "foods"), ("meals", "dates"), ("foods", "meals")]

# list that determines what attributes need to be present for post/put
requiredAttributes = {
    "dates": ["month", "day", "year"],
    "meals": ["meal", "ateWithOthers", "drankLiquid", "wasTasty", "wasHealthy"],
    "foods": ["food", "amount", "units"]
}

# ---------------------------- # error messages as a JSON object + the failure response code -----------------------------------------

err = {
    "missingAttributes": ({"Error": "The request object is missing at least one of the required attributes"}, 400),
    "invalidAttributes": ({"Error": "The request object doesn't support one of the entered attributes"}, 400),
    "unitIsNotAllowed": ({"Error": "The entered units aren't allowed, be sure to enter grams or pounds"}, 400),
    "duplicateDate": ({"Error": "The entered date has already been added by the current user"}, 400),
    "unauthorized": ({"Error": "The page or action you are trying to access cannot be performed without proper authentication"}, 401),
    "idChange": ({"Error": "No authority to change an ID"}, 403),
    "invalidID": ({"Error": "No object with this id exists"}, 404),
    "invalidRelationship": ({"Error": "These two objects aren't associated with one another"}, 404),
    "noPageFound": ({"Error": "This page does not exist"}, 404),
    "allModifications": ({"Error": "PUT or DELETE can be performed on a single object only, not all of them"}, 405),
    "requestMIME": ({"Error": "Client requested an unsupported MIME type"}, 406),
    "codeFail": ({"Error": "Generic response for failures within the code..."} , 500)
}