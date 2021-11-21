from google.cloud import datastore
from flask import Blueprint, Flask, request, abort, render_template
import datetime
import json
import requests

import Blueprints.api.const as const
import Blueprints.auth.views as authHelp

api = Blueprint('api', __name__, template_folder='templates')
client = datastore.Client()

def attributesIncorrect(requestData: request, obj: str) -> bool:
    """
    Function that checks if all attributes exist or are valid in the request data.
    If not existing, or valid - return True
    """
    # get the appropriate list from const
    postItems = const.requiredAttributes[obj]

    # check that each item exists in our request keys
    for item in postItems:
        if item not in requestData.keys():
            return True

    return False

def getNutritionInfo(requestData: request) -> request:
    """
    Function that makes an API call to calorieninjas with the user's given amount, units, and food,
    which then returns an updated request object w/ the new relevant information
    """
    # create the url
    api_url = 'https://api.calorieninjas.com/v1/nutrition?query='
    query = str(requestData["amount"]) + requestData["units"] + ' ' + requestData["food"]
    
    # make the request to calorieninjas
    response = requests.get(api_url + query, headers={'X-Api-Key': const.calNinjaKey})
    results = response.json()

    # add the food information to my requestData
    for item in const.info:
        requestData[item] = results["items"][0][item]

    # return our updated requestData
    return requestData 

def updateNutritionInfo(requestData: request, obj: str) -> request:
    """
    Function that updates the items in const.info
    info = ["carbohydrates_g", "fats_g", "protein_g", "calories"]
    """
    if obj == "meals":
        obj2 = "foods"
    elif obj == "dates":
        obj2 = "meals"

    # iterate through the desired info and reset to zero
    for info in const.updateInfo:
        requestData[info] = 0

    # iterate through the requestData's list of foods or meals
    for item in requestData[obj2]:
        # get the specific info for that food/meal
        objKey = client.key(obj2, int(item["id"]))
        objItem = client.get(key=objKey)
        
        # iterate through the desired info and update info
        for info in const.updateInfo:
            requestData[info] += objItem[info]

    return requestData

def checkNeedUpdate(obj: str, id: int) -> None:
    """
    Function that checks if any of our updated IDs were related to another object
    If so, update that object with the new updated ID info
    """
    if obj == "meals":
        obj2 = "foods"
    elif obj == "dates":
        obj2 = "meals"
    query = client.query(kind=obj)
    results = list(query.fetch())

    # iterate through each result
    for result in results:
        if result[obj2]:
            # if the updated object is in the list, update the related object's info!
            for item in result[obj2]:
                if item["id"] == int(id):
                    result = updateNutritionInfo(result, obj)
                    client.put(result)

                    # special scenario - if food is updated in meals, check for dates that need their meals updated
                    if obj == "meals":
                        checkNeedUpdate("dates", int(result.key.id))                        

@api.route('/')
def index():
    return render_template('apiIntro.html')

@api.route('/<obj>', methods=['POST','GET'])
def postOneGetAll(obj: str):
    """
    This function allows the creation of our specific objects [obj]
    or to view all the objects.
    """
    # validate client is only asking for specific objects
    if obj not in const.objects:
        abort(404)

    # JWT not required
    if 'Authorization' in request.headers:
        payload = authHelp.verify_jwt(request)
        # error code was returned
        if type(payload) is tuple:
            return payload
    else:
        payload = None

    # client requested an unsupported MIME
    if "application/json" not in request.accept_mimetypes:
        return const.err["requestMIME"]

    if request.method == 'POST':
        content = request.get_json()

        if "id" in content.keys():
            return const.err["idChange"]

        if attributesIncorrect(content, obj):
            return const.err["missingAttributes"]
        
        newObj = datastore.entity.Entity(key=client.key(obj))

        # update each newObj in accordance to the obj
        if obj == "dates":
            # create datetime object
            date = datetime.datetime(int(content["year"]), int(content["month"]), int(content["day"]))
            newObj.update(
                {
                    "date": date.strftime("%x"),
                    "weekday": date.strftime("%A"),
                    "week": date.strftime("%W"),
                    "year": date.strftime("%Y"),
                    "day_number": date.strftime("%j"),
                    "meals": [],
                    "calories": 0,
                    "fats_g": 0,
                    "carbohydrates_g": 0,
                    "protein_g": 0
                }
            )
        
        elif obj == "meals":            
            newObj.update(
                {
                    "meal": content["meal"],
                    "ateWithOthers": bool(content["ateWithOthers"]),
                    "drankLiquid": bool(content["drankLiquid"]),
                    "wasTasty": bool(content["wasTasty"]),
                    "wasHealthy": bool(content["wasHealthy"]),
                    "foods": [],
                    "dates": [],
                    "calories": 0,
                    "fats_g": 0,
                    "carbohydrates_g": 0,
                    "protein_g": 0
                }                
            )

        elif obj == "foods":
            if content["units"] not in const.allowedUnits:
                return const.err["unitIsNotAllowed"]
            
            # make call to get food informations
            content = getNutritionInfo(content)

            newObj.update(
                {
                    "food": content["food"],
                    "amount": int(content["amount"]),
                    "units": content["units"],
                    "meals": [],
                    "calories": content["calories"],
                    "fats_g": content["fat_total_g"],
                    "carbohydrates_g": content["carbohydrates_total_g"],
                    "protein_g": content["protein_g"]
                }
            )
        # add an owner to object if 'Authorization' header was set
        newObj.update({"owner": payload["sub"] if payload else None})
        # place into datastore
        client.put(newObj)

        # add "id" and "self" to the results - not stored in datastore
        newObj["id"] = newObj.key.id
        newObj["self"] = request.base_url + "/" + str(newObj.key.id)
        
        return json.dumps(newObj), 201

    elif request.method == 'GET':
        query = client.query(kind=obj)
        
        # pagination - save the next_url as a key in the output
        # retrieve limit and offset by the URL, otherwise default to 5 and 0, respectively
        qLimit = int(request.args.get('limit', str(const.defaultPagination)))
        qOffset = int(request.args.get('offset', '0'))
        lIterator = query.fetch(limit= qLimit, offset=qOffset)
        pages = lIterator.pages
        results = list(next(pages))
        
        if payload:
            # if payload exists, check for objects that match sub only
            newResults = [res for res in results if res["owner"] == payload["sub"]]
        else:
            # only display objects without an owner
            newResults = [res for res in results if not res["owner"]]

        # add "id" and "self" to the results - not stored in datastore
        for result in newResults:
            result["id"] = result.key.id
            result["self"] = request.base_url + "/" + str(result.key.id)

            # check for all objs
            for item in const.objects:
                # check for key prior to indexing
                if item in result.keys():
                    # add self to all list items
                    for res in result[item]:
                        res["self"] = request.url_root + item + "/" + str(res["id"])

        output = {str(obj): newResults}
        
        # if more than 'offset' results are available, set the "next" value in the output
        if lIterator.next_page_token:
            nextOffset = qOffset + qLimit
            nextUrl = request.base_url + "?limit=" + str(qLimit) + "&offset=" + str(nextOffset)
            output["next"] = nextUrl

        return json.dumps(output), 200

    else:
        return const.err["allModifications"]

@api.route('/<obj>/<id>', methods=['DELETE','GET', 'PUT'])
def deleteGetPutOneItem(obj: str, id: str):
    """
    This function allows the delete of specific objects [obj]
    or to view a specific object, or to edit a specific object
    with a specific id [id]
    """
    # validate client is only asking for specific objects
    if obj not in const.objects:
        abort(404)

    # JWT not required
    if 'Authorization' in request.headers:
        payload = authHelp.verify_jwt(request)
        # error code was returned
        if type(payload) is tuple:
            return payload
    else:
        payload = None

    objKey = client.key(obj, int(id))
    objItem = client.get(key=objKey)

    # check that objItem isn't None
    if not objItem:
        return const.err["invalidID"]

    # check that objItem has an owner, otherwise just continue
    if objItem["owner"]:
        # no authentication provided
        if not payload:
            return const.err["unauthorized"]
        # check that the objItem's owner doesn't match
        if objItem["owner"] != payload["sub"]:
            return const.err["unauthorized"]

    if request.method == 'DELETE':
        # check for all objs
        for item in const.objects:
            # check for key prior to indexing
            if item in objItem.keys():
                # iterate through the list of object ids - all of these items reference our specified id
                for res in objItem[item]:
                    itemKey = client.key(item, int(res["id"]))
                    changedItem = client.get(key=itemKey)
                    
                    # remove the reference to the specified id
                    changedItem[obj].remove({"id": int(id)})
                    
                    # update our dates' or meals' nutritional information
                    if obj in const.objRel:                    
                        changedItem = updateNutritionInfo(changedItem, item)
                   
                    # make our update
                    client.put(changedItem)

        client.delete(objKey)
        return "", 204

    elif request.method == 'GET':
        # client requested an unsupported MIME
        if "application/json" not in request.accept_mimetypes:
            return const.err["requestMIME"]

        # add 'id' and 'self' to the object
        objItem["id"] = objItem.key.id
        objItem["self"] = request.base_url

        # check for all objs
        for item in const.objects:
            # check for key prior to indexing
            if item in objItem.keys():
                # add self to all list items
                for res in objItem[item]:
                    res["self"] = request.url_root + item + "/" + str(res["id"])

        return json.dumps(objItem), 200
    
    elif request.method == 'PUT':
        # update each item with the new info
        content = request.get_json()

        if "id" in content.keys():
            return const.err["idChange"]

        if attributesIncorrect(content, obj):
            return const.err["missingAttributes"]

        if obj == "dates":
            date = datetime.datetime(int(content["year"]), int(content["month"]), int(content["day"]))
            objItem.update(
                {
                    "date": date.strftime("%x"),
                    "weekday": date.strftime("%A"),
                    "week": date.strftime("%W"),
                    "year": date.strftime("%Y"),
                    "day_number": date.strftime("%j")
                }
            )
            client.put(objItem)

        elif obj == "meals":
            objItem.update(
                {
                    "meal": content["meal"],
                    "ateWithOthers": bool(content["ateWithOthers"]),
                    "drankLiquid": bool(content["drankLiquid"]),
                    "wasTasty": bool(content["wasTasty"]),
                    "wasHealthy": bool(content["wasHealthy"])
            })
            client.put(objItem)

        # if food, check meals + check dates
        elif obj == "foods":
            if content["units"] not in const.allowedUnits:
                return const.err["unitIsNotAllowed"]
            
            # make call to get food informations
            content = getNutritionInfo(content)
            objItem.update(
                {
                    "food": content["food"],
                    "amount": int(content["amount"]),
                    "units": content["units"],
                    "calories": content["calories"],
                    "fats_g": content["fat_total_g"],
                    "carbohydrates_g": content["carbohydrates_total_g"],
                    "protein_g": content["protein_g"]
                }
            )
            client.put(objItem)            
            checkNeedUpdate("meals", int(id))
        
        return "", 204

@api.route('/<obj>/<id1>/<id2>', methods=['PATCH', 'DELETE'])
def patchDelete(obj: str, id1: str, id2: str):
    """
    Function that allows creating + deleting relationships 
    between a date + a meal, and a meal + a food.
    """
    # JWT not required
    if 'Authorization' in request.headers:
        payload = authHelp.verify_jwt(request)
        # error code was returned
        if type(payload) is tuple:
            return payload
    else:
        payload = None

    if obj in const.objRel:
        if obj == "dates":
            obj2 = "meals"

        elif obj == "meals":
            obj2 = "foods"

        # get our specific objects
        obj1Key = client.key(obj, int(id1))
        obj2Key = client.key(obj2, int(id2))
        objItem1 = client.get(key=obj1Key)
        objItem2 = client.get(key=obj2Key)
    else:
        abort(404)

    # check that objItem1/objItem2 aren't None
    if not objItem1 or not objItem2:
        return const.err["invalidID"]

    # check that objItem1 has an owner, otherwise just continue
    if objItem1["owner"]:
        # no authentication provided
        if not payload:
            return const.err["unauthorized"]
        # check that the objItem1's owner doesn't match
        if (objItem1["owner"] != payload["sub"]):
            return const.err["unauthorized"]
    # check that objItem2 has an owner, otherwise just continue
    if objItem2["owner"]:
        # no authentication provided
        if not payload:
            return const.err["unauthorized"]
        # check that the objItem2's owner doesn't match     
        if (objItem2["owner"] != payload["sub"]):
            return const.err["unauthorized"]

    if request.method == 'PATCH':
        # add references to each other
        objItem1[obj2].append({"id": int(id2)})
        objItem2[obj].append({"id": int(id1)})
        
        # update our dates' or meals' nutritional information
        objItem1 = updateNutritionInfo(objItem1, obj)
        
        # make our updates
        client.put(objItem1)
        client.put(objItem2)

        # if object to associate was a meal, check if any dates need their nutritional info updated
        if obj == "meals":
            checkNeedUpdate("dates", int(id1))

        return "", 204

    elif request.method == 'DELETE': 
        # check that our obj1 contains obj2
        if objItem1[obj2]:
            # if our id2 is in obj1 list, remove it, otherwise return an error
            if {"id": int(id2)} in objItem1[obj2] and {"id": int(id1)} in objItem2[obj]:
                # if dates, remove meals. if meals, remove foods.
                objItem1[obj2].remove({"id": int(id2)})
                objItem2[obj].remove({"id": int(id1)})

                # update our dates' or meals' nutritional information
                objItem1 = updateNutritionInfo(objItem1, obj)

                # make our updates
                client.put(objItem1)
                client.put(objItem2)

                # if object to associate was a meal, check if any dates need their nutritional info updated
                if obj == "meals":
                    checkNeedUpdate("dates", int(id1))
            else:
                return const.err["invalidRelationship"]
                    
        return "", 204

@api.route('/<obj1>/<id1>/<obj2>', methods=['GET'])
def getRelationItems(obj1: str, id1: str, obj2: str):
    """
    Function that simply gets the list items 
    for specific combos
    """
    # JWT not required
    if 'Authorization' in request.headers:
        payload = authHelp.verify_jwt(request)
        # error code was returned
        if type(payload) is tuple:
            return payload
    else:
        payload = None
    
    # client requested an unsupported MIME
    if "application/json" not in request.accept_mimetypes:
        return const.err["requestMIME"]

    # check that given obj1 and obj2 are valid
    if (obj1, obj2) in const.objCombo:
        objKey = client.key(obj1, int(id1))
        objItem = client.get(key=objKey)
    else:
        abort(404)

    # check that our objItem exists
    if not objItem:
        return const.err["invalidID"]

    # check that objItem has an owner, otherwise just continue
    if objItem["owner"]:
        # check that the objItem's owner doesn't match or no authentication provided
        if (objItem["owner"] != payload["sub"]) or not payload:
            return const.err["unauthorized"]
    
    # add self to all items
    for item in objItem[obj2]:
        item["self"] = request.url_root + obj2 + "/" + str(item["id"])

    return json.dumps({obj2: objItem[obj2]}), 200