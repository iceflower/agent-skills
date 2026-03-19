#!/usr/bin/env python3
"""Weather information script using KMA (기상청), AirKorea, and AccuWeather APIs.

Usage:
    python3 weather.py now [--city CITY]
    python3 weather.py daily [--city CITY]
    python3 weather.py hourly [--city CITY] [--day DAY]
    python3 weather.py past [--city CITY] [--date YYYYMMDD]
    python3 weather.py air [--city CITY]
    python3 weather.py air-hourly [--city CITY]

Examples:
    python3 weather.py now
    python3 weather.py daily --city busan
    python3 weather.py hourly --day 2
    python3 weather.py past --date 20260315
    python3 weather.py air --city daegu
"""

import argparse
import json
import os
import re
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

warnings.filterwarnings("ignore")

import requests
from bs4 import BeautifulSoup

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_CITIES_FILE = os.path.join(_SCRIPT_DIR, "..", "references", "cities.json")
_KST = ZoneInfo("Asia/Seoul")


def _load_cities() -> dict:
    """Load city data from references/cities.json as dict of dicts."""
    try:
        with open(_CITIES_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "seoul": {
                "accuweatherKey": "226081", "name": "서울특별시", "region": "서울",
                "station": "종로구", "asos": 108, "nx": 60, "ny": 127,
                "midTa": "11B10101", "midLand": "11B00000",
            },
        }


CITIES = _load_cities()

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
_KMA_API_KEY = os.environ.get("KMA_API_KEY", "")
_KMA_ASOS_BASE = "https://apihub.kma.go.kr/api/typ01/url/kma_sfctm3.php"
_KMA_FCST_BASE = "https://apihub.kma.go.kr/api/typ02/openApi"

_PM25_RANGE = {"좋음": "0~15", "보통": "16~35", "나쁨": "36~75", "매우나쁨": "76~"}
_PM10_RANGE = {"좋음": "0~30", "보통": "31~80", "나쁨": "81~150", "매우나쁨": "151~"}

# --- KMA common helpers ---

_SKY_MAP = {1: "맑음", 3: "구름많음", 4: "흐림"}
_PTY_MAP = {0: "", 1: "비", 2: "비/눈", 3: "눈", 4: "소나기", 5: "빗방울", 6: "빗방울눈날림", 7: "눈날림"}


def _now_kst() -> datetime:
    """Return current datetime in KST."""
    return datetime.now(_KST)


def _vec_to_dir(vec: float) -> str:
    """Convert wind direction in degrees to Korean 16-direction."""
    dirs = ["북", "북북동", "북동", "동북동", "동", "동남동", "남동", "남남동",
            "남", "남남서", "남서", "서남서", "서", "서북서", "북서", "북북서"]
    idx = round(vec / 22.5) % 16
    return dirs[idx]


def _kma_fcst_get(service: str, operation: str, params: dict) -> dict | None:
    """Call a KMA forecast API and return parsed JSON response."""
    if not _KMA_API_KEY:
        print("KMA_API_KEY가 설정되지 않았습니다.", file=sys.stderr)
        return None
    url = f"{_KMA_FCST_BASE}/{service}/{operation}"
    params = {**params, "dataType": "JSON", "authKey": _KMA_API_KEY}
    try:
        r = requests.get(url, params=params, timeout=30)
        if r.status_code != 200:
            print(f"API 오류: HTTP {r.status_code}", file=sys.stderr)
            return None
        data = r.json()
        if data.get("response", {}).get("header", {}).get("resultCode") != "00":
            msg = data.get("response", {}).get("header", {}).get("resultMsg", "")
            print(f"API 오류: {msg}", file=sys.stderr)
            return None
        return data
    except Exception as e:
        print(f"API 호출 실패: {e}", file=sys.stderr)
        return None


# --- now (초단기실황) ---

def fetch_now(city: str) -> None:
    """Fetch current weather using KMA ultra-short-term observation."""
    c = CITIES[city]
    now = _now_kst()
    # 실황은 매시 정각 발표, 약 10분 후 제공 → 현재시각-40분의 정시 사용
    base = now - timedelta(minutes=40)
    base_date = base.strftime("%Y%m%d")
    base_time = base.strftime("%H00")

    data = _kma_fcst_get("VilageFcstInfoService_2.0", "getUltraSrtNcst", {
        "pageNo": 1, "numOfRows": 10,
        "base_date": base_date, "base_time": base_time,
        "nx": c["nx"], "ny": c["ny"],
    })
    if not data:
        return

    items = data["response"]["body"]["items"]["item"]
    vals = {item["category"]: item["obsrValue"] for item in items}

    t1h = vals.get("T1H", "-")
    reh = vals.get("REH", "-")
    wsd = vals.get("WSD", "-")
    vec = vals.get("VEC", "0")
    pty = int(vals.get("PTY", "0"))
    rn1 = vals.get("RN1", "0")

    wind_dir = _vec_to_dir(float(vec)) if vec != "-" else "-"
    pty_str = _PTY_MAP.get(pty, "")
    precip = f"{rn1}mm" if pty and rn1 != "0" else "없음"

    print(f"## {c['name']} 현재 날씨\n")
    print(f"- **기온**: {t1h}°C")
    print(f"- **습도**: {reh}%")
    print(f"- **바람**: {wind_dir} {wsd}m/s")
    if pty_str:
        print(f"- **강수**: {pty_str} ({precip})")
    else:
        print(f"- **강수**: 없음")
    print(f"\n출처: 기상청")


# --- hourly (단기예보) ---

def _get_latest_base_time(now: datetime) -> tuple[str, str]:
    """Get the latest available base_time for short-term forecast."""
    base_times = [2, 5, 8, 11, 14, 17, 20, 23]
    hour = now.hour
    # 발표 후 약 10분 소요, 여유 두고 -1시간
    check = hour - 1
    chosen = 23
    for bt in reversed(base_times):
        if check >= bt:
            chosen = bt
            break
    base_date = now.strftime("%Y%m%d")
    if chosen == 23 and hour < 23:
        base_date = (now - timedelta(days=1)).strftime("%Y%m%d")
    return base_date, f"{chosen:02d}00"


def fetch_hourly(city: str, day: int) -> None:
    """Fetch hourly forecast using KMA short-term forecast API."""
    c = CITIES[city]
    now = _now_kst()
    base_date, base_time = _get_latest_base_time(now)

    data = _kma_fcst_get("VilageFcstInfoService_2.0", "getVilageFcst", {
        "pageNo": 1, "numOfRows": 1000,
        "base_date": base_date, "base_time": base_time,
        "nx": c["nx"], "ny": c["ny"],
    })
    if not data:
        return

    items = data["response"]["body"]["items"]["item"]

    # Group by fcstDate+fcstTime
    hourly = {}
    for item in items:
        key = (item["fcstDate"], item["fcstTime"])
        if key not in hourly:
            hourly[key] = {}
        hourly[key][item["category"]] = item["fcstValue"]

    # Filter by requested day
    target_date = (now + timedelta(days=day - 1)).strftime("%Y%m%d")
    filtered = {k: v for k, v in sorted(hourly.items()) if k[0] == target_date}

    if not filtered:
        print(f"{target_date} 시간별 예보 데이터가 없습니다.")
        return

    day_label = {1: "오늘", 2: "내일", 3: "모레"}.get(day, f"{day}일차")
    formatted = f"{target_date[:4]}-{target_date[4:6]}-{target_date[6:8]}"
    print(f"## {c['name']} 시간별 예보 ({day_label}, {formatted})\n")
    print("| 시간 | 기온 | 하늘 | 강수확률 | 강수형태 | 습도 | 바람 |")
    print("| --- | --- | --- | --- | --- | --- | --- |")

    for (fdate, ftime), vals in filtered.items():
        hour = int(ftime[:2])
        tmp = vals.get("TMP", "-")
        sky = _SKY_MAP.get(int(vals.get("SKY", "1")), "-")
        pop = vals.get("POP", "-")
        pty = int(vals.get("PTY", "0"))
        pty_str = _PTY_MAP.get(pty, "-") or "-"
        reh = vals.get("REH", "-")
        wsd = vals.get("WSD", "-")
        vec = vals.get("VEC", "0")
        wind_dir = _vec_to_dir(float(vec)) if vec != "-" else "-"
        wind = f"{wind_dir} {wsd}m/s"

        print(f"| {hour:02d}시 | {tmp}°C | {sky} | {pop}% | {pty_str} | {reh}% | {wind} |")

    # 에어코리아 미세먼지 정보
    if day == 1:
        air_realtime = _fetch_airkorea_realtime(c.get("station", ""))
        if air_realtime:
            latest_hour = max(air_realtime.keys())
            air = air_realtime[latest_hour]
            print(f"\n> 미세먼지 (최근 {latest_hour}시): PM2.5 **{air['pm25']}**µg/m³ / PM10 **{air['pm10']}**µg/m³ (출처: 에어코리아)")
    elif day <= 3:
        region = c.get("region", "")
        target = (now + timedelta(days=day - 1)).strftime("%Y-%m-%d")
        forecast = _fetch_airkorea_forecast(target, region)
        if forecast:
            pm25_g = forecast.get("pm25", "-")
            pm10_g = forecast.get("pm10", "-")
            pm25_r = _PM25_RANGE.get(pm25_g, "")
            pm10_r = _PM10_RANGE.get(pm10_g, "")
            pm25_d = f"{pm25_g} ({pm25_r}µg/m³)" if pm25_r else pm25_g
            pm10_d = f"{pm10_g} ({pm10_r}µg/m³)" if pm10_r else pm10_g
            print(f"\n> 미세먼지 예보: PM2.5 **{pm25_d}** / PM10 **{pm10_d}** (출처: 에어코리아)")

    print("\n출처: 기상청")


# --- daily (단기예보 + 중기예보) ---

def _parse_short_term_daily(items: list) -> dict:
    """Parse short-term forecast items into daily aggregated data."""
    daily = {}
    for item in items:
        d = item["fcstDate"]
        cat = item["category"]
        val = item["fcstValue"]
        if d not in daily:
            daily[d] = {"tmn": None, "tmx": None, "pops": [], "skys": [], "ptys": []}
        if cat == "TMN":
            daily[d]["tmn"] = val
        elif cat == "TMX":
            daily[d]["tmx"] = val
        elif cat == "POP":
            daily[d]["pops"].append(int(val))
        elif cat == "SKY":
            daily[d]["skys"].append(int(val))
        elif cat == "PTY":
            daily[d]["ptys"].append(int(val))
    return daily


def _fetch_mid_term(c: dict, tmfc: str) -> tuple[dict, dict]:
    """Fetch mid-term temperature and land forecasts in parallel."""
    ta_params = {"pageNo": 1, "numOfRows": 10, "regId": c.get("midTa", ""), "tmFc": tmfc}
    land_params = {"pageNo": 1, "numOfRows": 10, "regId": c.get("midLand", ""), "tmFc": tmfc}

    with ThreadPoolExecutor(max_workers=2) as executor:
        ta_future = executor.submit(_kma_fcst_get, "MidFcstInfoService", "getMidTa", ta_params)
        land_future = executor.submit(_kma_fcst_get, "MidFcstInfoService", "getMidLandFcst", land_params)
        ta_data = ta_future.result()
        land_data = land_future.result()

    mid_ta = {}
    if ta_data:
        items = ta_data["response"]["body"]["items"]["item"]
        if items:
            item = items[0]
            for d in range(4, 11):
                mid_ta[d] = {"min": item.get(f"taMin{d}"), "max": item.get(f"taMax{d}")}

    mid_land = {}
    if land_data:
        items = land_data["response"]["body"]["items"]["item"]
        if items:
            item = items[0]
            for d in range(4, 8):
                mid_land[d] = {
                    "wfAm": item.get(f"wf{d}Am", "-"), "wfPm": item.get(f"wf{d}Pm", "-"),
                    "rnAm": item.get(f"rnSt{d}Am", "-"), "rnPm": item.get(f"rnSt{d}Pm", "-"),
                }
            for d in range(8, 11):
                mid_land[d] = {"wf": item.get(f"wf{d}", "-"), "rn": item.get(f"rnSt{d}", "-")}

    return mid_ta, mid_land


def _format_daily_output(c: dict, now: datetime, short_daily: dict,
                         mid_ta: dict, mid_land: dict) -> None:
    """Format and print daily forecast output."""
    print(f"## {c['name']} 일별 예보\n")
    print("| 날짜 | 최저 | 최고 | 강수확률 | 날씨 |")
    print("| --- | --- | --- | --- | --- |")

    weekdays = ["월", "화", "수", "목", "금", "토", "일"]

    for offset in range(10):
        target = now + timedelta(days=offset)
        date_str = target.strftime("%Y%m%d")
        date_disp = f"{target.month}/{target.day}({weekdays[target.weekday()]})"
        days_ahead = offset + 1

        if date_str in short_daily:
            sd = short_daily[date_str]
            tmn = sd["tmn"] or "-"
            tmx = sd["tmx"] or "-"
            max_pop = max(sd["pops"]) if sd["pops"] else "-"
            if sd["skys"]:
                most_sky = max(set(sd["skys"]), key=sd["skys"].count)
                sky = _SKY_MAP.get(most_sky, "-")
            else:
                sky = "-"
            if sd["ptys"] and any(p > 0 for p in sd["ptys"]):
                most_pty = max((p for p in sd["ptys"] if p > 0), key=sd["ptys"].count)
                sky = _PTY_MAP.get(most_pty, sky)
            pop_str = f"{max_pop}%" if max_pop != "-" else "-"
            print(f"| {date_disp} | {tmn}°C | {tmx}°C | {pop_str} | {sky} |")
        elif days_ahead in mid_ta:
            mt = mid_ta.get(days_ahead, {})
            ml = mid_land.get(days_ahead, {})
            tmn = mt.get("min", "-")
            tmx = mt.get("max", "-")
            if "wfAm" in ml:
                wf = ml["wfAm"] if ml["wfAm"] == ml["wfPm"] else f"{ml['wfAm']}→{ml['wfPm']}"
                rn = max(ml.get("rnAm", 0), ml.get("rnPm", 0))
            else:
                wf = ml.get("wf", "-")
                rn = ml.get("rn", "-")
            pop_str = f"{rn}%" if rn != "-" else "-"
            print(f"| {date_disp} | {tmn}°C | {tmx}°C | {pop_str} | {wf} |")

    print("\n출처: 기상청")


def fetch_daily(city: str) -> None:
    """Fetch daily forecast using KMA short-term + mid-term APIs."""
    c = CITIES[city]
    now = _now_kst()

    # 1) 단기예보
    base_date, base_time = _get_latest_base_time(now)
    short_data = _kma_fcst_get("VilageFcstInfoService_2.0", "getVilageFcst", {
        "pageNo": 1, "numOfRows": 1000,
        "base_date": base_date, "base_time": base_time,
        "nx": c["nx"], "ny": c["ny"],
    })

    short_daily = {}
    if short_data:
        short_daily = _parse_short_term_daily(short_data["response"]["body"]["items"]["item"])
    else:
        print("단기예보 조회 실패, 중기예보만 표시합니다.", file=sys.stderr)

    # 2) 중기예보 (4~10일) — 병렬 호출
    mid_hour = 18 if now.hour >= 18 else 6
    mid_base = now.replace(hour=mid_hour, minute=0, second=0, microsecond=0)
    if now.hour < 6:
        mid_base = (now - timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)
    tmfc = mid_base.strftime("%Y%m%d%H%M")

    mid_ta, mid_land = _fetch_mid_term(c, tmfc)

    # 3) 출력
    _format_daily_output(c, now, short_daily, mid_ta, mid_land)


# --- past (ASOS 과거 관측) ---

def _wd36_to_ko(code: int) -> str:
    """Convert 36-direction wind code to Korean direction name."""
    if code <= 0 or code > 36:
        return "-"
    directions = [
        "북", "북북동", "북동", "동북동", "동", "동남동", "남동", "남남동",
        "남", "남남서", "남서", "서남서", "서", "서북서", "북서", "북북서",
    ]
    idx = round((code * 10) / 22.5) % 16
    return directions[idx]


def _parse_sfctm2_line(line: str) -> dict | None:
    """Parse a single data line from kma_sfctm2/3 response."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    parts = line.split()
    if len(parts) < 17:
        return None
    try:
        tm = parts[0]
        hour = int(tm[8:10])
        wd_code = int(parts[2]) if parts[2] not in ("-9", "-9.0") else -9
        ws = float(parts[3]) if parts[3] not in ("-9", "-9.0") else None
        ta = float(parts[11]) if parts[11] != "-9.0" else None
        td = float(parts[12]) if parts[12] != "-9.0" else None
        hm = float(parts[13]) if parts[13] != "-9.0" else None
        rn_day = float(parts[16]) if parts[16] != "-9.0" else None
        ps = float(parts[8]) if parts[8] != "-9.0" else None
        return {
            "hour": hour, "ta": ta, "td": td, "hm": hm,
            "ws": ws, "wd": _wd36_to_ko(wd_code),
            "rn_day": rn_day, "ps": ps,
        }
    except (ValueError, IndexError):
        return None


def fetch_past(city: str, date: str) -> None:
    """Fetch past hourly observation data from KMA ASOS API."""
    if not _KMA_API_KEY:
        print("KMA_API_KEY가 설정되지 않았습니다.", file=sys.stderr)
        return

    c = CITIES[city]
    asos = c.get("asos", 0)
    if not asos:
        print(f"{c['name']}에 대한 ASOS 관측소 번호가 등록되어 있지 않습니다.")
        return

    url = (
        f"{_KMA_ASOS_BASE}?tm1={date}0000&tm2={date}2300&stn={asos}"
        f"&help=0&authKey={_KMA_API_KEY}"
    )
    rows = []
    try:
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            print(f"API 오류: HTTP {r.status_code}")
            return
        for line in r.text.splitlines():
            parsed = _parse_sfctm2_line(line)
            if parsed:
                rows.append(parsed)
    except Exception as e:
        print(f"API 호출 실패: {e}")
        return

    if not rows:
        print(f"{date} 관측 데이터를 찾을 수 없습니다.")
        return

    formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
    print(f"## {c['name']} 과거 관측 ({formatted_date})\n")
    print("| 시간 | 기온 | 이슬점 | 습도 | 바람 | 기압 | 일강수 |")
    print("| --- | --- | --- | --- | --- | --- | --- |")

    for row in rows:
        ta = f"{row['ta']:.1f}°C" if row["ta"] is not None else "-"
        td = f"{row['td']:.1f}°C" if row["td"] is not None else "-"
        hm = f"{row['hm']:.0f}%" if row["hm"] is not None else "-"
        ws = f"{row['ws']:.1f}" if row["ws"] is not None else "-"
        ps = f"{row['ps']:.1f}hPa" if row["ps"] is not None else "-"
        rn = f"{row['rn_day']:.1f}mm" if row["rn_day"] is not None else "-"
        wind = f"{row['wd']} {ws}m/s" if ws != "-" else "-"
        print(f"| {row['hour']:02d}시 | {ta} | {td} | {hm} | {wind} | {ps} | {rn} |")

    print("\n출처: 기상청 (ASOS)")


# --- AirKorea helpers ---

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
    """에어코리아 일별 예보 등급을 조회한다."""
    if not _AIRKOREA_API_KEY:
        return {}
    today = _now_kst().strftime("%Y-%m-%d")
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
            for item in items:
                if item.get("informData") != target_date:
                    continue
                grade_str = item.get("informGrade", "")
                grades = dict(
                    g.split(" : ") for g in grade_str.split(",") if " : " in g
                )
                grade = grades.get(region, "")
                if grade:
                    key = "pm25" if code == "PM25" else "pm10"
                    result[key] = grade
                    break
        except Exception:
            continue
    return result


# --- AccuWeather (air quality only) ---

TIMEOUT = 15


def _create_session() -> requests.Session:
    """Create a session with browser-like headers."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.accuweather.com/",
    })
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


def _accu_base_url(city: str) -> str:
    key = CITIES[city]["accuweatherKey"]
    return f"https://www.accuweather.com/ko/kr/{city}/{key}"


def fetch_air_quality(city: str) -> None:
    session = _create_session()
    c = CITIES[city]
    key = c["accuweatherKey"]
    url = f"{_accu_base_url(city)}/air-quality-index/{key}"
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

    print(f"## {c['name']} 대기질\n")
    print(f"- **AQI**: {main_aqi} ({category})")

    pollutants = soup.select(".air-quality-pollutant")
    if pollutants:
        print()
        print("| 오염물질 | 등급 | AQI | 농도 |")
        print("| --- | --- | --- | --- |")
        names = {
            "PM2.5": "초미세먼지 (PM2.5)", "PM10": "미세먼지 (PM10)",
            "NO2": "이산화질소 (NO2)", "SO2": "이산화황 (SO2)",
            "O3": "오존 (O3)", "CO": "일산화탄소 (CO)",
        }
        for p in pollutants:
            dt = p.select_one(".display-type")
            pc = p.select_one(".category")
            pi = p.select_one(".pollutant-index")
            pcon = p.select_one(".pollutant-concentration")
            name_raw = dt.get_text(strip=True) if dt else "-"
            print(f"| {names.get(name_raw, name_raw)} | "
                  f"{pc.get_text(strip=True) if pc else '-'} | "
                  f"{pi.get_text(strip=True) if pi else '-'} | "
                  f"{pcon.get_text(strip=True) if pcon else '-'} |")

    print("\n출처: AccuWeather")


def fetch_air_hourly(city: str) -> None:
    session = _create_session()
    c = CITIES[city]
    key = c["accuweatherKey"]
    url = f"{_accu_base_url(city)}/air-quality-index/{key}"
    soup = _fetch(session, url)

    data_el = soup.select_one("[data-points]")
    if not data_el:
        print("시간별 대기질 데이터를 찾을 수 없습니다.")
        return

    points = json.loads(data_el.get("data-points"))
    if not points:
        print("시간별 대기질 데이터가 비어 있습니다.")
        return

    now = _now_kst()
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

    print(f"## {c['name']} 시간별 대기질 (24시간)\n")
    print("| 시간 | AQI | 등급 | PM2.5 | PM10 | O3 | NO2 |")
    print("| --- | --- | --- | --- | --- | --- | --- |")

    for i, pt in enumerate(points):
        xval = json.loads(pt["XValues"][0])
        aqi = xval["overallIndex"]
        category = xval["category"]
        poll = xval.get("pollutants", {})
        time_label = hours[i] if i < len(hours) else f"#{i}"
        print(f"| {time_label} | {aqi:.0f} | {category} | "
              f"{poll.get('PM2_5', '-')} | {poll.get('PM10', '-')} | "
              f"{poll.get('O3', '-')} | {poll.get('NO2', '-')} |")

    print("\n출처: AccuWeather")


# --- main ---

def main():
    parser = argparse.ArgumentParser(
        description="Weather information lookup (KMA, AirKorea, AccuWeather)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "type",
        choices=["now", "daily", "hourly", "air", "air-hourly", "past"],
        help="Query type",
    )
    parser.add_argument(
        "--city", default="seoul",
        help=f"City name (default: seoul). Available: {', '.join(sorted(CITIES.keys()))}",
    )
    parser.add_argument(
        "--day", type=int, default=1,
        help="Day for hourly forecast: 1=today, 2=tomorrow, 3=day after (default: 1)",
    )
    parser.add_argument(
        "--date", default=None,
        help="Date for past observation: YYYYMMDD format (e.g., 20260319)",
    )

    args = parser.parse_args()

    if args.city not in CITIES:
        print(
            f"알 수 없는 도시: {args.city}\n"
            f"등록된 도시: {', '.join(sorted(CITIES.keys()))}\n"
            f"새 도시를 추가하려면 references/cities.json 파일을 편집하세요.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        if args.type == "now":
            fetch_now(args.city)
        elif args.type == "daily":
            fetch_daily(args.city)
        elif args.type == "hourly":
            fetch_hourly(args.city, args.day)
        elif args.type == "air":
            fetch_air_quality(args.city)
        elif args.type == "air-hourly":
            fetch_air_hourly(args.city)
        elif args.type == "past":
            date = args.date or _now_kst().strftime("%Y%m%d")
            fetch_past(args.city, date)
    except requests.RequestException as e:
        print(f"네트워크 오류: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
