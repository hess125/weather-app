#Backend for Weather App

## Geocoding via OpenStreetMap is used

from flask import Flask, request
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime

app = Flask(__name__)

# Meteomatics API credentials
USERNAME = "kamal_hessa"
PASSWORD = "8J0tJZ9Fbi5SPjnn2g4M"

# Home endpoint
@app.route("/", methods=["GET"])
def home():
    return {"message": "App backend is running!"}

#Weather endpoint
@app.route("/weather", methods=["GET"])
def weather():
    city = request.args.get("city")
    date = request.args.get("date", "now")

    if not city:
        return {"error": "Please provide a city parameter, e.g., Dubai"}, 400

    # Get coordinates for the city
    loc = requests.get(
        f"https://nominatim.openstreetmap.org/search?q={city}&format=json&limit=1",
        headers={"User-Agent": "WeatherHackathon/1.0"}
    ).json()

    if not loc:
        return {"error": f"City '{city}' not found"}, 404

    lat = loc[0]["lat"]
    lon = loc[0]["lon"]

    # Get datetime
    if date == "now":
        date_obj = datetime.utcnow()
    else:
        try:
            date_obj = datetime.fromisoformat(date.replace("Z", ""))
        except ValueError:
            return {"error": "Invalid date format. Use format: 2023-10-04T14:00:00Z"}, 400

    date_str = date_obj.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Temperature and rain at given datetime
    weather_url = f"https://api.meteomatics.com/{date_str}/t_2m:C,precip_1h:mm/{lat},{lon}/json"
    response = requests.get(weather_url, auth=HTTPBasicAuth(USERNAME, PASSWORD)).json()

    try:
        temperature = response["data"][0]["coordinates"][0]["dates"][0]["value"]
        precipitation = response["data"][1]["coordinates"][0]["dates"][0]["value"]
    except (IndexError, KeyError):
        return {"error": "Weather data unavailable for this time/location."}, 500

    # Activity suggestions
    activities = []
    note = "Activities based on forecast — actual weather conditions may vary."

    if precipitation > 0.0:
        activities.append("Stay indoors — visit a museum or read a book.")
    else:
        if temperature > 30:
            activities.append("Go for a swim!")
            activities.append("Try water sports or visit a beach.")
        elif 20 < temperature <= 30:
            activities.append("Have a picnic in the park!")
            activities.append("Go for a walk or bike ride.")
        else:
            activities.append("Enjoy a calm walk or light outdoor exercise.")

    #Information to return
    return {
        "location": city,
        "lat": float(lat),
        "lon": float(lon),
        "temperature": f"{temperature}°C",
        "precipitation_mm": precipitation,
        "activities": activities,
        "date": date_str,
        "note": note
    }

if __name__ == "__main__":
    app.run()
