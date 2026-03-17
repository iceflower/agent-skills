#!/usr/bin/env python3
"""AccuWeather weather information scraping script.

Usage:
    python3 weather.py daily [--city CITY]
    python3 weather.py hourly [--city CITY] [--day DAY]
    python3 weather.py air [--city CITY]

Examples:
    python3 weather.py daily
    python3 weather.py daily --city busan
    python3 weather.py hourly --day 2
    python3 weather.py air --city daegu
"""

import argparse
import json
import os
import re
import sys
import warnings

warnings.filterwarnings("ignore")

import requests
from bs4 import BeautifulSoup

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_CITIES_FILE = os.path.join(_SCRIPT_DIR, "..", "references", "cities.json")


def _load_cities() -> dict:
    """Load city data from references/cities.json."""
    try:
        with open(_CITIES_FILE, encoding="utf-8") as f:
            raw = json.load(f)
        return {
            k: (v["key"], v["name"], v.get("region", ""), v.get("station", ""))
            for k, v in raw.items()
        }
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return {
            "seoul": ("226081", "서울특별시", "서울", "종로구"),
        }


LOCATION_KEYS = _load_cities()

_ENV_FILE = os.path.join(_SCRIPT_DIR, ".env")


def _load_env() -> None:
    """Load .env file from scripts/ directory into os.environ."""
    if not os.path.isfile(_ENV_FILE):
        return
    with open(_ENV_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


_load_env()
_AIRKOREA_API_KEY = os.environ.get("AIRKOREA_API_KEY", "")
_AIRKOREA_BASE = "https://apis.data.go.kr/B552584/ArpltnInforInqireSvc"

_PM25_RANGE = {"좋음": "0~15", "보통": "16~35", "나쁨": "36~75", "매우나쁨": "76~"}
_PM10_RANGE = {"좋음": "0~30", "보통": "31~80", "나쁨": "81~150", "매우나쁨": "151~"}


def _fetch_airkorea_realtime(station: str) -> dict:
    """에어코리아 측정소별 시간별 실측 데이터를 {hour: {...}} dict로 반환한다."""
    if not _AIRKOREA_API_KEY or not station:
        return {}

    import urllib.parse

    encoded_station = urllib.parse.quote(station)
    url = (
        f"{_AIRKOREA_BASE}/getMsrstnAcctoRltmMesureDnsty"
        f"?serviceKey={_AIRKOREA_API_KEY}"
        f"&returnType=json&numOfRows=24&pageNo=1"
        f"&stationName={encoded_station}&dataTerm=DAILY&ver=1.5"
    )
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return {}
        items = r.json()["response"]["body"]["items"]
        result = {}
        for item in items:
            dt = item.get("dataTime", "")
            # "2026-03-17 22:00" → hour=22
            hour_match = re.search(r"(\d{2}):00$", dt)
            if not hour_match:
                continue
            hour = int(hour_match.group(1))
            pm25 = item.get("pm25Value", "-")
            pm10 = item.get("pm10Value", "-")
            if pm25 == "-" or pm10 == "-":
                continue
            result[hour] = {"pm25": pm25, "pm10": pm10}
        return result
    except Exception:
        return {}


def _fetch_airkorea_forecast(target_date: str, region: str) -> dict:
    """에어코리아 일별 예보 등급을 조회한다.

    Returns: {"pm25": "보통", "pm10": "나쁨"} 또는 빈 dict
    """
    if not _AIRKOREA_API_KEY:
        return {}

    from datetime import datetime

    # searchDate는 통보 발표일 기준이므로 오늘 날짜로 검색
    today = datetime.now().strftime("%Y-%m-%d")
    result = {}
    for code in ("PM25", "PM10"):
        url = (
            f"{_AIRKOREA_BASE}/getMinuDustFrcstDspth"
            f"?serviceKey={_AIRKOREA_API_KEY}"
            f"&returnType=json&numOfRows=100&pageNo=1"
            f"&searchDate={today}&InformCode={code}"
        )
        try:
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                continue
            items = r.json()["response"]["body"]["items"]
            # 가장 최신 발표의 해당 날짜 예보를 사용
            for item in items:
                if item.get("informData") != target_date:
                    continue
                grade_str = item.get("informGrade", "")
                grades = dict(
                    g.split(" : ")
                    for g in grade_str.split(",")
                    if " : " in g
                )
                grade = grades.get(region, "")
                if grade:
                    key = "pm25" if code == "PM25" else "pm10"
                    result[key] = grade
                    break
        except Exception:
            continue
    return result

TIMEOUT = 15


def _create_session() -> requests.Session:
    """Create a session with browser-like headers to avoid bot detection."""
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Referer": "https://www.accuweather.com/",
        }
    )
    return s


def _fetch(session: requests.Session, url: str) -> BeautifulSoup:
    import time

    for attempt in range(3):
        r = session.get(url, timeout=TIMEOUT)
        if r.status_code == 200:
            return BeautifulSoup(r.text, "html.parser")
        if r.status_code == 403 and attempt < 2:
            time.sleep(2)
            continue
        r.raise_for_status()
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def _base_url(city: str) -> str:
    key = LOCATION_KEYS[city][0]
    return f"https://www.accuweather.com/ko/kr/{city}/{key}"


def fetch_daily(city: str) -> None:
    session = _create_session()
    key = LOCATION_KEYS[city][0]
    city_name = LOCATION_KEYS[city][1]
    url = f"{_base_url(city)}/daily-weather-forecast/{key}"
    soup = _fetch(session, url)

    wrappers = soup.select(".daily-wrapper")
    if not wrappers:
        print("일별 예보 데이터를 찾을 수 없습니다.")
        return

    print(f"## {city_name} 일별 예보\n")
    print("| 날짜 | 최고 | 최저 | 강수확률 | 날씨 |")
    print("| --- | --- | --- | --- | --- |")

    for wrapper in wrappers[:10]:
        card = wrapper.select_one(".daily-forecast-card")
        if not card:
            continue

        info = card.select_one(".info")
        precip = card.select_one(".precip")
        if not info:
            continue

        text = info.get_text(separator="|", strip=True)
        parts = text.split("|")
        if len(parts) < 4:
            continue

        day_name = parts[0]
        date_str = parts[1].strip()
        high = parts[2].strip().replace("°", "")
        low = parts[3].strip().lstrip("/").replace("°", "")
        precip_text = precip.get_text(strip=True) if precip else "-"

        full_text = wrapper.get_text(separator="|", strip=True)
        weather_desc = _extract_weather_desc(full_text, precip_text)

        print(
            f"| {day_name} {date_str} | {high}°C | {low}°C | {precip_text} | {weather_desc} |"
        )

    print("\n### 상세 정보\n")
    for wrapper in wrappers[:3]:
        card = wrapper.select_one(".daily-forecast-card")
        if not card:
            continue

        info = card.select_one(".info")
        if not info:
            continue

        text = info.get_text(separator="|", strip=True)
        parts = text.split("|")
        if len(parts) < 2:
            continue

        day_name = parts[0]
        date_str = parts[1].strip()

        full_text = wrapper.get_text(separator="|", strip=True)
        details = _parse_daily_details(full_text)

        print(f"**{day_name} {date_str}**\n")
        for k, v in details.items():
            print(f"- {k}: {v}")
        print()

    print("출처: AccuWeather")


def _extract_weather_desc(full_text: str, precip_text: str) -> str:
    parts = full_text.split("|")
    for i, part in enumerate(parts):
        if precip_text in part and i + 1 < len(parts):
            desc = parts[i + 1].strip()
            if desc and not desc.startswith("RealFeel"):
                return desc
    return "-"


def _parse_daily_details(full_text: str) -> dict:
    details = {}
    parts = [p.strip() for p in full_text.split("|")]

    key_map = {
        "RealFeel®": "체감온도",
        "RealFeel Shade™": "그늘 체감온도",
        "최대 자외선 지수": "자외선지수",
        "구름량": "구름량",
        "바람": "바람",
        "돌풍": "돌풍",
    }

    for i, part in enumerate(parts):
        for keyword, label in key_map.items():
            if part == keyword and i + 1 < len(parts):
                details[label] = parts[i + 1]

    return details


def _parse_time_to_hour(time_text: str) -> int:
    """'오전 7시' / '오후 12시' 등을 0-23 정수로 변환한다."""
    m = re.search(r"(오전|오후)\s*(\d+)시", time_text)
    if not m:
        return -1
    period, hour = m.group(1), int(m.group(2))
    if period == "오전":
        return 0 if hour == 12 else hour
    else:
        return 12 if hour == 12 else hour + 12


def fetch_hourly(city: str, day: int) -> None:
    session = _create_session()
    key = LOCATION_KEYS[city][0]
    city_name = LOCATION_KEYS[city][1]

    if day < 1 or day > 3:
        print("시간별 예보는 1~3일(오늘~모레)까지만 제공됩니다.")
        return

    url = f"{_base_url(city)}/hourly-weather-forecast/{key}?day={day}"
    soup = _fetch(session, url)

    items = soup.select(".accordion-item.hour")
    if not items:
        print("시간별 예보 데이터를 찾을 수 없습니다.")
        return

    # 오늘(day=1): 에어코리아 실측 데이터로 시간별 미세먼지 표시
    # 내일/모레(day>=2): 시간별 수치 없음, 테이블 아래에 일별 예보 등급 표시
    show_hourly_air = day == 1
    air_realtime = {}
    if show_hourly_air:
        station = LOCATION_KEYS[city][3]
        air_realtime = _fetch_airkorea_realtime(station)

    day_label = {1: "오늘", 2: "내일", 3: "모레"}
    print(f"## {city_name} 시간별 예보 ({day_label.get(day, f'{day}일차')})\n")
    if show_hourly_air:
        print("| 시간 | 기온 | 체감 | 날씨 | 강수 | 습도 | 바람 | PM2.5 | PM10 |")
        print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    else:
        print("| 시간 | 기온 | 체감 | 날씨 | 강수 | 습도 | 바람 |")
        print("| --- | --- | --- | --- | --- | --- | --- |")

    for item in items:
        time_el = item.select_one(".date")
        temp_el = item.select_one(".temp")
        realfeel_el = item.select_one(".real-feel__text")
        precip_el = item.select_one(".precip")

        time_text = time_el.get_text(strip=True) if time_el else "-"
        temp_raw = temp_el.get_text(strip=True) if temp_el else "-"
        temp_text = temp_raw.replace("°", "°C") if "°" in temp_raw else temp_raw
        precip_text = precip_el.get_text(strip=True) if precip_el else "-"

        realfeel_text = "-"
        if realfeel_el:
            rf_raw = realfeel_el.get_text(strip=True)
            rf_match = re.search(r"(-?\d+)°", rf_raw)
            if rf_match:
                realfeel_text = f"{rf_match.group(1)}°C"

        humidity = "-"
        wind = "-"
        panels = item.select(".panel")
        for p in panels:
            panel_parts = [
                t.strip()
                for t in p.get_text(separator="|", strip=True).split("|")
            ]
            for i, part in enumerate(panel_parts):
                if part == "습도" and i + 1 < len(panel_parts):
                    humidity = panel_parts[i + 1]
                elif part == "바람" and i + 1 < len(panel_parts):
                    wind = panel_parts[i + 1]

        weather = "-"
        header = item.select_one(".accordion-item-header-container")
        if header:
            h_parts = [
                p.strip()
                for p in header.get_text(separator="|", strip=True).split("|")
            ]
            for i, part in enumerate(h_parts):
                if part == "Chevron down" and i + 1 < len(h_parts):
                    weather = h_parts[i + 1]
                    break

        precip_text = precip_text.replace("rain drop", "").strip()
        precip_match = re.search(r"(\d+%)", precip_text)
        if precip_match:
            precip_text = precip_match.group(1)

        row = (
            f"| {time_text} | {temp_text} | {realfeel_text} | {weather} | "
            f"{precip_text} | {humidity} | {wind} |"
        )

        if show_hourly_air:
            hour = _parse_time_to_hour(time_text)
            air = air_realtime.get(hour, {})
            pm25 = air.get("pm25", "-")
            pm10 = air.get("pm10", "-")
            row += f" {pm25} | {pm10} |"

        print(row)

    # 내일/모레: 에어코리아 일별 예보 등급 표시
    if not show_hourly_air:
        from datetime import datetime, timedelta

        region = LOCATION_KEYS[city][2]
        target_date = (datetime.now() + timedelta(days=day - 1)).strftime("%Y-%m-%d")
        forecast = _fetch_airkorea_forecast(target_date, region)
        if forecast:
            pm25_grade = forecast.get("pm25", "-")
            pm10_grade = forecast.get("pm10", "-")
            pm25_range = _PM25_RANGE.get(pm25_grade, "")
            pm10_range = _PM10_RANGE.get(pm10_grade, "")
            pm25_display = f"{pm25_grade} ({pm25_range}µg/m³)" if pm25_range else pm25_grade
            pm10_display = f"{pm10_grade} ({pm10_range}µg/m³)" if pm10_range else pm10_grade
            print(f"\n> 미세먼지 일별 예보: PM2.5 **{pm25_display}** / PM10 **{pm10_display}** (출처: 에어코리아)")

    print("\n출처: AccuWeather")


def fetch_air_quality(city: str) -> None:
    session = _create_session()
    key = LOCATION_KEYS[city][0]
    city_name = LOCATION_KEYS[city][1]
    url = f"{_base_url(city)}/air-quality-index/{key}"
    soup = _fetch(session, url)

    aqi_content = soup.select_one(".air-quality-content")
    if not aqi_content:
        print("대기질 데이터를 찾을 수 없습니다.")
        return

    category_el = aqi_content.select_one(".category-text")
    category = category_el.get_text(strip=True) if category_el else "-"

    aqi_text = aqi_content.get_text(separator="|", strip=True)
    aqi_match = re.search(r"(\d+)\|?AQI", aqi_text)
    main_aqi = aqi_match.group(1) if aqi_match else "-"

    print(f"## {city_name} 대기질\n")
    print(f"- **AQI**: {main_aqi} ({category})")

    pollutants = soup.select(".air-quality-pollutant")
    if pollutants:
        print()
        print("| 오염물질 | 등급 | AQI | 농도 |")
        print("| --- | --- | --- | --- |")

        pollutant_names = {
            "PM2.5": "초미세먼지 (PM2.5)",
            "PM10": "미세먼지 (PM10)",
            "NO2": "이산화질소 (NO2)",
            "SO2": "이산화황 (SO2)",
            "O3": "오존 (O3)",
            "CO": "일산화탄소 (CO)",
        }

        for p in pollutants:
            display_type = p.select_one(".display-type")
            p_category = p.select_one(".category")
            p_index = p.select_one(".pollutant-index")
            p_conc = p.select_one(".pollutant-concentration")

            name_raw = display_type.get_text(strip=True) if display_type else "-"
            name = pollutant_names.get(name_raw, name_raw)
            cat = p_category.get_text(strip=True) if p_category else "-"
            idx = p_index.get_text(strip=True) if p_index else "-"
            conc = p_conc.get_text(strip=True) if p_conc else "-"

            print(f"| {name} | {cat} | {idx} | {conc} |")

    print("\n출처: AccuWeather")


def fetch_air_hourly(city: str) -> None:
    import json

    session = _create_session()
    key = LOCATION_KEYS[city][0]
    city_name = LOCATION_KEYS[city][1]
    url = f"{_base_url(city)}/air-quality-index/{key}"
    soup = _fetch(session, url)

    data_el = soup.select_one("[data-points]")
    if not data_el:
        print("시간별 대기질 데이터를 찾을 수 없습니다.")
        return

    points = json.loads(data_el.get("data-points"))
    if not points:
        print("시간별 대기질 데이터가 비어 있습니다.")
        return

    # 현재 시각 기준으로 시간 라벨 생성 (24개 포인트 = 24시간)
    from datetime import datetime, timedelta

    now = datetime.now()
    start_hour = now.hour
    hours = []
    for i in range(len(points)):
        h = (start_hour + i) % 24
        if h == 0:
            hours.append("오전 12시")
        elif h < 12:
            hours.append(f"오전 {h}시")
        elif h == 12:
            hours.append("오후 12시")
        else:
            hours.append(f"오후 {h - 12}시")

    print(f"## {city_name} 시간별 대기질 (24시간)\n")
    print("| 시간 | AQI | 등급 | PM2.5 | PM10 | O3 | NO2 |")
    print("| --- | --- | --- | --- | --- | --- | --- |")

    for i, pt in enumerate(points):
        xval = json.loads(pt["XValues"][0])
        aqi = xval["overallIndex"]
        category = xval["category"]
        pollutants = xval.get("pollutants", {})
        pm25 = pollutants.get("PM2_5", "-")
        pm10 = pollutants.get("PM10", "-")
        o3 = pollutants.get("O3", "-")
        no2 = pollutants.get("NO2", "-")
        time_label = hours[i] if i < len(hours) else f"#{i}"

        print(
            f"| {time_label} | {aqi:.0f} | {category} | {pm25} | {pm10} | {o3} | {no2} |"
        )

    print("\n출처: AccuWeather")


def main():
    parser = argparse.ArgumentParser(
        description="AccuWeather weather information lookup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "type",
        choices=["daily", "hourly", "air", "air-hourly"],
        help="Forecast type: daily, hourly, air(quality), air-hourly(hourly air quality)",
    )
    parser.add_argument(
        "--city",
        default="seoul",
        help=f"City name (default: seoul). Available: {', '.join(sorted(LOCATION_KEYS.keys()))}",
    )
    parser.add_argument(
        "--day",
        type=int,
        default=1,
        help="Day for hourly forecast: 1=today, 2=tomorrow, 3=day after (default: 1)",
    )

    args = parser.parse_args()

    if args.city not in LOCATION_KEYS:
        print(
            f"알 수 없는 도시: {args.city}\n"
            f"등록된 도시: {', '.join(sorted(LOCATION_KEYS.keys()))}\n"
            f"새 도시를 추가하려면 references/cities.json 파일을 편집하세요.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        if args.type == "daily":
            fetch_daily(args.city)
        elif args.type == "hourly":
            fetch_hourly(args.city, args.day)
        elif args.type == "air":
            fetch_air_quality(args.city)
        elif args.type == "air-hourly":
            fetch_air_hourly(args.city)
    except requests.RequestException as e:
        print(f"네트워크 오류: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
