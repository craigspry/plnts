import csv
import cherrypy
import ephem
import geoip2.database


def get_obj_details(obj, name, lat, lon):
    # Create an observer object for Melbourne
    observer = ephem.Observer()
    observer.lat = lat
    observer.lon = lon
    # Set the date and time to now
    observer.date = ephem.now()
    # Compute the altitude of Saturn
    obj.compute(observer)
    # Get the elevation of Saturn in degrees
    elevation = obj.alt * 180 / ephem.pi
    azimuth = obj.az * 180 / ephem.pi
    rising_time = None
    if elevation < 0:
        rising_time = observer.next_rising(obj)
    else:
        rising_time = observer.previous_rising(obj)
    setting_time = observer.next_setting(obj)
    transit_time = observer.next_transit(obj)
    return (elevation, azimuth, rising_time, setting_time, transit_time)


def pretty_print_obj(obj, name, lat, lon):
    details = get_obj_details(obj, name, lat, lon)
    pretty_name = name.ljust(15)
    return f"  {pretty_name}| {details[0]:>7.2f} | {details[1]:>7.2f} | {details[2].datetime():%Y-%m-%d %H:%M:%S} | {details[3].datetime():%Y-%m-%d %H:%M:%S} | {details[4].datetime():%Y-%m-%d %H:%M:%S}\n"


def do_city_lookup(city):
    try:
        with open("./geoip/worldcities.csv", 'r') as f:
            cities = list(csv.reader(f))
            return next(filter(lambda x : x[0] == city, cities), None)
    except Exception:
        return None


def do_location_lookup(address):
    try:
        with geoip2.database.Reader('./geoip/GeoLite2-City_20230908/GeoLite2-City.mmdb') as reader:
            response = reader.city(address)
            match = do_city_lookup(response.city.name)
            if match:
                return match[2], match[3], response.city.name
        return 0, 0, response.city.name
    except Exception:
        return 0, 0, "Null Island"


class Planets(object):
    @cherrypy.expose
    def index(self, city=None):
        lat = 0
        lon = 0
        if city:
            location = do_city_lookup(city)
            if location:
                lat = location[2]
                lon = location[3]
        else:
            ip_address = cherrypy.request.remote.ip
            location = do_location_lookup(ip_address)
            lat, lon, city = do_location_lookup(location)

        user_agent = cherrypy.request.headers.get('User-Agent')
        rtn = f"Plantes rise set time in UTC for {city}\n"
        rtn += "  Body           |Elevation|Azimuth  |Rise Time            |Set Time             |Transit Time\n"
        rtn += "--------------------------------------------------------------------------------------------------------\n"
        sun = ephem.Sun()
        rtn += pretty_print_obj(sun, "Sun", lat, lon)
        mercury = ephem.Mercury()
        rtn += pretty_print_obj(mercury, "Mercury", lat, lon)
        venus = ephem.Venus()
        rtn += pretty_print_obj(venus, "Venus", lat, lon)
        moon = ephem.Moon()
        rtn += pretty_print_obj(moon, "Moon", lat, lon)
        mars = ephem.Mars()
        rtn += pretty_print_obj(mars, "Mars", lat, lon)
        jupiter = ephem.Jupiter()
        rtn += pretty_print_obj(jupiter, "Jupiter", lat, lon)
        saturn = ephem.Saturn()
        rtn += pretty_print_obj(saturn, "Saturn", lat, lon)
        rtn += "\n\n\n This product includes GeoLite2 Data created by MaxMind, available from https://www.maxmind.com/.\n"
        if 'curl' not in user_agent:
            rtn = "<html><body>" + rtn.replace('\n', '<br>') + "<p>Best viewed with curl</p></body></html>"
        else:
            cherrypy.response.headers['Content-Type'] = 'plain/text'
        return str.encode(rtn)


if __name__ == '__main__':
    cherrypy.quickstart(Planets(), '/')
