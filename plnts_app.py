import csv
import os
from pathlib import Path

import cherrypy
import ephem
import geoip2.database
from geoip2.errors import AddressNotFoundError

ROOT = Path(__file__).resolve().parent
DEFAULT_MMDB = ROOT / "geoip" / "GeoLite2-City_20230908" / "GeoLite2-City.mmdb"
DEFAULT_CITIES = ROOT / "geoip" / "worldcities.csv"
MAXMIND_NOTE = (
    "This product includes GeoLite2 Data created by MaxMind, "
    "available from https://www.maxmind.com/."
)

_mmdb_reader = None
_city_index = None


def _env_path(name, default):
    value = os.environ.get(name)
    return Path(value) if value else Path(default)


def load_city_index(path=None):
    """Map lowercased city_ascii / city -> (lat, lon, display_name). First wins."""
    csv_path = Path(path) if path else _env_path("PLNTS_CITIES", DEFAULT_CITIES)
    index = {}
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                lat = float(row["lat"])
                lon = float(row["lng"])
            except (KeyError, TypeError, ValueError):
                continue
            display = row.get("city_ascii") or row.get("city") or "Unknown"
            for key in (row.get("city_ascii"), row.get("city")):
                if not key:
                    continue
                lowered = key.strip().lower()
                if lowered and lowered not in index:
                    index[lowered] = (lat, lon, display)
    return index


def get_city_index():
    global _city_index
    if _city_index is None:
        _city_index = load_city_index()
    return _city_index


def get_mmdb_reader():
    global _mmdb_reader
    if _mmdb_reader is None:
        mmdb_path = _env_path("PLNTS_MMDB", DEFAULT_MMDB)
        _mmdb_reader = geoip2.database.Reader(str(mmdb_path))
    return _mmdb_reader


def _is_trusted_proxy(remote):
    """Loopback or private peers (local nginx / Docker bridge) may set client IP headers."""
    if remote in ("127.0.0.1", "::1", "localhost"):
        return True
    if remote.startswith("10.") or remote.startswith("192.168."):
        return True
    if remote.startswith("172."):
        try:
            second = int(remote.split(".")[1])
        except (IndexError, ValueError):
            return False
        return 16 <= second <= 31
    return False


def client_ip():
    """Prefer X-Real-IP / X-Forwarded-For when the peer is a trusted local proxy."""
    remote = cherrypy.request.remote.ip
    if _is_trusted_proxy(remote):
        real_ip = cherrypy.request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        forwarded = cherrypy.request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return remote


def lookup_city(name):
    if not name:
        return None
    return get_city_index().get(name.strip().lower())


def lookup_ip(address):
    try:
        response = get_mmdb_reader().city(address)
    except (AddressNotFoundError, ValueError, OSError):
        return None
    lat = response.location.latitude
    lon = response.location.longitude
    if lat is None or lon is None:
        return None
    city = response.city.name or response.country.name or address
    return float(lat), float(lon), city


def get_obj_details(obj, lat, lon):
    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.date = ephem.now()
    obj.compute(observer)
    elevation = obj.alt * 180 / ephem.pi
    azimuth = obj.az * 180 / ephem.pi
    if elevation < 0:
        rising_time = observer.next_rising(obj)
    else:
        rising_time = observer.previous_rising(obj)
    setting_time = observer.next_setting(obj)
    transit_time = observer.next_transit(obj)
    return elevation, azimuth, rising_time, setting_time, transit_time


def pretty_print_obj(obj, name, lat, lon):
    details = get_obj_details(obj, lat, lon)
    pretty_name = name.ljust(15)
    return (
        f"  {pretty_name}| {details[0]:>7.2f} | {details[1]:>7.2f} | "
        f"{details[2].datetime():%Y-%m-%d %H:%M:%S} | "
        f"{details[3].datetime():%Y-%m-%d %H:%M:%S} | "
        f"{details[4].datetime():%Y-%m-%d %H:%M:%S}\n"
    )


def resolve_location(city=None, lat=None, lon=None):
    if lat is not None and lon is not None:
        try:
            return float(lat), float(lon), f"{float(lat):.4f},{float(lon):.4f}"
        except (TypeError, ValueError):
            return None, None, "invalid lat/lon"
    if city:
        match = lookup_city(city)
        if not match:
            return None, None, None
        return match
    ip_address = client_ip()
    match = lookup_ip(ip_address)
    if match:
        return match
    return 0.0, 0.0, "Null Island"


class Planets(object):
    @cherrypy.expose
    def index(self, city=None, lat=None, lon=None):
        resolved_lat, resolved_lon, label = resolve_location(city=city, lat=lat, lon=lon)
        if city and resolved_lat is None and label is None:
            cherrypy.response.status = 404
            msg = f"Unknown city: {city}\n"
            return _format_body(msg)

        if lat is not None and lon is not None and resolved_lat is None:
            cherrypy.response.status = 400
            return _format_body("Invalid lat/lon\n")

        rtn = f"Planets rise set time in UTC for {label}\n"
        rtn += (
            "  Body           |Elevation|Azimuth  |Rise Time            |"
            "Set Time             |Transit Time\n"
        )
        rtn += (
            "-------------------------------------------------------------"
            "---------------------------\n"
        )
        for body, name in (
            (ephem.Sun(), "Sun"),
            (ephem.Mercury(), "Mercury"),
            (ephem.Venus(), "Venus"),
            (ephem.Moon(), "Moon"),
            (ephem.Mars(), "Mars"),
            (ephem.Jupiter(), "Jupiter"),
            (ephem.Saturn(), "Saturn"),
        ):
            rtn += pretty_print_obj(body, name, resolved_lat, resolved_lon)
        rtn += f"\n\n\n {MAXMIND_NOTE}\n"
        return _format_body(rtn)


def _format_body(text):
    user_agent = cherrypy.request.headers.get("User-Agent") or ""
    if "curl" not in user_agent.lower():
        html = "<html><body>" + text.replace("\n", "<br>") + "<p>Best viewed with curl</p></body></html>"
        return html.encode("utf-8")
    cherrypy.response.headers["Content-Type"] = "text/plain; charset=utf-8"
    return text.encode("utf-8")


def main():
    # Warm indexes so the first request is fast and failures are early.
    get_city_index()
    get_mmdb_reader()
    port = int(os.environ.get("PORT", "8080"))
    host = os.environ.get("PLNTS_HOST", "0.0.0.0")
    cherrypy.config.update(
        {
            "server.socket_port": port,
            "server.thread_pool": 10,
            "server.socket_host": host,
        }
    )
    cherrypy.quickstart(Planets(), "/")


if __name__ == "__main__":
    main()
