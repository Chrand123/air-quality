# Main Program - Project 3

from pathlib import Path
import geocoding
import sensor
import json
import time

TYPES_OF_INPUT = {
    'center': {
        'nominatim': 'CENTER NOMINATIM ',
        'file': 'CENTER FILE '
        },
    'range': 'RANGE ',
    'threshold': 'THRESHOLD ',
    'max': 'MAX ',
    'aqi': {
        'purpleair': 'AQI PURPLEAIR',
        'file': 'AQI FILE '
        },
    'reverse': {
        'nominatim': 'REVERSE NOMINATIM',
        'files': 'REVERSE FILES '
        }
    }


def _extract_from_input(the_input: str) -> (str, str):
    '''Sees if the input provided is valid based on the type(s) of input;
    If valid, returns a tuple of the input type and the rest of input;
    else, returns a tuple of None and None'''
    for input_type in TYPES_OF_INPUT.items():
        if type(input_type[1]) == dict:
            for sub_input_type in input_type[1].items():
                if the_input.startswith(sub_input_type[1]):
                    rest_of_input = the_input.replace(sub_input_type[1], '')
                    return (sub_input_type[0], rest_of_input)
        else:
            if the_input.startswith(input_type[1]):
                rest_of_input = the_input.replace(input_type[1], '')
                return (input_type[0], rest_of_input)

    # invalid input
    return (None, None)

assert _extract_from_input('CENTER NOMINATIM ') == ('nominatim', '')
assert _extract_from_input('CENTER FILE a') == ('file', 'a')
assert _extract_from_input('') == (None, None)
assert _extract_from_input('1') == (None, None)
assert _extract_from_input('RANGE') == (None, None)
assert _extract_from_input('RANGERANGE ') == (None, None)
assert _extract_from_input(' RANGE ') == (None, None)
assert _extract_from_input('RANGE 1290') == ('range', '1290')
assert _extract_from_input('AQI PURPLEAIR') == ('purpleair', '')
assert _extract_from_input('REVERSE NOMINATIM') == ('nominatim', '')
assert _extract_from_input('REVERSE NOMINATIM ') == ('nominatim', ' ')
assert _extract_from_input('REVERSE FILE 1234') == (None, None)
assert _extract_from_input('REVERSE FILES') == (None, None)
assert _extract_from_input('REVERSE FILES ') == ('files', '')
assert _extract_from_input('REVERSE FILES esr ever') == ('files', 'esr ever')

def _ask_for_center() -> geocoding.ForwardFile or geocoding.ForwardAPI:
    '''Extracts the type of input and returns a Location object'''
    
    type_of_input, center_input = _extract_from_input(input())

    if type_of_input == None or center_input == '':
        raise ValueError

    if type_of_input == 'nominatim':
        # for Nominatim's API
        return geocoding.ForwardAPI(center_input)
    else:
        # for path to file
        return geocoding.ForwardFile(center_input)

def _ask_for_positive_int() -> int:
    '''Extracts the type of input and returns a positive integer'''
    type_of_input, int_input = _extract_from_input(input())

    int_val = int(int_input)

    if type_of_input == None or int_val < 0:
        raise ValueError

    return int_val

def _ask_for_aqi() -> sensor.SensorFile or sensor.SensorAPI:
    '''Extracts the type of input and returns an AQI object'''
    
    type_of_input, aqi_input = _extract_from_input(input())

    if type_of_input == None:
        raise ValueError

    if type_of_input == 'purpleair':
        # for PurpleAir's API
        if aqi_input != '':
            raise ValueError
        return sensor.SensorAPI()
    else:
        # for path to file
        if aqi_input == '':
            raise ValueError
        return sensor.SensorFile(aqi_input)

def _ask_for_reverse() -> (str, str):
    '''Returns the type of input and reverse input, after checking
    that the input is valid'''
    
    type_of_input, reverse_input = _extract_from_input(input())

    if type_of_input == None:
        raise ValueError

    if reverse_input * (type_of_input == 'nominatim') != '':
        raise ValueError

    return (type_of_input, reverse_input)

def _get_reverse_geocoding(
    location: geocoding.Location,
    user_input: (str, str)
    ) -> geocoding.ReverseFile or geocoding.ReverseAPI:
    '''Gets a reverse geocoding object from a list of locations
    Either uses Nominatim API or files, depending on user input'''
    type_of_input, file_path_string = user_input

    if type_of_input == 'nominatim':
        # For Nominatim's API
        location_desc = geocoding.ReverseAPI(location)
    else:
        # For path to file
        location_desc = geocoding.ReverseFile(path)

def _get_location_desc(
    reverse_geo_list: list[geocoding.ReverseFile or geocoding.ReverseAPI]
    ) -> list[str]:
    location_desc_list = []
    for reverse_geo in reverse_geo_list:
        description = reverse_geo.get_description()
        location_desc_list.append(description)

    return location_desc_list

def _get_sensor_info(chosen_sensors: list,
                     reverse_input: str) -> list:
    '''Gets the AQI value, location, and location description
    of the chosen sensors'''
    type_of_input, file_path_string = reverse_input
    file_paths = file_path_string.split()
    file_count = 0
    sensor_info = []
    for chosen_sensor in chosen_sensors:
        reverse_obj = None
        location = geocoding.Location(chosen_sensor[27], chosen_sensor[28])
        if type_of_input == 'nominatim':
            # For Nominatim's API
            reverse_obj = geocoding.ReverseAPI(location)
        else:
            # For path to file
            reverse_obj = geocoding.ReverseFile(file_paths[file_count])
            file_count += 1
            
        aqi_val = sensor.calculate_aqi(chosen_sensor[1])
        location_str = location.get_str()
        description = reverse_obj.get_description()
        sensor_info.append([aqi_val, location_str, description])
            
    return sensor_info
    
def _print_output(center_location: geocoding.Location,
                  sensor_info_list: list) -> None:
    '''Prints the AQI value, location, and location description
    of the chosen sensors'''
    print('CENTER', center_location.get_str())
    for sensor_info in sensor_info_list:
        print('AQI', sensor_info[0])
        print(sensor_info[1])
        print(sensor_info[2])
  
def run() -> None:
    'Runs the main user interface of the program'
    # INPUT
    center = None
    try:
        center = _ask_for_center()
    except geocoding.FileError as e:
        print('FAILED')
        print(str(e.path))
        print(e.error)
        return
    except geocoding.APIError as e:
        print('FAILED')
        print(e.status, e.url)
        print(e.error)
        return
    except geocoding.NetworkError as e:
        print('FAILED')
        print(e.url)
        print(e.error)
        return
    range_miles = _ask_for_positive_int()
    threshold = _ask_for_positive_int()
    max_num = _ask_for_positive_int()
    aqi = None
    try:
        aqi = _ask_for_aqi()
    except sensor.FileError as e:
        print('FAILED')
        print(str(e.path))
        print(e.error)
        return
    except sensor.APIError as e:
        print('FAILED')
        print(e.status, e.url)
        print(e.error)
        return
    except sensor.NetworkError as e:
        print('FAILED')
        print(e.url)
        print(e.error)
        return
    reverse_input = _ask_for_reverse()
    
    # PROCESSING DATA
    center_location = center.get_location()
    chosen_sensors = sensor.find_sensors(center_location,
                                              range_miles,
                                              threshold,
                                              max_num,
                                              aqi.get_data())
    sensor_info_list = None
    try:
        sensor_info_list = _get_sensor_info(chosen_sensors,
                                            reverse_input)
    except geocoding.FileError as e:
        print('FAILED')
        print(str(e.path))
        print(e.error)
        return
    except geocoding.APIError as e:
        print('FAILED')
        print(e.status, e.url)
        print(e.error)
        return
    except geocoding.NetworkError as e:
        print('FAILED')
        print(e.url)
        print(e.error)
        return
    
    # OUTPUT
    _print_output(center_location, sensor_info_list)
    

if __name__ == '__main__':
    run()
