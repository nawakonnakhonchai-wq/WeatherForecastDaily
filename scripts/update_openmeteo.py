"""ดึงสภาพอากาศปัจจุบัน + พยากรณ์ 10 วัน ของ 77 จังหวัดจาก Open-Meteo

ใช้แค่ Python standard library (ไม่ต้อง pip install อะไร)
ผลลัพธ์:
  provinces_weather.json     ข้อมูลเต็ม (ปัจจุบัน + รายวัน 10 วัน) สำหรับหน้าเว็บ
  provinces_weather.geojson  จุดจังหวัด + ค่าปัจจุบัน/วันนี้ สำหรับโปรแกรม GIS

รันเอง:  python scripts/update_openmeteo.py
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROVINCES_FILE = ROOT / "provinces.json"
OUT_JSON = ROOT / "provinces_weather.json"
OUT_GEOJSON = ROOT / "provinces_weather.geojson"

API_URL = "https://api.open-meteo.com/v1/forecast"
# Open-Meteo นับคำขอที่เกิน 10 ตัวแปรเป็น (จำนวนตัวแปร / 10) calls ต่อพิกัด
# 17 ตัวแปร ≈ 1.7 calls x 77 จุด x 24 ครั้ง ≈ 3,150 calls/วัน (โควตาฟรี 10,000/วัน)
CURRENT_VARS = ["temperature_2m", "apparent_temperature", "relative_humidity_2m", "precipitation",
                "weather_code", "wind_speed_10m", "wind_direction_10m", "visibility", "is_day"]
DAILY_VARS = ["weather_code", "temperature_2m_max", "temperature_2m_min",
              "precipitation_probability_max", "precipitation_sum", "uv_index_max", "sunrise", "sunset"]
FORECAST_DAYS = 10
TZ_NAME = "Asia/Bangkok"
BKK = timezone(timedelta(hours=7))

# รหัสสภาพอากาศ WMO -> คำอธิบายภาษาไทย / อังกฤษ
WMO = {
    0: ("ท้องฟ้าแจ่มใส", "Clear sky"),
    1: ("มีเมฆเล็กน้อย", "Mainly clear"),
    2: ("มีเมฆบางส่วน", "Partly cloudy"),
    3: ("มีเมฆมาก", "Overcast"),
    45: ("มีหมอก", "Fog"),
    48: ("หมอกน้ำค้างแข็ง", "Depositing rime fog"),
    51: ("ฝนละอองเล็กน้อย", "Light drizzle"),
    53: ("ฝนละออง", "Moderate drizzle"),
    55: ("ฝนละอองหนาแน่น", "Dense drizzle"),
    56: ("ฝนละอองเยือกแข็งเล็กน้อย", "Light freezing drizzle"),
    57: ("ฝนละอองเยือกแข็ง", "Dense freezing drizzle"),
    61: ("ฝนตกเล็กน้อย", "Slight rain"),
    63: ("ฝนตกปานกลาง", "Moderate rain"),
    65: ("ฝนตกหนัก", "Heavy rain"),
    66: ("ฝนเยือกแข็งเล็กน้อย", "Light freezing rain"),
    67: ("ฝนเยือกแข็งหนัก", "Heavy freezing rain"),
    71: ("หิมะตกเล็กน้อย", "Slight snow"),
    73: ("หิมะตกปานกลาง", "Moderate snow"),
    75: ("หิมะตกหนัก", "Heavy snow"),
    77: ("เกล็ดหิมะ", "Snow grains"),
    80: ("ฝนซู่เล็กน้อย", "Slight rain showers"),
    81: ("ฝนซู่ปานกลาง", "Moderate rain showers"),
    82: ("ฝนซู่หนักมาก", "Violent rain showers"),
    85: ("หิมะซู่เล็กน้อย", "Slight snow showers"),
    86: ("หิมะซู่หนัก", "Heavy snow showers"),
    95: ("พายุฝนฟ้าคะนอง", "Thunderstorm"),
    96: ("พายุฝนฟ้าคะนอง มีลูกเห็บเล็กน้อย", "Thunderstorm with slight hail"),
    99: ("พายุฝนฟ้าคะนอง มีลูกเห็บหนัก", "Thunderstorm with heavy hail"),
}


def describe(code):
    if code is None:
        return (None, None)
    return WMO.get(int(code), ("ไม่ทราบ", "Unknown"))


def fetch(provinces, retries=4):
    params = {
        "latitude": ",".join(f"{p['lat']:.4f}" for p in provinces),
        "longitude": ",".join(f"{p['lon']:.4f}" for p in provinces),
        "current": ",".join(CURRENT_VARS),
        "daily": ",".join(DAILY_VARS),
        "timezone": TZ_NAME,
        "forecast_days": FORECAST_DAYS,
    }
    url = API_URL + "?" + urllib.parse.urlencode(params, safe=",")
    req = urllib.request.Request(url, headers={"User-Agent": "WeatherForecastDaily/1.0 (GitHub Actions)"})
    delay = 5
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.load(resp)
            # เมื่อส่งหลายพิกัด API จะตอบเป็น list เรียงตามลำดับพิกัด
            return data if isinstance(data, list) else [data]
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            body = ""
            if isinstance(e, urllib.error.HTTPError):
                body = e.read().decode("utf-8", "replace")[:300]
                if 400 <= e.code < 500 and e.code != 429:
                    raise SystemExit(f"Open-Meteo ตอบ {e.code}: {body}")
            print(f"ครั้งที่ {attempt} ล้มเหลว: {e} {body}", file=sys.stderr)
            if attempt == retries:
                raise
            time.sleep(delay)
            delay *= 2


def build(provinces, results, fetched_at):
    if len(results) != len(provinces):
        raise SystemExit(f"จำนวนผลลัพธ์ ({len(results)}) ไม่ตรงกับจำนวนจังหวัด ({len(provinces)})")

    out = []
    for p, r in zip(provinces, results):
        cur = r.get("current", {})
        cur_th, cur_en = describe(cur.get("weather_code"))
        d = r.get("daily", {})
        days = []
        for i, date in enumerate(d.get("time", [])):
            code = d["weather_code"][i]
            th, en = describe(code)
            days.append({
                "date": date,
                "weather_code": code,
                "weather_th": th,
                "weather_en": en,
                "temp_max": d["temperature_2m_max"][i],
                "temp_min": d["temperature_2m_min"][i],
                "rain_prob": d["precipitation_probability_max"][i],
                "rain_mm": d["precipitation_sum"][i],
                "uv_max": d["uv_index_max"][i],
                "sunrise": d["sunrise"][i],
                "sunset": d["sunset"][i],
            })
        out.append({
            **p,
            "current": {
                "time": cur.get("time"),
                "temp": cur.get("temperature_2m"),
                "feels_like": cur.get("apparent_temperature"),
                "humidity": cur.get("relative_humidity_2m"),
                "rain_mm": cur.get("precipitation"),
                "wind_kmh": cur.get("wind_speed_10m"),
                "wind_dir": cur.get("wind_direction_10m"),
                "visibility_m": cur.get("visibility"),
                "is_day": cur.get("is_day"),
                "weather_code": cur.get("weather_code"),
                "weather_th": cur_th,
                "weather_en": cur_en,
            },
            "daily": days,
        })

    meta = {
        "updated_at": fetched_at.isoformat(timespec="seconds"),
        "timezone": TZ_NAME,
        "source": "Open-Meteo.com",
        "attribution": "Weather data by Open-Meteo.com (CC BY 4.0)",
        "attribution_url": "https://open-meteo.com/",
        "units": {"temp": "°C", "humidity": "%", "rain_mm": "mm", "wind_kmh": "km/h", "wind_dir": "°",
                  "visibility_m": "m", "rain_prob": "%"},
        "count": len(out),
    }
    full = {**meta, "provinces": out}

    features = []
    for p in out:
        today = p["daily"][0] if p["daily"] else {}
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]},
            "properties": {
                "id": p["id"],
                "name_th": p["name_th"],
                "name_en": p["name_en"],
                "region": p["region"],
                "obs_time": p["current"]["time"],
                "temp": p["current"]["temp"],
                "feels_like": p["current"]["feels_like"],
                "humidity": p["current"]["humidity"],
                "rain_mm": p["current"]["rain_mm"],
                "wind_kmh": p["current"]["wind_kmh"],
                "weather_code": p["current"]["weather_code"],
                "weather_th": p["current"]["weather_th"],
                "today_max": today.get("temp_max"),
                "today_min": today.get("temp_min"),
                "today_rain_prob": today.get("rain_prob"),
                "today_rain_mm": today.get("rain_mm"),
                "today_uv_max": today.get("uv_max"),
                "updated_at": meta["updated_at"],
            },
        })
    geo = {"type": "FeatureCollection", "metadata": meta, "features": features}
    return full, geo


def main():
    provinces = json.loads(PROVINCES_FILE.read_text(encoding="utf-8"))
    results = fetch(provinces)
    full, geo = build(provinces, results, datetime.now(BKK))
    OUT_JSON.write_text(json.dumps(full, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT_GEOJSON.write_text(json.dumps(geo, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"บันทึก {full['count']} จังหวัด เวลา {full['updated_at']}")


if __name__ == "__main__":
    main()
