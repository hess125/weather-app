# Backend for Weather App 

# Geocoding via OpenStreetMap is used
# Meteomatics API is used
# with Weather Model 

#---------- Import Libraries ----------
from flask import Flask, request
import requests
from requests.auth import HTTPBasicAuth
from datetime import timezone, datetime

app = Flask(__name__)

# Meteomatics API credentials
USERNAME = "kamal_hessa"
PASSWORD = "8J0tJZ9Fbi5SPjnn2g4M"


# ------- Weather Model -------
def calculate_comfort_index(temperature, precipitation, humidity=50):
    """
    Calculate how comfortable the weather feels on a scale of 0-100.
    Higher score means more comfortable for being outside.
    """
    comfort = 100  # maximum comfort
    
    # Temperature affects comfort - we like it around 20-25°C
    if temperature < 10:
        # Cold weather - reduce points based on how cold
        comfort -= (10 - temperature) * 3
    elif temperature > 35:
        # Very hot - reduce many points
        comfort -= (temperature - 35) * 4
    elif temperature > 30:
        # Warm - reduce some points
        comfort -= (temperature - 30) * 2
    
    if precipitation > 0:
        # More rain = less comfort, but do not reduce beyond 40 points
        comfort -= min(precipitation * 10, 40)
    
    # range
    return max(0, min(100, comfort))


def predict_activity_suitability(temperature, precipitation):
    """
    Rate different types of activities from 0-10 based on the weather.
    Returns a dictionary with activity types as keys and scores as values.
    """
    scores = {
        'outdoor_sports': 0,
        'water_activities': 0,
        'indoor_activities': 0,
        'walking': 0,
        'relaxation': 0
    }
    
    # Heavy rain = Indoor
    if precipitation > 2.0:
        scores['indoor_activities'] = 9
        scores['outdoor_sports'] = 2
        scores['water_activities'] = 1
        scores['walking'] = 3
        scores['relaxation'] = 7
    
    # Light rain = Balance
    elif precipitation > 0:
        scores['indoor_activities'] = 7
        scores['outdoor_sports'] = 4
        scores['walking'] = 5
        scores['relaxation'] = 6
    
    # No rain
    else:
        if temperature > 30:
            # Hot day - water activities
            scores['water_activities'] = 10
            scores['outdoor_sports'] = 6
            scores['walking'] = 5
            scores['indoor_activities'] = 4
            scores['relaxation'] = 8
        
        elif 20 <= temperature <= 30:
            # Perfect weather 
            scores['outdoor_sports'] = 9
            scores['walking'] = 10
            scores['water_activities'] = 7
            scores['indoor_activities'] = 5
            scores['relaxation'] = 7
        
        elif 10 <= temperature < 20:
            # Cool & pleasant
            scores['walking'] = 8
            scores['outdoor_sports'] = 7
            scores['indoor_activities'] = 6
            scores['relaxation'] = 6
            scores['water_activities'] = 3
        
        else:
            # Cold = indoor 
            scores['indoor_activities'] = 8
            scores['walking'] = 5
            scores['relaxation'] = 7
            scores['outdoor_sports'] = 4
            scores['water_activities'] = 1
    
    return scores


def generate_activity_recommendations(temperature, precipitation, comfort_index, suitability_scores):
    """
    This looks at the suitability scores and generates actual recommendations.
    """
    activities = []
    
    sorted_activities = sorted(suitability_scores.items(), key=lambda x: x[1], reverse=True)
    top_activity_type = sorted_activities[0][0]
    
    # Generate specific recommendations based on what's most suitable
    if top_activity_type == 'water_activities':
        activities.append("Perfect beach weather! Swimming and water sports highly recommended.")
        activities.append("Try kayaking, paddleboarding, or just relax by the water.")
    
    elif top_activity_type == 'outdoor_sports':
        activities.append("Great conditions for outdoor activities!")
        activities.append("Consider jogging, cycling, tennis, or team sports.")
    
    elif top_activity_type == 'walking':
        activities.append("Ideal weather for a pleasant walk or hike.")
        activities.append("Explore a nature trail or stroll through your neighborhood.")
    
    elif top_activity_type == 'indoor_activities':
        activities.append("Weather suggests indoor activities today.")
        activities.append("Visit a museum, gym, library, or enjoy a cozy cafe.")
    
    # Add extra advice based on comfort level
    if comfort_index < 40:
        activities.append("⚠️ Comfort level is low - weather may be challenging.")
    elif comfort_index > 80:
        activities.append("✨ Excellent comfort level - enjoy the beautiful weather!")
    
    return activities


def determine_weather_condition(temperature, precipitation):
    """
    a simple label like "Pleasant" or "Rainy".
    makes it easy to display a quick summary.
    """
    if precipitation > 5:
        return "Heavy Rain"
    elif precipitation > 0:
        return "Light Rain"
    elif temperature > 35:
        return "Very Hot"
    elif temperature > 28:
        return "Hot"
    elif temperature > 20:
        return "Pleasant"
    elif temperature > 10:
        return "Cool"
    else:
        return "Cold"


def analyze_weather(temperature, precipitation, humidity=50):
    """
    This is the main function 
    """

    comfort_index = calculate_comfort_index(temperature, precipitation, humidity)
    suitability_scores = predict_activity_suitability(temperature, precipitation)
    activities = generate_activity_recommendations(temperature, precipitation, comfort_index, suitability_scores)
    condition = determine_weather_condition(temperature, precipitation)
    
    #Return Information
    return {
        'comfort_index': round(comfort_index, 1),
        'condition': condition,
        'activity_suitability': suitability_scores,
        'recommended_activities': activities
    }


#------- Home Endpoint -------
@app.route("/", methods=["GET"])
def home():
    return {"message": "Weather API backend with model running!"}


#------- Weather Endpoint -------
@app.route("/weather", methods=["GET"])
def weather():
    """
    Main weather endpoint - fetches live data and runs it through the model.
    """
    city = request.args.get("city")
    date = request.args.get("date", "now")
    
    if not city:
        return {"error": "Please provide a city parameter, e.g., ?city=Dubai"}, 400
    
    # Get coordinates for the city using OpenStreetMap
    try:
        loc = requests.get(
            f"https://nominatim.openstreetmap.org/search?q={city}&format=json&limit=1",
            headers={"User-Agent": "WeatherHackathon/1.0"}
        ).json()
    except Exception as e:
        return {"error": f"Geocoding service error: {str(e)}"}, 500
    
    if not loc:  # If the list is empty
        return {"error": f"City '{city}' not found"}, 404
    
    lat = loc[0]["lat"]
    lon = loc[0]["lon"]
    
    # Check date
    if date == "now":
        date_obj = datetime.now(timezone.utc)
    else:
        try:
            date_obj = datetime.fromisoformat(date.replace("Z", ""))
        except ValueError:
            return {"error": "Invalid date format. Use ISO 8601, e.g., 2023-10-04T14:00:00Z"}, 400
    
    date_str = date_obj.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Fetch weather data from Meteomatics API
    weather_url = f"https://api.meteomatics.com/{date_str}/t_2m:C,precip_1h:mm,relative_humidity_2m:p/{lat},{lon}/json"
    
    try:
        response = requests.get(weather_url, auth=HTTPBasicAuth(USERNAME, PASSWORD)).json()
        temperature = response["data"][0]["coordinates"][0]["dates"][0]["value"]
        precipitation = response["data"][1]["coordinates"][0]["dates"][0]["value"]
        
        # get humidity, use default if not available
        try:
            humidity = response["data"][2]["coordinates"][0]["dates"][0]["value"]
        except (IndexError, KeyError):
            humidity = 50
            
    except (IndexError, KeyError, Exception) as e:
        return {"error": "Weather data unavailable for this time/location."}, 500
    
    # Run the weather data through model
    model_predictions = analyze_weather(temperature, precipitation, humidity)
    
    # Return the response
    response_data = {
        "location": city,
        "coordinates": {
            "lat": float(lat),
            "lon": float(lon)
        },
        "date": date_str,
        
        "weather": {
            "temperature_celsius": temperature,
            "precipitation_mm": precipitation,
            "humidity_percent": humidity
        },
        
        "predictions": {
            "condition": model_predictions['condition'],
            "comfort_index": model_predictions['comfort_index'],
            "activity_suitability": model_predictions['activity_suitability']
        },
        
        "recommended_activities": model_predictions['recommended_activities'],
        "note": "Predictions powered by weather analysis model"
    }
    
    return response_data


if __name__ == "__main__":
    app.run()
