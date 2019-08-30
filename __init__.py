''' Python Code for Communication with the Daikin Skyport Thermostat.  This is taken mostly from pyecobee, so much credit to those contributors'''
import requests
import json
import os
import logging

from requests.exceptions import RequestException;

logger = logging.getLogger('daikinskyport')


def config_from_file(filename, config=None):
    ''' Small configuration file management function'''
    if config:
        # We're writing configuration
        try:
            with open(filename, 'w') as fdesc:
                fdesc.write(json.dumps(config))
        except IOError as error:
            logger.exception(error)
            return False
        return True
    else:
        # We're reading config
        if os.path.isfile(filename):
            try:
                with open(filename, 'r') as fdesc:
                    return json.loads(fdesc.read())
            except IOError as error:
                return False
        else:
            return {}


class DaikinSkyport(object):
    ''' Class for storing Daikin Skyport Thermostats and Sensors '''

    def __init__(self, config_filename=None, user_email=None, user_password=None, config=None):
        self.thermostats = list()
        self.thermostatlist = list()
        self.authenticated = False

        if config is None:
            self.file_based_config = True
            if config_filename is None:
                if user_email is None || user_password is None:
                    logger.error("Error. No user email or password was supplied.")
                    return
                jsonconfig = {"USER_EMAIL": user_email, "USER_PASSWORD": user_password}
                config_filename = 'daikinskyport.conf'
                config_from_file(config_filename, jsonconfig)
            config = config_from_file(config_filename)
        else:
            self.file_based_config = False
        self.user_email = config['USER_EMAIL']
        self.user_password = config['USER_PASSWORD']
        self.config_filename = config_filename

        if 'ACCESS_TOKEN' in config:
            self.access_token = config['ACCESS_TOKEN']
        else:
            self.access_token = ''

        if 'REFRESH_TOKEN' in config:
            self.refresh_token = config['REFRESH_TOKEN']
        else:
            self.refresh_token = ''
            self.request_tokens()
            return

        self.update()

    def request_tokens(self):
        ''' Method to request API tokens from skyport '''
        url = 'https://api.daikinskyport.com/users/auth/login'
        params = {'email': self.user_email, 'password': self.user_password}
        try:
            request = requests.post(url, params=params)
        except RequestException:
            logger.warn("Error connecting to Daikin Skyport.  Possible connectivity outage."
                        "Could not request token.")
            return
        if request.status_code == requests.codes.ok:
            self.access_token = request.json()['accessToken']
            self.refresh_token = request.json()['refreshToken']
            self.write_tokens_to_file()
        else:
            logger.warn('Error while requesting tokens from daikinskyport.com.'
                  ' Status code: ' + str(request.status_code))
            return

    def refresh_tokens(self):
        ''' Method to refresh API tokens from daikinskyport.com '''
        url = 'https://api.daikinskyport.com/users/auth/token'
        params = {'email': self.user_email,
                  'refreshToken': self.refresh_token}
        request = requests.post(url, params=params)
        if request.status_code == requests.codes.ok:
            self.access_token = request.json()['accessToken']
            self.refresh_token = request.json()['refreshToken']
            self.write_tokens_to_file()
            return True
        else:
            self.request_tokens()

    def get_thermostats(self):
        ''' Set self.thermostats to a json list of thermostats from daikinskyport.com '''
        url = 'https://api.daikinskyport.com/devices'
        header = {'Content-Type': 'application/json;charset=UTF-8',
                  'Authorization': 'Bearer ' + self.access_token}
        params = {}
        try:
            request = requests.get(url, headers=header, params=params)
        except RequestException:
            logger.warn("Error connecting to Daikin Skyport.  Possible connectivity outage.")
            return None
        if request.status_code == requests.codes.ok:
            self.authenticated = True
            self.thermostatlist = request.json()
            for thermostat in self.thermostatlist:
            self.thermostats[thermostat['name']]=get_thermostat_info(deviceid=thermostat['id'])
            return self.thermostats
        else:
            self.authenticated = False
            logger.info("Error connecting to Daikin Skyport while attempting to get "
                  "thermostat data.  Refreshing tokens and trying again.")
            if self.refresh_tokens():
                return self.get_thermostats()
            else:
                return None

    def get_thermostat_info(self, deviceid):
        ''' Set self.thermostats to a json list of thermostats from daikinskyport.com '''
        url = 'https://api.daikinskyport.com/deviceData/' + deviceid
        header = {'Content-Type': 'application/json;charset=UTF-8',
                  'Authorization': 'Bearer ' + self.access_token}
        params = {}
        try:
            request = requests.get(url, headers=header, params=params)
        except RequestException:
            logger.warn("Error connecting to Daikin Skyport.  Possible connectivity outage.")
            return None
        if request.status_code == requests.codes.ok:
            self.authenticated = True
            return request.json()
        else:
            self.authenticated = False
            logger.info("Error connecting to Daikin Skyport while attempting to get "
                  "thermostat data.  Refreshing tokens and trying again.")
            if self.refresh_tokens():
                return self.get_thermostat_info()
            else:
                return None

    def get_thermostat(self, index):
        ''' Return a single thermostat based on index '''
        return self.thermostats[index]

'''    def get_remote_sensors(self, index):'''
        ''' Return remote sensors based on index '''
'''        return self.thermostats[index]['remoteSensors']'''

    def write_tokens_to_file(self):
        ''' Write api tokens to a file '''
        config = dict()
        config['ACCESS_TOKEN'] = self.access_token
        config['REFRESH_TOKEN'] = self.refresh_token
        if self.file_based_config:
            config_from_file(self.config_filename, config)
        else:
            self.config = config

    def update(self):
        ''' Get new thermostat data from daikin skyport '''
        self.get_thermostats()

    def make_request(self, body, log_msg_action, *, retry_count=0):
        url = 'https://api.daikinskyport.com/deviceData/' + self.thermostat.id
        header = {'Content-Type': 'application/json;charset=UTF-8',
                  'Authorization': 'Bearer ' + self.access_token}
        params = {}
        try:
            request = requests.post(url, headers=header, params=params, json=body)
        except RequestException:
            logger.warn("Error connecting to Daikin Skyport.  Possible connectivity outage.")
            return None
        if request.status_code == requests.codes.ok:
            return request
        elif (request.status_code == 401 and retry_count == 0 and
              request.json()['error'] == 'authorization_expired'):
            if self.refresh_tokens():
                return self.make_request(body, log_msg_action,
                                         retry_count=retry_count + 1)
        else:
            logger.info(
                "Error fetching data from Ecobee while attempting to %s: %s",
                log_msg_action, request.json())
            return None

    def set_hvac_mode(self, index, hvac_mode):
        ''' possible hvac modes are auto, auxHeatOnly, cool, heat, off '''
        body = {"selection": {"selectionType": "thermostats",
                              "selectionMatch": self.thermostats[index]['identifier']},
                              "thermostat": {
                                  "settings": {
                                      "hvacMode": hvac_mode
                                  }
                              }}
        log_msg_action = "set HVAC mode"
        return self.make_request(body, log_msg_action)

    def set_fan_min_on_time(self, index, fan_min_on_time):
        ''' The minimum time, in minutes, to run the fan each hour. Value from 1 to 60 '''
        body = {"selection": {"selectionType": "thermostats",
                        "selectionMatch": self.thermostats[index]['identifier']},
                        "thermostat": {
                            "settings": {
                                "fanMinOnTime": fan_min_on_time
                            }
                        }}
        log_msg_action = "set fan minimum on time."
        return self.make_request(body, log_msg_action)

    def set_fan_mode(self, index, fan_mode, cool_temp, heat_temp, hold_type="nextTransition"):
        ''' Set fan mode. Values: auto, minontime, on '''
        body = {"selection": {
                    "selectionType": "thermostats",
                    "selectionMatch": self.thermostats[index]['identifier']},
                "functions": [{"type": "setHold", "params": {
                    "holdType": hold_type,
                    "coolHoldTemp": int(cool_temp * 10),
                    "heatHoldTemp": int(heat_temp * 10),
                    "fan": fan_mode
                }}]}
        log_msg_action = "set fan mode"
        return self.make_request(body, log_msg_action)

    def set_hold_temp(self, index, cool_temp, heat_temp,
                      hold_type="nextTransition"):
        ''' Set a hold '''
        body = {"selection": {
                    "selectionType": "thermostats",
                    "selectionMatch": self.thermostats[index]['identifier']},
                "functions": [{"type": "setHold", "params": {
                    "holdType": hold_type,
                    "coolHoldTemp": int(cool_temp * 10),
                    "heatHoldTemp": int(heat_temp * 10)
                }}]}
        log_msg_action = "set hold temp"
        return self.make_request(body, log_msg_action)

    def set_climate_hold(self, index, climate, hold_type="nextTransition"):
        ''' Set a climate hold - ie away, home, sleep '''
        body = {"selection": {
                    "selectionType": "thermostats",
                    "selectionMatch": self.thermostats[index]['identifier']},
                "functions": [{"type": "setHold", "params": {
                    "holdType": hold_type,
                    "holdClimateRef": climate
                }}]}
        log_msg_action = "set climate hold"
        return self.make_request(body, log_msg_action)

    def delete_vacation(self, index, vacation):
        ''' Delete the vacation with name vacation '''
        body = {"selection": {
                    "selectionType": "thermostats",
                    "selectionMatch": self.thermostats[index]['identifier']},
                "functions": [{"type": "deleteVacation", "params": {
                    "name": vacation
                }}]}

        log_msg_action = "delete a vacation"
        return self.make_request(body, log_msg_action)

    def resume_program(self, index, resume_all=False):
        ''' Resume currently scheduled program '''
        body = {"selection": {
                    "selectionType": "thermostats",
                    "selectionMatch": self.thermostats[index]['identifier']},
                "functions": [{"type": "resumeProgram", "params": {
                    "resumeAll": resume_all
                }}]}

        log_msg_action = "resume program"
        return self.make_request(body, log_msg_action)

    def send_message(self, index, message="Hello from python-ecobee!"):
        ''' Send a message to the thermostat '''
        body = {"selection": {
                    "selectionType": "thermostats",
                    "selectionMatch": self.thermostats[index]['identifier']},
                "functions": [{"type": "sendMessage", "params": {
                    "text": message[0:500]
                }}]}

        log_msg_action = "send message"
        return self.make_request(body, log_msg_action)

    def set_humidity(self, index, humidity):
        ''' Set humidity level'''
        body = {"selection": {"selectionType": "thermostats",
                              "selectionMatch": self.thermostats[index]['identifier']},
                              "thermostat": {
                                  "settings": {
                                      "humidity": int(humidity)
                                  }
                              }}

        log_msg_action = "set humidity level"
        return self.make_request(body, log_msg_action)

    def set_mic_mode(self, index, mic_enabled):
        '''Enable/disable Alexa mic (only for Ecobee 4)
        Values: True, False
        '''

        body = {
            'selection': {
                'selectionType': 'thermostats',
                'selectionMatch': self.thermostats[index]['identifier']},
            'thermostat': {
                'audio': {
                    'microphoneEnabled': mic_enabled}}}

        log_msg_action = 'set mic mode'
        return self.make_request(body, log_msg_action)

    def set_occupancy_modes(self, index, auto_away=None, follow_me=None):
        '''Enable/disable Smart Home/Away and Follow Me modes
        Values: True, False
        '''

        body = {
            'selection': {
                'selectionType': 'thermostats',
                'selectionMatch': self.thermostats[index]['identifier']},
            'thermostat': {
                'settings': {
                    'autoAway': auto_away,
                    'followMeComfort': follow_me}}}

        log_msg_action = 'set occupancy modes'
        return self.make_request(body, log_msg_action)

    def set_dst_mode(self, index, dst):
        '''Enable/disable daylight savings
        Values: True, False
        '''

        body = {
            'selection': {
                'selectionType': 'thermostats',
                'selectionMatch': self.thermostats[index]['identifier']},
            'thermostat': {
                'location': {
                    'isDaylightSaving': dst}}}

        log_msg_action = 'set dst mode'
        return self.make_request(body, log_msg_action)
