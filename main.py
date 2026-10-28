# Instalações:

import math
import requests
from datetime import datetime
from flask import Flask, render_template, request

app = Flask(__name__)

# Url da API Open Meteo:
url = "https://api.open-meteo.com/v1/forecast"

# Url da API GDACS:
url_2 = (
    "https://www.gdacs.org/gdacsapi/api/"
    "events/geteventlist/EVENTS4APP"
)

# Condições Climáticas e seus respectivos Ícones:
weather_conditions = {
    0: ("Céu limpo", "sunny.png"),
    1: ("Predominantemente limpo", "mainly_clear.png"),
    2: ("Parcialmente nublado", "partly_cloudy.png"),
    3: ("Nublado", "cloudy.png"),
    45: ("Neblina", "fog.png"),
    48: ("Neblina com geada", "fog.png"),
    51: ("Garoa fraca", "drizzle_light.png"),
    53: ("Garoa moderada", "drizzle_moderate.png"),
    55: ("Garoa intensa", "drizzle_heavy.png"),
    56: ("Garoa congelante fraca", "freezing_drizzle_light.png"),
    57: ("Garoa congelante intensa", "freezing_drizzle_heavy.png"),
    61: ("Chuva fraca", "rain_light.png"),
    63: ("Chuva moderada", "rain_moderate.png"),
    65: ("Chuva forte", "heavy_rain.png"),
    66: ("Chuva congelante fraca", "freezing_rain_light.png"),
    67: ("Chuva congelante forte", "freezing_rain_heavy.png"),
    71: ("Neve fraca", "snow_light.png"),
    73: ("Neve moderada", "snow_moderate.png"),
    75: ("Neve forte", "snow_heavy.png"),
    77: ("Grãos de neve", "snow_grains.png"),
    80: ("Pancadas de chuva fracas", "rain_showers_light.png"),
    81: ("Pancadas de chuva moderadas", "rain_showers_moderate.png"),
    82: ("Pancadas de chuva violentas", "eain_showers_heavy.png"),
    85: ("Pancadas de neve fracas", "snow_showers_light.png"),
    86: ("Pancadas de neve fortes", "snow_showers_heavy.png"),
    95: ("Trovoada", "thunderstorm.png"),
    96: ("Trovoada com granizo fraco", "thunderstorm_hail_light.png"),
    99: ("Trovoada com granizo forte", "thunderstorm_hail_heavy.png")
}

# Formatação da Data:


def format_date(date_value):
    return datetime.strptime(
        date_value, "%Y-%m-%d"
    ).strftime("%d/%m/%Y")

# Cálculo da distância entre dois pontos:


def cal_distance(lat1, lon1, lat2, lon2):
    earth_rad = 6371

    lat1, lon1, lat2, lon2 = map(
        math.radians, [lat1, lon1, lat2, lon2]
    )

    # Diferença de Latitude e Longitude:

    sub_latitude = lat2 - lat1
    sub_longitude = lon2 - lon1

    a = (
        math.sin(sub_latitude / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(sub_longitude / 2) ** 2
    )
    return 2 * earth_rad * math.asin(
        math.sqrt(min(1, a))
        )

# Obtendo os alertas climáticos:


def get_gdacs_alerts(latitude, longitude, radius_km=500):
    try:
        response = requests.get(url_2, timeout=15)
        response.raise_for_status()
        gdacs_data = response.json()

        if not isinstance(gdacs_data.get("features"), list):
            return [], "erro"

    except (requests.RequestException, ValueError):
        return [], "erro"

    event_types = {
        "EQ": "Terremoto",
        "TC": "Ciclone tropical",
        "FL": "Inundação",
        "VO": "Atividade vulcânica",
        "WF": "Incêndio florestal",
        "DR": "Seca",
        "TS": "Tsunami"
    }

    alerts = []

    for event in gdacs_data["features"]:
        properties = event.get("properties") or {}
        geometry = event.get("geometry") or {}

        if geometry.get("type") != "Point":
            continue

        coordinates = geometry.get("coordinates", [])

        if not isinstance(coordinates, list) or len(coordinates) < 2:
            continue

        try:
            lon_event = float(coordinates[0])
            lat_event = float(coordinates[1])
        except (TypeError, ValueError):
            continue

        distance = cal_distance(
            latitude,
            longitude,
            lat_event,
            lon_event
        )

        if distance > radius_km:
            continue

        event_type = properties.get("eventtype", "")

        alerts.append({
            "nome": properties.get("name") or "Evento sem nome",
            "tipo": event_types.get(event_type, "Desastre natural"),
            "nivel": properties.get("alertlevel") or "Não informado",
            "pais": properties.get("country") or "",
            "data": properties.get("fromdate") or "",
            "descricao": properties.get("description") or "",
            "distancia": round(distance, 1)
        })

    alerts.sort(key=lambda alert: alert["distancia"])

    if alerts:
        return alerts, "ok"

    return [], "vazio"


@app.route("/", methods=["GET", "POST"])
def inicio():

    # Recebe as coordenadas do formulário do HTML
    lat_text = request.form.get("lat", "")
    lon_text = request.form.get("lon", "")

    if not lat_text and not lon_text:
        lat_local = -31.77
        lon_local = -52.34

    else:
        try:
            lat_local = float(lat_text.replace(",", "."))
            lon_local = float(lon_text.replace(",", "."))

            if not (-90 <= lat_local <= 90):
                raise ValueError

            if not (-180 <= lon_local <= 180):
                raise ValueError

        except ValueError:
            return render_template(
                "index.html",
                erro_coordenadas=(
                    "Coordenadas inválidas. "
                    "Confira os valores informados."
                ),
                lat_atual=lat_text,
                lon_atual=lon_text
            )

    alerts, alerts_status = get_gdacs_alerts(
        lat_local,
        lon_local
    )

    # Parâmetros da requisição
    parameters = {
        "latitude": lat_local,
        "longitude": lon_local,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "precipitation",
            "pressure_msl",
            "wind_speed_10m",
            "weather_code",
            "cloud_cover"
        ],
        "daily": [
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min"
        ],
        "timezone": "America/Sao_Paulo",
        "forecast_days": 7
    }

    # Requisição à API
    response = requests.get(url, params=parameters, timeout=10)
    response.raise_for_status()
    data = response.json()

    # Dados atuais
    clima = data["current"]

    temperature = clima["temperature_2m"]
    humidity = clima["relative_humidity_2m"]
    precipitation = clima["precipitation"]
    pressure = clima["pressure_msl"]
    wind_speed = clima["wind_speed_10m"]
    weather_code = clima["weather_code"]
    feels_like = clima["apparent_temperature"]
    cloud_cover = clima["cloud_cover"]

    current_datetime = clima["time"]

    date = format_date(current_datetime.split("T")[0])
    time = current_datetime.split("T")[1]

    today_weather, weather_icon = weather_conditions.get(
        weather_code,
        ("Condição desconhecida", "unknown.png")
    )

    # Previsão diária
    forecast = data["daily"]

    max_temperature = forecast["temperature_2m_max"][0]
    min_temperature = forecast["temperature_2m_min"][0]

    # Segundo dia da previsão (Texto [0] e Ícone [1])
    day_2_data = weather_conditions.get(
        forecast["weather_code"][1],
        ("Condição desconhecida", "unknown.png")
    )
    weather_forecast_2 = day_2_data[0]
    icon_2 = day_2_data[1]
    max_temperature_2 = forecast["temperature_2m_max"][1]
    min_temperature_2 = forecast["temperature_2m_min"][1]
    dia_2 = format_date(forecast["time"][1])

    # Terceiro dia
    day_3_data = weather_conditions.get(
        forecast["weather_code"][2],
        ("Condição desconhecida", "unknown.png")
    )
    weather_forecast_3 = day_3_data[0]
    icon_3 = day_3_data[1]
    max_temperature_3 = forecast["temperature_2m_max"][2]
    min_temperature_3 = forecast["temperature_2m_min"][2]
    dia_3 = format_date(forecast["time"][2])

    # Quarto dia
    day_4_data = weather_conditions.get(
        forecast["weather_code"][3],
        ("Condição desconhecida", "unknown.png")
    )
    weather_forecast_4 = day_4_data[0]
    icon_4 = day_4_data[1]
    max_temperature_4 = forecast["temperature_2m_max"][3]
    min_temperature_4 = forecast["temperature_2m_min"][3]
    dia_4 = format_date(forecast["time"][3])

    # Quinto dia
    day_5_data = weather_conditions.get(
        forecast["weather_code"][4],
        ("Condição desconhecida", "unknown.png")
    )
    weather_forecast_5 = day_5_data[0]
    icon_5 = day_5_data[1]
    max_temperature_5 = forecast["temperature_2m_max"][4]
    min_temperature_5 = forecast["temperature_2m_min"][4]
    dia_5 = format_date(forecast["time"][4])

    # Sexto dia
    day_6_data = weather_conditions.get(
        forecast["weather_code"][5],
        ("Condição desconhecida", "unknown.png")
    )
    weather_forecast_6 = day_6_data[0]
    icon_6 = day_6_data[1]
    max_temperature_6 = forecast["temperature_2m_max"][5]
    min_temperature_6 = forecast["temperature_2m_min"][5]
    dia_6 = format_date(forecast["time"][5])

    # Sétimo dia
    day_7_data = weather_conditions.get(
        forecast["weather_code"][6],
        ("Condição desconhecida", "unknown.png")
    )
    weather_forecast_7 = day_7_data[0]
    icon_7 = day_7_data[1]
    max_temperature_7 = forecast["temperature_2m_max"][6]
    min_temperature_7 = forecast["temperature_2m_min"][6]
    dia_7 = format_date(forecast["time"][6])

    # Envio das variáveis para o HTML
    return render_template(
        "index.html",
        temperature=temperature,
        today_weather=today_weather,
        date=date,
        time=time,
        max_temperature=max_temperature,
        min_temperature=min_temperature,
        feels_like=feels_like,
        weather_icon=weather_icon,
        cloud_cover=cloud_cover,

        dia_2=dia_2,
        weather_forecast_2=weather_forecast_2,
        max_temperature_2=max_temperature_2,
        min_temperature_2=min_temperature_2,
        icon_2=icon_2,

        dia_3=dia_3,
        weather_forecast_3=weather_forecast_3,
        max_temperature_3=max_temperature_3,
        min_temperature_3=min_temperature_3,
        icon_3=icon_3,

        dia_4=dia_4,
        weather_forecast_4=weather_forecast_4,
        max_temperature_4=max_temperature_4,
        min_temperature_4=min_temperature_4,
        icon_4=icon_4,

        dia_5=dia_5,
        weather_forecast_5=weather_forecast_5,
        max_temperature_5=max_temperature_5,
        min_temperature_5=min_temperature_5,
        icon_5=icon_5,

        dia_6=dia_6,
        weather_forecast_6=weather_forecast_6,
        max_temperature_6=max_temperature_6,
        min_temperature_6=min_temperature_6,
        icon_6=icon_6,

        dia_7=dia_7,
        weather_forecast_7=weather_forecast_7,
        max_temperature_7=max_temperature_7,
        min_temperature_7=min_temperature_7,
        icon_7=icon_7,

        precipitation=precipitation,
        humidity=humidity,
        pressure=pressure,
        wind_speed=wind_speed,
        alerts=alerts,
        alerts_status=alerts_status
    )


if __name__ == "__main__":
    app.run(debug=True)
