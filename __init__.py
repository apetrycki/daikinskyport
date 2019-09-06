''' Python Code for Communication with the Daikin Skyport Thermostat.  This is taken mostly from pyecobee, so much credit to those contributors'''
import requests
import json
import os
import logging

from requests.exceptions import RequestException

logger = logging.getLogger('daikinskyport')

NEXT_SCHEDULE = 1

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
                if (user_email is None) or (user_password is None):
                    logger.error("Error. No user email or password was supplied.")
                    return
                jsonconfig = {"EMAIL": user_email, "PASSWORD": user_password}
                config_filename = 'daikinskyport.conf'
                config_from_file(config_filename, jsonconfig)
            config = config_from_file(config_filename)
        else:
            self.file_based_config = False
        self.user_email = config['EMAIL']
        self.user_password = config['PASSWORD']
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
                self.thermostats.append(get_thermostat_info(thermostat['id']))
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
        ''' Retrieve the device info for the specific device '''
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

    """
    def get_remote_sensors(self, index):
        ''' Return remote sensors based on index '''
        return self.thermostats[index]['remoteSensors']
    """

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

    def make_request(self, deviceID, body, log_msg_action, *, retry_count=0):
        url = 'https://api.daikinskyport.com/deviceData/' + deviceID
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
                return self.make_request(body, deviceID, log_msg_action,
                                         retry_count=retry_count + 1)
        else:
            logger.info(
                "Error fetching data from Daikin Skyport while attempting to %s: %s",
                log_msg_action, request.json())
            return None

    def set_hvac_mode(self, deviceID, hvac_mode):
        ''' possible hvac modes are auto (3), auxHeatOnly (4), cool (2), heat (1), off (0) '''
        body = {"mode": hvac_mode}
        log_msg_action = "set HVAC mode"
        return self.make_request(deviceID, body, log_msg_action)

    def set_fan_schedule(self, deviceID, start_time, end_time, duration):
        ''' Schedule to run the fan.  
        start_time is the beginning of the schedule per day.  It is an integer value where every 15 minutes from 00:00 is 1 (each hour = 4)
        end_time is the end of the schedule each day.  Values are same as start_time
        duration is the run time per hour of the schedule. Options are on the full time (0), 5mins (1), 15mins (2), 30mins (3), and 45mins (4) '''
        body = {"fanCirculateDuration": duration,
                "fanCirculateStart": start_time,
                "fanCirculateStop": end_time
                }
        log_msg_action = "set fan minimum on time."
        return self.make_request(deviceID, body, log_msg_action)

    def set_fan_mode(self, deviceID, fan_mode):
        ''' Set fan mode. Values: auto (0), schedule (2), on (1) '''
        body = {"fanCirculate": fan_mode}
        log_msg_action = "set fan mode"
        return self.make_request(deviceID, body, log_msg_action)

    def set_fan_clean(self, deviceID, active):
        ''' Enable/disable fan clean mode.  This runs the fan at high speed to clear out the air.
        active values are true/false'''
        body = {"oneCleanFanActive": active}
        log_msg_action = "set fan clean mode"
        return self.make_request(deviceID, body, log_msg_action)

    def set_hold_temp(self, deviceID, cool_temp, heat_temp,
                      hold_type=NEXT_SCHEDULE):
        ''' Set a hold '''
        body = {"hspHome": heat_temp,
                "cspHome": cool_temp,
                "schedOverride": hold_type  # Need to verify this one
                }
        log_msg_action = "set hold temp"
        return self.make_request(deviceID, body, log_msg_action)

    def set_climate_hold(self, deviceID, active, hold_type=NEXT_SCHEDULE):
        ''' Set a climate hold - ie enable/disable schedule. 
        active values are true/false
        hold_type is NEXT_SCHEDULE or PERMANENT_HOLD'''
        body = {"schedEnabled": active,
                "schedOverride": hold_type
                }
        log_msg_action = "set climate hold"
        return self.make_request(deviceID, body, log_msg_action)

    ''' TBD '''
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

    def resume_program(self, deviceID, resume_sched=False):
        ''' Resume currently scheduled program '''
        body = {"schedEnabled": resume_sched}

        log_msg_action = "resume program"
        return self.make_request(deviceID, body, log_msg_action)

    ''' TBD if this is supported '''
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

    def set_humidity(self, deviceID, humidity):
        ''' Set humidity level'''
        body = {"dehumSP": humidity}

        log_msg_action = "set humidity level"
        return self.make_request(deviceID, body, log_msg_action)
