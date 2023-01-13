# File to handle sensor information

from pathlib import Path
import json
import urllib.parse
import urllib.request
import time
import math
from decimal import Decimal
from collections import namedtuple
import geocoding
import socket

_SHOW_DEBUG_TRACE = False

SENSOR_DATA_URL = 'https://www.purpleair.com/data.json'

Range = namedtuple('Range', 'min max')

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

def _proper_round(num: float) -> int:
    tenth_digit = int(num * 10) % 10
    if tenth_digit < 5:
        return int(num)
    else:
        return int(num) + 1

assert _proper_round(250.5) == 251
assert _proper_round(49.5) == 50

def _subtract(num1: float, num2: float) -> float:
    int_num1 = int(num1 * 1e9)
    int_num2 = int(num2 * 1e9)
    diff = int_num1 - int_num2
    diff /= 1e9
    return round(diff, 9)

assert _subtract(5.123, 4.122) == 1.001
assert _subtract(49.494, 49.494) == 0.000
assert _subtract(49.495, 49.494999999999999) == 0.000
assert _subtract(49.495000001, 49.495) == 0.000000001
assert _subtract(49.4950000001, 49.495) == 0.0000000000

def calculate_aqi(pm: float) -> int:
    aqi = None
    if pm >= 0.0 and pm < 12.1:
        aqi = _proper_round(pm * 50 / 12.0)
    elif pm >= 12.1 and pm < 35.5:
        pm_offset = _subtract(pm, 12.1)
        aqi = _proper_round(pm_offset * 49 / 23.3) + 51
    elif pm >= 35.5 and pm < 55.5:
        pm_offset = _subtract(pm, 35.5)
        aqi = _proper_round(pm_offset * 49 / 19.9) + 101
    elif pm >= 55.5 and pm < 150.5:
        pm_offset = _subtract(pm, 55.5)
        aqi = _proper_round(pm_offset * 49 / 94.9) + 151
    elif pm >= 150.5 and pm < 250.5:
        pm_offset = _subtract(pm, 150.5)
        aqi = _proper_round(pm_offset * 99 / 99.9) + 201
    elif pm >= 250.5 and pm < 350.5:
        pm_offset = _subtract(pm, 250.5)
        aqi = _proper_round(pm_offset * 99 / 99.9) + 301
    elif pm >= 350.5 and pm < 500.5:
        pm_offset = _subtract(pm, 350.5)
        aqi = _proper_round(pm_offset * 99 / 149.9) + 401
    elif pm >= 500.5:
        aqi = 501

    return aqi

assert calculate_aqi(-1) == None
assert calculate_aqi(0) == 0
assert calculate_aqi(0.0) == 0
assert calculate_aqi(0.1) == 0
assert calculate_aqi(6.0) == 25
assert calculate_aqi(12.0) == 50
assert calculate_aqi(12.1) == 51
assert calculate_aqi(23.75) == 76
assert calculate_aqi(35.4) == 100
assert calculate_aqi(35.5) == 101
assert calculate_aqi(45.45) == 126
assert calculate_aqi(55.4) == 150
assert calculate_aqi(55.5) == 151
assert calculate_aqi(102.95) == 176
assert calculate_aqi(150.4) == 200
assert calculate_aqi(150.5) == 201
assert calculate_aqi(200.45) == 251
assert calculate_aqi(250.4) == 300
assert calculate_aqi(250.5) == 301
assert calculate_aqi(300.45) == 351
assert calculate_aqi(350.4) == 400
assert calculate_aqi(350.5) == 401
assert calculate_aqi(425.45) == 451
assert calculate_aqi(500.4) == 500
assert calculate_aqi(500.5) == 501
assert calculate_aqi(19023.123) == 501        

def _test_data(data: list, n: int) -> None:
        '''Prints/Tests an aspect of the selective sensor data
        that meets criteria based on pm, age, Type, Lat, and/or Lon'''
        count = 0
        for sensor in data:
            if (count < n):
                count += 1
                print(f'----- SENSOR {count} -----\n')
                print('pm =', sensor[1])
                print('age =', sensor[4])
                print('Type =', sensor[25])
                print('Lat =', sensor[27])
                print('Lon =', sensor[28])
                print()

class SensorAPI:
    def __init__(self):
        self._data = None
        request = urllib.request.Request(SENSOR_DATA_URL)
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

    def get_data(self) -> list:
        return self._data['data']
        
class SensorFile:
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

    def get_data(self) -> list:
        return self._data['data']

def _sort_by_aqi(sensors: list) -> list:
    sorted_sensors = []
    highest_aqi = 0
    for sensor in sensors:
        aqi = calculate_aqi(sensor[1])
        if aqi > highest_aqi:
            highest_aqi = aqi
            sorted_sensors.insert(0, sensor)
        else:
            index = 0
            inserted_sensor = False
            for sorted_sensor in sorted_sensors:
                sub_aqi = calculate_aqi(sorted_sensor[1])
                if aqi > sub_aqi:
                    sorted_sensors.insert(index, sensor)
                    inserted_sensor = True
                    break
                else:
                    index += 1
            if not inserted_sensor:
                sorted_sensors.append(sensor)
                
    return sorted_sensors

def _remove_null_sensors(sensors: list) -> list:
    '''Removes sensors if they contain null in important elements'''
    filtered_sensors = []
    count = 0
    for sensor in sensors:
        if (sensor[1] == None or
            sensor[4] == None or
            sensor[25] == None or
            sensor[27] == None or
            sensor[28] == None):
            count += 1
        else:
            filtered_sensors.append(sensor)
    if _SHOW_DEBUG_TRACE:
        print('Sensors with null data:', count)
    return filtered_sensors

def _remove_indoor_sensors(sensors: list) -> list:
    '''Removes indoor sensors'''
    filtered_sensors = []
    count = 0
    for sensor in sensors:
        if (sensor[25] == 1):
            count += 1
        else:
            filtered_sensors.append(sensor)
    if _SHOW_DEBUG_TRACE:
        print('Indoor Sensors:', count)
    return filtered_sensors

def _remove_old_sensors(sensors: list) -> list:
    '''Removes indoor sensors'''
    filtered_sensors = []
    count = 0
    for sensor in sensors:
        if (sensor[4] > 3600):
            count += 1
        else:
            filtered_sensors.append(sensor)
    if _SHOW_DEBUG_TRACE:
        print('Old Sensors:', count)
    return filtered_sensors

def _filter_by_range(sensors: list,
                     center: geocoding.Location,
                     range_miles: int) -> list:
    '''Removes sensors if they are outside of the range'''
    filtered_sensors = []
    count = 0
    for sensor in sensors:
        sensor_location = geocoding.Location(sensor[27], sensor[28])
        if geocoding.get_distance(center, sensor_location) <= range_miles:
            # print(center.get_str())
            # print(sensor_location.get_str())
            # print(geocoding.get_distance(center, sensor_location))
            filtered_sensors.append(sensor)
        else:
            count += 1
    if _SHOW_DEBUG_TRACE:
        print('Sensors out of range:', count)
    return filtered_sensors

def _filter_by_aqi(sensors: list, threshold: int) -> list:
    '''Removes sensors below the certain AQI threshold'''
    filtered_sensors = []
    count = 0
    for sensor in sensors:
        aqi = calculate_aqi(sensor[1])
        if (aqi < threshold):
            count += 1
        else:
            filtered_sensors.append(sensor)
    if _SHOW_DEBUG_TRACE:
        print('Below Threshold Sensors:', count)
    return filtered_sensors

def _get_n_elements(elements: list,
                   n: int) -> list:
    '''Gets the first n values from a list'''
    n_elements = []
    count = 0
    for element in elements:
        if count < n:
            n_elements.append(element)
            count += 1
        else:
            return n_elements
    return n_elements

def _count_sensors(sensors: list) -> int:
    count = len(sensors)
    if _SHOW_DEBUG_TRACE:
        print('Remaining Sensors:', count)
    return count

def find_sensors(center: geocoding.Location,
                 range_miles: int, threshold: int, n: int,
                 sensor_data: list) -> list[geocoding.Location]:
    '''Uses the sensor data to find the sensors that are in the
    specified range (in miles) of the center location; then
    determines which of those sensors have the highest AQI
    values and returns the location of the first n sensors
    that are at or above the AQI threshold'''
    # print('pm =', sensor[1])
    # print('age =', sensor[4])
    # print('Type =', sensor[25])
    # print('Lat =', sensor[27])
    # print('Lon =', sensor[28])
    _count_sensors(sensor_data)
    
    working_sensors = _remove_null_sensors(sensor_data)
    _count_sensors(working_sensors)
    
    outdoor_sensors = _remove_indoor_sensors(working_sensors)
    _count_sensors(outdoor_sensors)
    
    new_sensors = _remove_old_sensors(outdoor_sensors)
    _count_sensors(new_sensors)
    
    sensors_in_range = _filter_by_range(new_sensors,
                                        center,
                                        range_miles)
    _count_sensors(sensors_in_range)
    
    aqi_sorted_sensors = _sort_by_aqi(sensors_in_range)
    _count_sensors(aqi_sorted_sensors)

    aqi_filtered_sensors = _filter_by_aqi(aqi_sorted_sensors,
                                          threshold)
    _count_sensors(aqi_filtered_sensors)

    first_n_sensors = _get_n_elements(aqi_filtered_sensors, n)
    _count_sensors(first_n_sensors)
    
    if _SHOW_DEBUG_TRACE:
        _test_data(first_n_sensors, 5)
        # _print_data(first_n_sensors)

    return first_n_sensors
    

