import requests
import xml.etree.ElementTree as ET
import json

url = "https://data.tmd.go.th/api/WeatherForecast7DaysByRegion/v2/?uid=demo&ukey=demokey"
response = requests.get(url)
root = ET.fromstring(response.content)

weather_list = []
for region in root.findall('.//RegionForecast'):
    data = {
        "region_thai": region.find('RegionNameThai').text.strip(),
        "description_thai": region.find('DescriptionThai').text.strip(),
        "region_eng": region.find('RegionNameEnglish').text.strip()
    }
    weather_list.append(data)

# บันทึกเป็นไฟล์ JSON ง่ายๆ
with open("weather.json", "w", encoding="utf-8") as f:
    json.dump(weather_list, f, ensure_ascii=False, indent=4)
