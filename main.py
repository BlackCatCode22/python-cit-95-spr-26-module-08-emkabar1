from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests

app = FastAPI()

USER_AGENT = "FCC-Student-App"

# Generalized City Configuration Registry
CITY_REGISTRY = {
    "Fresno": {
        "region": "US",
        "lat": 36.7378,
        "lon": -119.7871,
        "state": "CA",
    },
    "New York": {
        "region": "US",
        "lat": 40.7128,
        "lon": -74.0060,
        "state": "NY",
    },
    "London": {
        "region": "INTL",
        "lat": 51.5074,
        "lon": -0.1278,
        "state": "UK",
    },
}


def get_us_weather(lat: float, lon: float):
    """Fetches and normalizes weather from the National Weather Service."""
    headers = {"User-Agent": USER_AGENT}
    try:
        # Resolve coordinates to NWS Grid
        points_url = f"https://api.weather.gov/points/{lat},{lon}"
        points_res = requests.get(points_url, headers=headers, timeout=5        )
        if points_res.status_code != 200:
            return {"temp": "N/A", "condition": "Service Unavailable"}

        forecast_url = points_res.json()["properties"]["forecast"]

        # Fetch active forecast period
        forecast_res = requests.get(forecast_url, headers=headers, timeout=5)
        if forecast_res.status_code != 200:
            return {"temp": "N/A", "condition": "Forecast Error"}

        current_period = forecast_res.json()["properties"]["periods"][0]
        return {
            "temp": f"{current_period['temperature']}°{current_period['temperatureUnit']}",
            "condition": current_period["shortForecast"],
        }
    except Exception:
        return {"temp": "Error", "condition": "Connection Failed"}


def get_intl_weather(lat: float, lon: float):
    """Fetches and normalizes weather from Open-Meteo (Global)."""
    # Open-Meteo provides immediate data; requesting Fahrenheit matching standard NWS metrics
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&temperature_unit=fahrenheit"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code != 200:
            return {"temp": "N/A", "condition": "Service Unavailable"}

        data = res.json()["current_weather"]
        units = res.json()["current_weather_units"]

        # WMO Weather interpretation codes
        wmo_codes = {
            0: "Clear Sky",
            1: "Mainly Clear",
            2: "Partly Cloudy",
            3: "Overcast",
            45: "Foggy",
            48: "Depositing Rime Fog",
            51: "Light Drizzle",
            61: "Light Rain",
            71: "Light Snow",
            95: "Thunderstorm",
        }
        condition_code = data.get("weathercode", 0)
        condition_str = wmo_codes.get(condition_code, "Variable")

        return {
            "temp": f"{round(data['temperature'])}{units['temperature']}",
            "condition": condition_str,
        }
    except Exception:
        return {"temp": "Error", "condition": "Connection Failed"}


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    dashboard_data = []

    # Dynamic loop allows scaling out to 10+ cities cleanly without layout breakage
    for city_name, meta in CITY_REGISTRY.items():
        if meta["region"] == "US":
            weather = get_us_weather(meta["lat"], meta["lon"])
        else:
            weather = get_intl_weather(meta["lat"], meta["lon"])

        dashboard_data.append(
            {
                "name": city_name,
                "location": meta["state"],
                "temp": weather["temp"],
                "condition": weather["condition"],
            }
        )

    # Professional HTML Dashboard Template Injection
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Global Weather Metrics</title>
        <style>
            :root {{
                --bg-main: #0f172a;
                --card-bg: #1e293b;
                --text-main: #f8fafc;
                --text-muted: #94a3b8;
                --accent-blue: #38bdf8;
            }}
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background-color: var(--bg-main);
                color: var(--text-main);
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                padding: 20px;
            }}
            header {{
                text-align: center;
                margin-bottom: 40px;
            }}
            header h1 {{
                font-size: 2.5rem;
                font-weight: 700;
                letter-spacing: -0.05em;
                margin-bottom: 8px;
            }}
            .dashboard {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 24px;
                width: 100%;
                max-width: 1000px;
            }}
            .card {{
                background-color: var(--card-bg);
                border: 1px solid #334155;
                border-radius: 16px;
                padding: 32px;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }}
            .card:hover {{
                transform: translateY(-4px);
                box-shadow: 0 12px 20px -10px rgba(0,0,0,0.5);
                border-color: var(--accent-blue);
            }}
            .city {{
                font-size: 0.9rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.1em;
                color: var(--text-muted);
                margin-bottom: 16px;
            }}
            .temp {{
                font-size: 3.5rem;
                font-weight: 300;
                line-height: 1;
                margin-bottom: 12px;
                color: var(--text-main);
            }}
            .condition {{
                font-size: 1.1rem;
                color: var(--accent-blue);
                font-weight: 500;
            }}
        </style>
    </head>
    <body>
        <header>
            <h1>Weather Dashboard</h1>
        </header>
        
        <div class="dashboard">
    """

    for city in dashboard_data:
        html_content += f"""
                <div class="card">
                    <div class="city">{city['name']}, {city['location']}</div>
                    <div class="temp">{city['temp']}</div>
                    <div class="condition">{city['condition']}</div>
                </div>
        """

    html_content += """
            </div>
        </div>
    </body>
    </html>
    """
    return html_content