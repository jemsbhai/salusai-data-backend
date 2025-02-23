import os
import pymongo
import json
import random
import hashlib
import time
import datetime
import requests
from flask import Response

from hashlib import sha256


def fhir_headers():
    return {
        "Content-Type": "application/fhir+json",
        "Authorization": "REDACTED TOKEN"
    }



def get_signed_url():
    
    agent_id = "REDACTED"
    api_key = "REDACTED"
    
    if not agent_id or not api_key:
        return {"error": "Missing required variables"}

    url = f"https://api.elevenlabs.io/v1/convai/conversation/get_signed_url?agent_id={agent_id}"
    headers = {"xi-api-key": api_key}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        return {"error": "Failed to get signed URL"}
    
    data = response.json()
    return {"signedUrl": data.get("signed_url")}



def sendsms(tonum, message):


    url = "https://us-central1-aiot-fit-xlab.cloudfunctions.net/sendsms"

    payload = json.dumps({
    "receiver": tonum,
    "message": message,
    "token": "REDACTED"
    })
    headers = {
    'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    # print(response.text)

def hashthis(st):


    hash_object = hashlib.md5(st.encode())
    h = str(hash_object.hexdigest())
    return h



def dummy(request):
    """Responds to any HTTP request.
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The response text or any set of values that can be turned into a
        Response object using
        `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """
    if request.method == 'OPTIONS':
        # Allows GET requests from origin https://mydomain.com with
        # Authorization header
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': '*',
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Max-Age': '3600',
            'Access-Control-Allow-Credentials': 'true'
        }
        return ('', 204, headers)

    # Set CORS headers for main requests
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': '*',
        'Access-Control-Allow-Headers': '*',
        'Access-Control-Max-Age': '3600',
        'Access-Control-Allow-Credentials': 'true'
    }

    if request.method == 'GET':

        mongostr = os.environ.get('MONGOSTR')
        client = pymongo.MongoClient(mongostr)
        db = client["salus"]

        retjson = {}
        
        if "getUrl" in request.args:

         
            retjson = get_signed_url()
            
            return Response(json.dumps(retjson), mimetype='application/json', headers = headers)
        
        if "getreading" in request.args:
            col = db.readings
            
            user_id = request.args.get('userid')  # Extract user ID from request parameters
            reading_name = request.args.get('readingName')  # Optional filter for specific reading type
            
            query = {"userid": user_id}
            if reading_name:
                query["readingName"] = reading_name
            
            reading_data = []
            
            for x in col.find(query):
                cdat = {}
                cdat['readingName'] = x['readingName']
                cdat['readingValue'] = x['readingValue']
                cdat['readingTS'] = x['readingTS']
                cdat['readingunit'] = x['readingunit']
                
                reading_data.append(cdat)
            
            retjson = {"readings": reading_data}
            
            return Response(json.dumps(retjson), mimetype='application/json', headers = headers)

        col = db.fakes

        datas = []

        for x in col.find():
            d = {}
            d['ts'] = x['ts']

            datas.append(d)

        retjson['data'] = datas

        return Response(json.dumps(retjson), mimetype='application/json', headers = headers)




    request_json = request.get_json()


    mongostr = os.environ.get('MONGOSTR')
    client = pymongo.MongoClient(mongostr)
    db = client["salus"]


    retjson = {}

    action = request_json['action']


    if action == "storeuserdata":
        col = db.identities if request.get_json().get("use_real") else db.fakes
        
        request_data = request.get_json()
        user_id = request_data['userid']
        
        user_data = col.find_one({"userid": user_id})
        if not user_data:
            retjson = {"message": "User not found"}
            return Response(json.dumps(retjson), mimetype='application/json', headers=headers)
        
        fhir_patient = {
            "resourceType": "Patient",
            "id": user_id,
            "name": [{
                "use": "official",
                "family": user_data["last_name"],
                "given": [user_data["first_name"]]
            }],
            "gender": user_data["gender"].lower(),
            "telecom": [{"system": "phone", "value": user_data["phone_number"]}],
            "address": [{"text": user_data["address"]}],
            "identifier": [{"system": "https://your-organization.com/patient-ids", "value": user_id}]
        }
        
        response = requests.post("https://epic.fhirserver.com/Patient", json=fhir_patient, headers=fhir_headers())
        
        if response.status_code in [200, 201]:
            retjson = {"message": "User data stored in EPIC successfully"}
        else:
            retjson = {"message": "Failed to store user data", "error": response.text}
        
        return Response(json.dumps(retjson), mimetype='application/json', headers=headers)

    if action == "retrieveuserdata":
        request_data = request.get_json()
        user_id = request_data['userid']
        
        response = requests.get(f"https://epic.fhirserver.com/Patient/{user_id}", headers=fhir_headers())
        
        if response.status_code == 200:
            epic_user_data = response.json()
            retjson = {"message": "User data retrieved successfully", "data": epic_user_data}
        else:
            retjson = {"message": "Failed to retrieve user data", "error": response.text}
        
        return Response(json.dumps(retjson), mimetype='application/json', headers=headers)





    if action == "getreadings":
        col = db.readings

        found = 0
        user_id = request_json['userid']  # Extract user ID from request JSON

        reading_names = request_json.get('reading_names', [])
        reading_data = []

        query = {"userid": user_id}
        if reading_names:
            query["readingName"] = {"$in": reading_names}

        for x in col.find(query):
            cdat = {}
            cdat['readingName'] = x['readingName']
            cdat['readingValue'] = x['readingValue']
            cdat['readingTS'] = x['readingTS']
            cdat['readingunit'] = x['readingunit']

            reading_data.append(cdat)

        retjson['readings'] = reading_data

        return Response(json.dumps(retjson), mimetype='application/json', headers = headers)




    if action == "getAQI":

        url = "http://api.openweathermap.org/data/2.5/air_pollution?lat=28.5470276&lon=-81.3860283&appid=13363dac9972f9c90c481124c1bca05d"

        payload = {}
        headers = {}

        response = requests.request("GET", url, headers=headers, data=payload)

        # print(response.text)

        retjson['airquality'] = response.json()

        return Response(json.dumps(retjson), mimetype='application/json', headers = headers)


    if action == "addreading":
        col = db.readings
        
        user_id = request_json['userid']  # Extract user ID from request JSON
        reading_name = request_json['readingName']
        reading_value = request_json['readingValue']
        reading_unit = request_json['readingunit']
        reading_ts = request_json.get('readingTS', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        reading_data = {
            "userid": user_id,
            "readingName": reading_name,
            "readingValue": reading_value,
            "readingTS": reading_ts,
            "readingunit": reading_unit
        }
        
        col.insert_one(reading_data)
        
        retjson['message'] = "Reading added successfully"
        return Response(json.dumps(retjson), mimetype='application/json', headers = headers)


    if action == "getappointments":
        col = db.appointments
        
        request_data = request.get_json()
        user_id = request_data['userid']  # Extract user ID from request JSON
        
        query = {"userid": user_id}
        appointment_data = []
        
        for x in col.find(query):
            appt = {}
            appt['doctor_name'] = x['doctor_name']
            appt['medical_facility'] = x['medical_facility']
            appt['appointment_datetime'] = x['appointment_datetime']
            appt['status'] = x['status']
            appt['doctor_type'] = x['doctor_type']
            appt['appointment_type'] = x['appointment_type']
            
            appointment_data.append(appt)
        
        retjson = {"appointments": appointment_data}
        
        return Response(json.dumps(retjson), mimetype='application/json', headers = headers)


    if action == "addappointment":
        col = db.appointments
        
        request_data = request.get_json()
        user_id = request_data['userid']
        doctor_name = request_data['doctor_name']
        medical_facility = request_data['medical_facility']
        appointment_datetime = request_data['appointment_datetime']
        status = request_data.get('status', 'upcoming')
        doctor_type = request_data['doctor_type']
        appointment_type = request_data['appointment_type']
        
        appointment_data = {
            "userid": user_id,
            "doctor_name": doctor_name,
            "medical_facility": medical_facility,
            "appointment_datetime": appointment_datetime,
            "status": status,
            "doctor_type": doctor_type,
            "appointment_type": appointment_type
        }
        
        col.insert_one(appointment_data)
        
        retjson = {"message": "Appointment added successfully"}
        
        return Response(json.dumps(retjson), mimetype='application/json', headers=headers)

    if action == "getprescriptions":
        col = db.prescriptions
        
        request_data = request.get_json()
        user_id = request_data['userid']
        
        query = {"userid": user_id}
        prescription_data = []
        
        for x in col.find(query):
            pres = {}
            pres['prescription_id'] = x['prescription_id']
            pres['prescriber_id'] = x['prescriber_id']
            pres['medical_facility'] = x['medical_facility']
            pres['status'] = x['status']
            pres['drug_name'] = x['drug_name']
            pres['dosage'] = x['dosage']
            
            prescription_data.append(pres)
        
        retjson = {"prescriptions": prescription_data}
        
        return Response(json.dumps(retjson), mimetype='application/json', headers=headers)

    if action == "addprescription":
        col = db.prescriptions
        
        request_data = request.get_json()
        prescription_id = request_data['prescription_id']
        user_id = request_data['userid']
        prescriber_id = request_data['prescriber_id']
        medical_facility = request_data['medical_facility']
        status = request_data['status']
        drug_name = request_data['drug_name']
        dosage = request_data['dosage']
        
        prescription_data = {
            "prescription_id": prescription_id,
            "userid": user_id,
            "prescriber_id": prescriber_id,
            "medical_facility": medical_facility,
            "status": status,
            "drug_name": drug_name,
            "dosage": dosage
        }
        
        col.insert_one(prescription_data)
        
        retjson = {"message": "Prescription added successfully"}
        
        return Response(json.dumps(retjson), mimetype='application/json', headers=headers)

    if action == "getpillrecords":
        col = db.pillrecords
        
        request_data = request.get_json()
        user_id = request_data['userid']
        
        query = {"userid": user_id}
        pill_data = []
        
        for x in col.find(query):
            pill = {}
            pill['prescription_id'] = x['prescription_id']
            pill['userid'] = x['userid']
            pill['dosage_amount'] = x['dosage_amount']
            pill['dosage_time'] = x['dosage_time']
            pill['status'] = x['status']
            pill['timestamp'] = x['timestamp']
            
            pill_data.append(pill)
        
        retjson = {"pills": pill_data}
        
        return Response(json.dumps(retjson), mimetype='application/json', headers=headers)

    if action == "addpillrecord":
        col = db.pillrecords
        
        request_data = request.get_json()
        prescription_id = request_data['prescription_id']
        user_id = request_data['userid']
        dosage_amount = request_data['dosage_amount']
        dosage_time = request_data['dosage_time']
        status = request_data['status']
        timestamp = request_data['timestamp']
        
        pill_data = {
            "prescription_id": prescription_id,
            "userid": user_id,
            "dosage_amount": dosage_amount,
            "dosage_time": dosage_time,
            "status": status,
            "timestamp": timestamp
        }
        
        col.insert_one(pill_data)
        
        retjson = {"message": "Pill record added successfully"}
        
        return Response(json.dumps(retjson), mimetype='application/json', headers=headers)

    if action == "updatepillstatus":
        col = db.pillrecords
        
        request_data = request.get_json()
        prescription_id = request_data['prescription_id']
        user_id = request_data['userid']
        dosage_time = request_data['dosage_time']
        new_status = request_data['status']
        
        query = {
            "prescription_id": prescription_id,
            "userid": user_id,
            "dosage_time": dosage_time
        }
        
        existing_record = col.find_one(query)
        if existing_record:
            result = col.update_one(query, {"$set": {"status": new_status}})
            retjson = {"message": "Pill status updated successfully"}
        else:
            retjson = {"message": "No matching record found"}
        
        return Response(json.dumps(retjson), mimetype='application/json', headers=headers)

    if action == "countmissedpills":
        col = db.pillrecords
        
        request_data = request.get_json()
        user_id = request_data['userid']
        start_date = request_data['start_date']
        end_date = request_data['end_date']
        
        query = {
            "userid": user_id,
            "status": "missed",
            "dosage_time": {"$gte": start_date, "$lte": end_date}
        }
        
        missed_count = col.count_documents(query)
        
        retjson = {"missed_pills": missed_count}
        
        return Response(json.dumps(retjson), mimetype='application/json', headers=headers)


    if action == "getexerciseminutes":
        col = db.exerciserecords
        
        request_data = request.get_json()
        user_id = request_data['userid']
        start_date = request_data['start_date']
        end_date = request_data['end_date']
        
        query = {
            "userid": user_id,
            "exercise_date": {"$gte": start_date, "$lte": end_date}
        }
        
        total_minutes = sum(x["minutes_exercised"] for x in col.find(query))
        
        retjson = {"total_exercise_minutes": total_minutes}
        
        return Response(json.dumps(retjson), mimetype='application/json', headers=headers)

    if action == "getaverageheartrate":
        col = db.exerciserecords
        
        request_data = request.get_json()
        user_id = request_data['userid']
        start_date = request_data['start_date']
        end_date = request_data['end_date']
        
        query = {
            "userid": user_id,
            "exercise_date": {"$gte": start_date, "$lte": end_date}
        }
        
        records = list(col.find(query))
        if records:
            avg_heartrate = sum(x["average_heartrate"] for x in records) / len(records)
        else:
            avg_heartrate = 0
        
        retjson = {"average_heartrate": avg_heartrate}
        
        return Response(json.dumps(retjson), mimetype='application/json', headers=headers)

    if action == "addexerciserecord":
        col = db.exerciserecords
        
        request_data = request.get_json()
        user_id = request_data['userid']
        exercise_date = request_data['exercise_date']
        exercise_type = request_data['exercise_type']
        minutes_exercised = request_data['minutes_exercised']
        average_heartrate = request_data['average_heartrate']
        calories_burned = request_data['calories_burned']
        
        exercise_data = {
            "userid": user_id,
            "exercise_date": exercise_date,
            "exercise_type": exercise_type,
            "minutes_exercised": minutes_exercised,
            "average_heartrate": average_heartrate,
            "calories_burned": calories_burned
        }
        
        col.insert_one(exercise_data)
        
        retjson = {"message": "Exercise record added successfully"}
        
        return Response(json.dumps(retjson), mimetype='application/json', headers=headers)

    if action == "getexerciserecords":
        col = db.exerciserecords
        
        request_data = request.get_json()
        user_id = request_data['userid']
        
        query = {"userid": user_id}
        exercise_data = []
        
        for x in col.find(query):
            record = {}
            record['exercise_date'] = x['exercise_date']
            record['exercise_type'] = x['exercise_type']
            record['minutes_exercised'] = x['minutes_exercised']
            record['average_heartrate'] = x['average_heartrate']
            record['calories_burned'] = x['calories_burned']
            
            exercise_data.append(record)
        
        retjson = {"exercise_records": exercise_data}
        
        return Response(json.dumps(retjson), mimetype='application/json', headers=headers)



    retstr = "action not done"

    if request.args and 'message' in request.args:
        return request.args.get('message')
    elif request_json and 'message' in request_json:
        return request_json['message']
    else:
        return retstr

