# WeatherForecastDaily

ข้อมูลสภาพอากาศประเทศไทย อัปเดตอัตโนมัติด้วย GitHub Actions

## 1. สภาพอากาศ 77 จังหวัด (Open-Meteo)
| ไฟล์ | คำอธิบาย |
|---|---|
| `provinces.json` | รายชื่อ 77 จังหวัด (ไทย/อังกฤษ, ภาค, พิกัดตัวเมือง) — แก้/เพิ่มจุดได้ที่ไฟล์นี้ |
| `scripts/update_openmeteo.py` | ดึงข้อมูลทั้ง 77 จุดใน **คำขอเดียว** จาก Open-Meteo (ใช้ Python มาตรฐาน ไม่ต้องติดตั้งแพ็กเกจ) |
| `provinces_weather.json` | ผลลัพธ์เต็ม: สภาพอากาศปัจจุบัน + พยากรณ์รายวัน 7 วัน ของทุกจังหวัด |
| `provinces_weather.geojson` | จุดจังหวัด + ค่าปัจจุบัน/วันนี้ สำหรับ QGIS / ArcGIS / Leaflet |
| `index.html` | หน้าเว็บแผนที่ + ตาราง (ค้นหา, กรองภาค, เรียงลำดับ, คลิกดูพยากรณ์ 7 วัน) |
| `.github/workflows/openmeteo_update.yml` | รันทุกชั่วโมง (นาทีที่ 17) แล้ว commit ไฟล์ผลลัพธ์ |

ค่าที่เก็บ — ปัจจุบัน: อุณหภูมิ, ความชื้น, ปริมาณฝน, รหัสสภาพอากาศ (แปลเป็นไทยแล้ว), ความเร็วลม ·
รายวัน: สภาพอากาศ, อุณหภูมิสูง/ต่ำสุด, โอกาสฝนสูงสุด, ปริมาณฝนรวม (เวลา `Asia/Bangkok`)

### โควตา
Open-Meteo นับ 1 พิกัด = 1 call (จำกัดตัวแปรไว้ 10 ตัวเพื่อไม่ให้ถูกนับซ้ำ) → 77 × 24 ≈ **1,850 calls/วัน, ~55,000/เดือน**
ต่ำกว่าโควตาฟรี (10,000/วัน, 300,000/เดือน) — แต่แบบฟรีใช้ได้เฉพาะงาน **ไม่เชิงพาณิชย์** ถ้าใช้เชิงพาณิชย์ต้องซื้อ API plan
แล้วเปลี่ยน `API_URL` เป็น `customer-api.open-meteo.com` พร้อมใส่ `apikey` (เก็บเป็น GitHub Secret)

### เครดิต
ข้อมูลอยู่ภายใต้ CC BY 4.0 — ทุกหน้าที่นำไปแสดงต้องใส่ "Weather data by Open-Meteo.com" พร้อมลิงก์ https://open-meteo.com/

### ใช้งานในเว็บอื่น
```js
const url = "https://raw.githubusercontent.com/nawakonnakhonchai-wq/WeatherForecastDaily/main/provinces_weather.json";
const data = await (await fetch(url)).json();
data.provinces.forEach(p => console.log(p.name_th, p.current.temp, p.current.weather_th));
```

## 2. พยากรณ์รายภาค (กรมอุตุนิยมวิทยา)
`weather_update.yml` ดึงพยากรณ์ 7 วันรายภาคจาก TMD ทุก 3 ชั่วโมง → `weather.geojson`

ทั้งสอง workflow อยู่ใน concurrency group เดียวกัน (`data-commit`) จึงไม่ push ชนกัน
