# File to handle both forward and reverse geocoding

from pathlib import Path
import json
import urllib.parse
import urllib.request
from collections import namedtuple
import time
import math
import socket

BASE_SEARCH_URL = 'https://nominatim.openstreetmap.org/search?'
BASE_REVERSE_URL = 'https://nominatim.openstreetmap.org/reverse?'

HEADER = 'https://www.ics.uci.edu/~thornton/ics32a/ProjectGuide/Project3/collina2'

# EXAMPLE:
# https://nominatim.openstreetmap.org/search?q=Bren+Hall&format=json

# distance = float, direction = str (N = North, S = South, etc.)
Position = namedtuple('Position', 'distance direction')
# lat and lon are Position namedtuples
Coordinate = namedtuple('Coordinate', 'lat lon')

directions = {
    'lat': ['N', 'S'],
    'lon': ['E', 'W']
    }

class NetworkError(Exception):
    def __init__(self, url):
        self.url = url
        self.error = 'NETWORK'

class APIError(Exception):
    def __init__(self, status, url, error):
        self.status = status
        self.url = url
        self.error = error

class FileError(Exception):
    def __init__(self, path, error):
        self.path = path
        self.error = error

def _get_position(val, axis) -> Position:
        distance = abs(val)
        direction = directions[axis][distance != val]
        return Position(distance, direction)

class Location:
    def __init__(self, lat, lon):
        lat_position = _get_position(lat, 'lat')
        lon_position = _get_position(lon, 'lon')
        self._coordinate = Coordinate(lat_position,
                                      lon_position)

    def get_coord(self) -> Coordinate:
        return self._coordinate

    def get_lat(self) -> float:
        'Returns the float value of the Location\'s latitude'
        lat = self._coordinate.lat
        dir_sign = 1
        if lat.direction == directions['lat'][1]:
            dir_sign = -1
        lat_val = dir_sign * lat.distance
        return lat_val

    def get_lon(self) -> float:
        'Returns the float value of the Location\'s longitude'
        lon = self._coordinate.lon
        dir_sign = 1
        if lon.direction == directions['lon'][1]:
            dir_sign = -1
        lon_val = dir_sign * lon.distance
        return lon_val

    def get_str(self) -> str:
        '''Returns the location in this format:
        {lat_dist}/{lat_dir} {lon_dist}/{lon_dir}
        where lat = latitude, dist = distance, and dir = direction'''
        lat = self._coordinate.lat
        lon = self._coordinate.lon
        location_string = ''
        location_string += str(lat.distance) + '/' + lat.direction
        location_string += ' '
        location_string += str(lon.distance) + '/' + lon.direction
        return location_string

    def show(self) -> None:
        '''Prints the location in this format:
        CENTER {lat_dist}/{lat_dir} {lon_dist}/{lon_dir}
        where lat = latitude, dist = distance, and dir = direction'''
        lat = self._coordinate.lat
        lon = self._coordinate.lon
        print(lat.distance, lat.direction, sep = '/', end = '')
        print(' ', end = '')
        print(lon.distance, lon.direction, sep = '/')

    

def get_distance(loc1: Location, loc2: Location) -> float:
        'Returns the distance (in miles) from one location to another'
        lat1_rads = math.radians(loc1.get_lat())
        lat2_rads = math.radians(loc2.get_lat())
        lon1_rads = math.radians(loc1.get_lon())
        lon2_rads = math.radians(loc2.get_lon())
        dlat = lat1_rads - lat2_rads
        dlon = lon1_rads - lon2_rads
        alat = (lat1_rads + lat2_rads) / 2
        R = 3958.8 # radius of Earth in miles
        x = dlon * math.cos(alat)
        d = math.sqrt(x ** 2 + dlat ** 2) * R
        return d

class ForwardAPI:
    def __init__(self, location_desc):
        self._data = None
        time.sleep(1)
        query_params = [('q', location_desc), ('format', 'json')]
        encoded_params = urllib.parse.urlencode(query_params)
        url = f'{BASE_SEARCH_URL}{encoded_params}'
        request = urllib.request.Request(
            url,
            headers = {
                'Referer': HEADER
                }
            )
        response = None
        try:
            response = urllib.request.urlopen(request)    
            if response.status != 200:
                raise APIError(response.status, response.url, 'NOT 200')
            json_text = response.read().decode(encoding = 'utf-8')
            self._data = json.loads(json_text)
            if len(self._data) == 0:
                raise APIError(response.status, response.url, 'FORMAT')
        except socket.gaierror:
            raise NetworkError(url)
        except urllib.error.URLError:
            raise NetworkError(url)
        finally:
            if response != None:
                response.close()

    def print_data(self, keyword) -> None:
        'Prints the file data that contains the keyword'
        for element in self._data:
            print('-----')
            for item in element.items():
                key, value = item
                if keyword in key:
                    print('FIELD: ' + str(key))
                    print('VALUE: ' + str(value))
                    print('-----')

    def get_location(self) -> Location:
        lat = float(self._data[0]['lat'])
        lon = float(self._data[0]['lon'])
        location = Location(lat, lon)
        return location

class ForwardFile:
    def __init__(self, path_input):
        path = Path(path_input)
        file = None
        self._data = None
        try:
            file = path.open('r')
            text = file.read()
            self._data = json.loads(text)
            if len(self._data) == 0:
                raise FileError(path, 'FORMAT')
        except FileNotFoundError:
            raise FileError(path, 'MISSING')
        finally:
            if file != None:
                file.close()

    def print_data(self, keyword) -> None:
        'Prints the file data that contains the keyword'
        for element in self._data:
            print('-----')
            for item in element.items():
                key, value = item
                if keyword in key:
                    print('FIELD: ' + str(key))
                    print('VALUE: ' + str(value))
                    print('-----')


    def get_location(self) -> Location:
        'Gets the location from a file of the center'
        lat = float(self._data[0]['lat'])
        lon = float(self._data[0]['lon'])
        location = Location(lat, lon)
        return location

class ReverseAPI:
    def __init__(self, location: Location):
        # TODO:
        self._data = []
        time.sleep(1) # pause for 1 second
        query_params = [('lat', location.get_lat()),
                        ('lon', location.get_lon()),
                        ('format', 'json')]
        encoded_params = urllib.parse.urlencode(query_params)
        url = f'{BASE_REVERSE_URL}{encoded_params}'
        request = urllib.request.Request(
            url,
            headers = {
                'Referer': HEADER
                }
            )
        response = None
        try:
            response = urllib.request.urlopen(request)    
            if response.status != 200:
                raise APIError(response.status, response.url, 'NOT 200')
            json_text = response.read().decode(encoding = 'utf-8')
            self._data = json.loads(json_text)
            if len(self._data) == 0:
                raise APIError(response.status, response.url, 'FORMAT')
        except socket.gaierror:
            raise NetworkError(url)
        except urllib.error.URLError:
            raise NetworkError(url)
        finally:
            if response != None:
                response.close()

    def get_description(self) -> str:
        return self._data['display_name']

class ReverseFile:
    def __init__(self, path_input: str):
        path = Path(path_input)
        file = None
        self._data = None
        try:
            file = path.open('r')
            text = file.read()
            self._data = json.loads(text)
            if len(self._data) == 0:
                raise FileError(path, 'FORMAT')
        except FileNotFoundError:
            raise FileError(path, 'MISSING')
        finally:
            if file != None:
                file.close()

    def get_description(self) -> str:
        return self._data['display_name']
