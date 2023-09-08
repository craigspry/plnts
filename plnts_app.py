import cherrypy
import ephem


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
    transit_time = observer.next_transit(obj)
    return (elevation, azimuth, rising_time, setting_time, transit_time)


def pretty_print_obj(obj, name):
    details = get_obj_details(obj, name)
    pretty_name = name.ljust(15)
    return f"  {pretty_name}| {details[0]:>7.2f} | {details[1]:>7.2f} | {details[2].datetime():%Y-%m-%d %H:%M:%S} | {details[3].datetime():%Y-%m-%d %H:%M:%S} | {details[4].datetime():%Y-%m-%d %H:%M:%S}\n"


class Planets(object):
    @cherrypy.expose
    def index(self):
        user_agent = cherrypy.request.headers.get('User-Agent')
        rtn = "  Body           |Elevation|Azimuth  |Rise Time            |Set Time             |Transit Time\n"
        rtn += "--------------------------------------------------------------------------------------------------------\n"
        sun = ephem.Sun()
        rtn += pretty_print_obj(sun, "Sun")
        mercury = ephem.Mercury()
        rtn += pretty_print_obj(mercury, "Mercury")
        venus = ephem.Venus()
        rtn += pretty_print_obj(venus, "Venus")
        moon = ephem.Moon()
        rtn += pretty_print_obj(moon, "Moon")
        mars = ephem.Mars()
        rtn += pretty_print_obj(mars, "Mars")
        jupiter = ephem.Jupiter()
        rtn += pretty_print_obj(jupiter, "Jupiter")
        saturn = ephem.Saturn()
        rtn += pretty_print_obj(saturn, "Saturn")
        if 'curl' not in user_agent:
            rtn = "<html><body>" + rtn.replace('\n', '<br>') + "</body></html>"
        else:
            cherrypy.response.headers['Content-Type'] = 'plain/text'
        return str.encode(rtn)


if __name__ == '__main__':
    cherrypy.quickstart(Planets(), '/')
