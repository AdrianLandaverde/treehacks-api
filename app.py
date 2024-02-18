from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import requests
import os
from openai import OpenAI
from PIL import Image 
from pytesseract import pytesseract
from io import BytesIO

api_key= os.getenv('GOOGLE_API_KEY')
openaikey= os.getenv('OPENAI_API_KEY')

app = FastAPI()

origins = ["*"]

# Setup CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def hello_world():
    return {'message':'Hello World'}

def get_coordinates(address):
    url = 'https://maps.googleapis.com/maps/api/geocode/json'
    parameters = {
        'address': address, 
        'key': api_key,
    }

    response = requests.get(url, params=parameters)

    if response.status_code == 200:
        data = response.json()

        if data['status'] == 'OK':
            lat = data['results'][0]['geometry']['location']['lat']
            lon = data['results'][0]['geometry']['location']['lng']
        else:
            print(f'Error: {data["status"]}')
    else:
        print(f'Request failed with status code: {response.status_code}')
    
    return {'lat': lat, 'lon': lon}

@app.get("/coordinates")
async def coordinates(address: str):
    return get_coordinates(address)

@app.get("/restaurants")
async def restaurants(address: str):

    coordinates = get_coordinates(address)
    lat = coordinates['lat']
    lon = coordinates['lon']

    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        'keyword': 'sustainable veggie plant-based',
        'location': f"{lat},{lon}",
        'radius': 1500,
        'type': 'restaurant',
        'key': api_key
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        # The request was successful
        data = response.json()
        # Process the response data as needed
        print("Ok")
    else:
        # There was an error with the request
        print(f"Error: {response.status_code}, {response.text}")

    address= data['results'][0]['vicinity']
    name= data['results'][0]['name']

    complete= address + name
    swap = complete.replace(" ", "+")
    main_map= f"https://www.google.com/maps/embed/v1/place?key={api_key}&q={swap}"
    
    results= []

    for i in range(len(data["results"])):
        results.append(data["results"][i]["name"] + " " + data["results"][i]["vicinity"])

    base_link= f"https://maps.googleapis.com/maps/api/staticmap?center={lat},{lon}&zoom=13&size=600x400"
    markers=""
    for i in range(min([len(data["results"]), 9])):
        temp_lat=data["results"][i]["geometry"]["location"]["lat"]
        temp_lon=data["results"][i]["geometry"]["location"]["lng"]
        marker= f"&markers=color:red%7Clabel:{i+1}%7C{temp_lat},{temp_lon}"
        markers+= marker
    link= base_link+markers+"&key="+api_key

    results= []

    for i in range(len(data["results"])):
        results.append({"name":data["results"][i]["name"], "direction":data["results"][i]["vicinity"]})

    return {'names': results, 'main_map': main_map, 'static_map': link}

@app.get("/route_map")
async def route_map(origin: str, destination: str, mode: str):
    link= f"""https://www.google.com/maps/embed/v1/directions?key={api_key}&origin={origin}&destination={destination}&mode={mode.lower()}"""
    return {"link":link}

@app.get("/label_info")
def get_label_info(image_path:str):
    text= """40% VISCOSE
        33% NYLON
        25% POLYESTER
        2% CASHMERE /CACHEMIRE
        MAND WASH ‘COLD, WITH
        LIKE COLORS ONLY NON-
        CHLORINE BLEACH IF
        NEEDED ROLL IN TOWEL TO
        REMOVE EXCE
        MOISTURE, RES
        
        FLATTO."""

    client = OpenAI(api_key= openaikey)

    completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": """You are an expert in sustainable fashion. You know this about materials: 
            - High carbon efficiency: Linen, Hemp
            - Mid-level carbon efficiency: Carbon, Wool, Denim, Silk
            - Low carbon efficiency: Polyester, Rayon, Nylon 
        """},
        {"role": "user", "content": f"""Classify into one of this categories (High carbon efficiency, Mid-level carbon efficiency, Low carbon efficiency) the following label of the cloth. Based on the percentages and classification, give a rating from 1 (low efficiency) to 10 (high efficiency).   
        
        LABEL: {text}"""},
    ]
    )

    # Return the text
    return completion.choices[0].message.content
