---
name: weather
description: >-
  Weather and air quality information lookup using KMA (기상청), AirKorea, and AccuWeather.
  Use when users ask for current weather, weather forecasts, hourly forecasts, weather conditions,
  sunrise/sunset times, UV index, air quality (미세먼지/초미세먼지), or past/historical weather observations.
license: MIT
metadata:
  author: iceflower
  version: "1.0"
  last-reviewed: "2026-03"
compatibility: Requires internet access for KMA/AccuWeather APIs
---

# Weather Information Rules

## 1. Overview

This skill provides weather information from multiple data sources:

- **KMA (기상청)**: Current weather, hourly/daily forecasts, past observations (primary source)
- **AirKorea (에어코리아)**: Fine dust (미세먼지/초미세먼지) data
- **AccuWeather**: Air quality index (AQI), sunrise/sunset, UV index (supplementary)

## 2. Weather Script (Primary)

A Python script at `scripts/weather.py` is the primary tool for weather queries. **Always prefer using this script.**

### Prerequisites

- Python 3.x
- `requests` and `beautifulsoup4` packages
- API keys in `scripts/.env` (KMA_API_KEY, AIRKOREA_API_KEY)

### Usage

```bash
# Current weather (KMA 초단기실황)
python3 scripts/weather.py now [--city CITY]

# Daily forecast (KMA 단기예보 + 중기예보, up to 10 days)
python3 scripts/weather.py daily [--city CITY]

# Hourly forecast (KMA 단기예보, up to 3 days)
python3 scripts/weather.py hourly [--city CITY] [--day DAY]

# Past observation (KMA ASOS, any past date)
python3 scripts/weather.py past [--city CITY] [--date YYYYMMDD]

# Air quality (AccuWeather AQI)
python3 scripts/weather.py air [--city CITY]

# Hourly air quality (AccuWeather 24h)
python3 scripts/weather.py air-hourly [--city CITY]
```

### Supported Cities

About 100 locations are registered including sub-districts. Major cities:

`seoul`, `busan`, `daegu`, `incheon`, `gwangju`, `daejeon`, `ulsan`, `sejong`, `gangneung`, `chuncheon`, `jeonju`, `cheongju`, `jeju`, `seogwipo`, `gumi`, `suwon`, `changwon`, `pohang`, `gimhae`, `yeosu`, `wonju`, `gyeongju`, `andong`, `gimcheon`, `sangju`, `yeongju`, `mungyeong`

Sub-districts use `{city}-{district}` format (e.g., `seoul-gangnam`, `busan-haeundae`, `suwon-yeongtong`). See `references/cities.json` for the full list.

### Examples

```bash
# Current weather for Seoul
python3 scripts/weather.py now

# Tomorrow's hourly forecast for Seoul
python3 scripts/weather.py hourly --day 2

# Daily forecast for Busan
python3 scripts/weather.py daily --city busan

# Past observation for Seoul on specific date
python3 scripts/weather.py past --date 20260315

# Air quality for Daegu
python3 scripts/weather.py air --city daegu
```

### Query Strategy

1. **First**: Try `scripts/weather.py` (most reliable)
2. **Fallback**: Use WebFetch with AccuWeather URLs (Section 8)

## 3. Data Sources by Command

| Command      | Data Source              | Coverage                        |
| ------------ | ------------------------ | ------------------------------- |
| `now`        | KMA 초단기실황           | Current conditions              |
| `hourly`     | KMA 단기예보 + AirKorea  | Today ~ 3 days, hourly          |
| `daily`      | KMA 단기+중기예보        | Today ~ 10 days, daily          |
| `past`       | KMA ASOS 관측            | Any past date, hourly           |
| `air`        | AccuWeather + AirKorea   | Current AQI + pollutants        |
| `air-hourly` | AccuWeather              | 24-hour AQI forecast            |

## 4. KMA Forecast Details

### Short-term Forecast (단기예보) - `hourly`, `daily`

- Published every 3 hours: 0200, 0500, 0800, 1100, 1400, 1700, 2000, 2300
- Covers up to 3 days with hourly resolution
- Data: temperature (TMP), sky condition (SKY), precipitation probability (POP), precipitation type (PTY), humidity (REH), wind speed (WSD), wind direction (VEC)

### Mid-term Forecast (중기예보) - `daily`

- Published at 0600, 1800
- Covers day 4 ~ day 10
- Temperature: getMidTa (최고/최저기온)
- Weather/precipitation: getMidLandFcst (날씨상태, 강수확률)

### Ultra-short-term Observation (초단기실황) - `now`

- Published every hour
- Data: temperature (T1H), humidity (REH), wind (WSD/VEC), precipitation (PTY/RN1)

### ASOS Observation (종관기상관측) - `past`

- Historical hourly data via kma_sfctm3 API
- Data: temperature, dew point, humidity, wind, pressure, precipitation

## 5. Sky Condition Codes

| Code | Korean    | English        |
| ---- | --------- | -------------- |
| 1    | 맑음      | Clear          |
| 3    | 구름많음  | Mostly Cloudy  |
| 4    | 흐림      | Overcast       |

## 6. Precipitation Type Codes

| Code | Korean       | English          |
| ---- | ------------ | ---------------- |
| 0    | 없음         | None             |
| 1    | 비           | Rain             |
| 2    | 비/눈        | Rain/Snow        |
| 3    | 눈           | Snow             |
| 4    | 소나기       | Shower           |
| 5    | 빗방울       | Drizzle          |
| 6    | 빗방울눈날림 | Drizzle/Flurry   |
| 7    | 눈날림       | Snow Flurry      |

## 7. Air Quality

### AirKorea (미세먼지)

Integrated into `hourly` output:

- Today: real-time PM2.5/PM10 from AirKorea stations
- Tomorrow/day after: daily forecast grade from AirKorea

### AccuWeather AQI (`air`, `air-hourly`)

| AQI Range | Korean Level       | Health Impact                    |
| --------- | ------------------ | -------------------------------- |
| 0-19      | 완벽함             | Suitable for all activities      |
| 20-49     | 보통               | Acceptable for most people       |
| 50-99     | 나쁨               | Sensitive groups may be affected |
| 100-149   | 건강에 해로움      | Limit outdoor activities         |
| 150-249   | 건강에 매우 해로움 | Avoid outdoor activities         |
| 250+      | 위험               | Avoid all outdoor exposure       |

## 8. AccuWeather Fallback (WebFetch)

If the script fails, use WebFetch with these URL patterns:

```text
# Air quality
https://www.accuweather.com/ko/kr/{city}/{location-key}/air-quality-index/{location-key}

# Sunrise/sunset
https://www.accuweather.com/ko/kr/{city}/{location-key}/weather-today/{location-key}
```

AccuWeather location keys are stored in `references/cities.json` under the `accuweatherKey` field.

## 9. Sunrise/Sunset

### AccuWeather

Available on the `weather-today` page via WebFetch.

### KASI (한국천문연구원)

For precise astronomical data:

| Service              | URL                                        |
| -------------------- | ------------------------------------------ |
| 일출일몰시각계산     | `https://astro.kasi.re.kr/life/pageView/9` |
| 월별 해/달 출몰시각  | `https://astro.kasi.re.kr/life/pageView/6` |

## 10. UV Index Scale

| Index | Korean Level       | English Level |
| ----- | ------------------ | ------------- |
| 0-2   | 좋음               | Good          |
| 3-5   | 보통               | Moderate      |
| 6-7   | 해로움 (민감 그룹) | High          |
| 8-10  | 건강에 해로움      | Very High     |
| 11+   | 매우 해로움        | Extreme       |

## 11. Best Practices

### Best Practices Query Strategy

1. For current weather: `scripts/weather.py now`
2. For hourly forecast: `scripts/weather.py hourly` with `--day` parameter
3. For multi-day forecast: `scripts/weather.py daily`
4. For past weather: `scripts/weather.py past` with `--date` parameter
5. For air quality: `scripts/weather.py air` or `air-hourly`
6. For sunrise/sunset: WebFetch with AccuWeather or KASI

### Information Prioritization

When user asks for weather without specifying details:

1. Temperature (high/low or current)
2. Weather condition
3. Precipitation probability
4. Wind information
5. Air quality (if relevant)
6. Sunrise/sunset (if relevant)

### Attribution

Cite the data source:

```markdown
출처: 기상청
출처: 에어코리아
출처: AccuWeather
```

## 12. Limitations

- KMA hourly forecasts cover up to 3 days only; beyond that, daily forecasts are provided
- KMA API may have intermittent timeouts; retry once if failed
- ASOS past observations require the KMA ASOS API subscription
- AccuWeather scraping may break if website structure changes
- Grid coordinates (nx, ny) represent 5km cells; nearby locations within the same city share coordinates
