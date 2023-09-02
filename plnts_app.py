import cherrypy
import ephem
from datetime import datetime 

def get_obj_details(obj, name):
    # Melbourne, Australia coordinates
    lat = '-37.8136'  # Latitude
    lon = '144.9631'  # Longitude
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
    return (elevation, azimuth, rising_time, setting_time)

def pretty_print_obj(obj, name):
    details = get_obj_details(obj, name)
    pretty_name = name.ljust(15)
    return f"  {pretty_name}| {details[0]:>7.2f} | {details[1]:>7.2f} | {details[2].datetime():%Y-%m-%d %H:%M:%S} | {details[3].datetime():%Y-%m-%d %H:%M:%S}\n"

def get_rise_set(obsv, obj):
    # obj.compute(obsv)
    if obj.alt < 0:
        return obsv.next_rising(obj), obsv.next_transit(obj), obsv.next_setting(obj), obj.az, obj.alt
    else:
        return obsv.previous_rising(obj).datetime(), obsv.next_transit(obj), obsv.next_setting(obj), obj.az, obj.alt

class Planets(object):
    @cherrypy.expose
    def index(self):
        rtn = "  Body           |Elevation|Azimuth  |Rise Time            |Set Time\n"
        rtn += "----------------------------------------------------------------------------------\n"
        sun = ephem.Sun()
        rtn += pretty_print_obj(sun, "Sun")
        moon = ephem.Moon()
        rtn += pretty_print_obj(moon, "Moon")
        saturn = ephem.Saturn()
        rtn += pretty_print_obj(saturn, "Saturn")
        jupiter = ephem.Jupiter()
        rtn += pretty_print_obj(jupiter, "Jupiter")
        mars = ephem.Mars()
        rtn += pretty_print_obj(mars, "Mars")
        cherrypy.response.headers['Content-Type'] = 'plain/text'
        return str.encode(rtn)

if __name__ == '__main__':
   cherrypy.quickstart(Planets(), '/')

