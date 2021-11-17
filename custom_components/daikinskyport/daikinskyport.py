''' Python Code for Communication with the Daikin Skyport Thermostat.  This is taken mostly from pyecobee, so much credit to those contributors'''
import requests
import json
import os
import logging
import aiohttp

import async_timeout

from requests.exceptions import RequestException, ConnectionError, Timeout

from .const import DAIKIN_PERCENT_MULTIPLIER

_LOGGER = logging.getLogger('daikinskyport')

NEXT_SCHEDULE = 1

def config_from_file(filename, config=None):
    ''' Small configuration file management function'''
    if config:
        # We're writing configuration
        try:
            with open(filename, 'w') as fdesc:
                fdesc.write(json.dumps(config))
        except IOError as error:
            _LOGGER.exception(error)
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

    def __init__(self, user_email=None, user_password=None):
        self.thermostats = list()
        self.thermostatlist = list()
        self.authenticated = False

    async def get_thermostats(self):
        ''' Set self.thermostats to a json list of thermostats from daikinskyport.com '''
        url = 'https://api.daikinskyport.com/devices'
        header = {'Content-Type': 'application/json;charset=UTF-8',
                  'Authorization': 'Bearer ' + self.access_token}
        try:
            request = requests.get(url, headers=header)
        except RequestException:
            _LOGGER.warn("Error connecting to Daikin Skyport.  Possible connectivity outage.")
            return None
        if request.status_code == requests.codes.ok:
            self.authenticated = True
            self.thermostatlist = request.json()
            for thermostat in self.thermostatlist:
                overwrite = False
                thermostat_info = self.get_thermostat_info(thermostat['id'])
                thermostat_info['name'] = thermostat['name']
                thermostat_info['id'] = thermostat['id']
                for index in range(len(self.thermostats)):
                    if thermostat['id'] == self.thermostats[index]['id']:
                        overwrite = True
                        self.thermostats[index] = thermostat_info
                if not overwrite:
                    self.thermostats.append(thermostat_info)
            return self.thermostats
        else:
            self.authenticated = False
            _LOGGER.debug("Error connecting to Daikin Skyport while attempting to get "
                        "thermostat data.  Refreshing tokens and trying again.")
            if self.refresh_tokens():
                return self.get_thermostats()
            else:
                return None

    async def get_thermostat_info(self, deviceid):
        ''' Retrieve the device info for the specific device '''
        url = 'https://api.daikinskyport.com/deviceData/' + deviceid
        header = {'Content-Type': 'application/json;charset=UTF-8',
                  'Authorization': 'Bearer ' + self.access_token}
        try:
            request = requests.get(url, headers=header)
        except RequestException:
            _LOGGER.warn("Error connecting to Daikin Skyport.  Possible connectivity outage.")
            return None
        if request.status_code == requests.codes.ok:
            self.authenticated = True
            return request.json()
        else:
            self.authenticated = False
            _LOGGER.debug("Error connecting to Daikin Skyport while attempting to get "
                        "thermostat data.  Refreshing tokens and trying again.")
            if self.refresh_tokens():
                return self.get_thermostat_info(deviceid)
            else:
                return None

    async def get_thermostat(self, index):
        ''' Return a single thermostat based on index '''
        return self.thermostats[index]

    async def get_sensors(self, index):
        ''' Return sensors based on index '''
        sensors = list()
        sensors.append({"name": self.thermostats[index]['name'] + " Outdoor", "value": self.thermostats[index]['tempOutdoor'], "type": "temperature"})
        sensors.append({"name": self.thermostats[index]['name'] + " Outdoor", "value": self.thermostats[index]['humOutdoor'], "type": "humidity"})
        sensors.append({"name": self.thermostats[index]['name'] + " Outdoor fan", "value": round(self.thermostats[index]['ctOutdoorFanRequestedDemandPercentage'] / DAIKIN_PERCENT_MULTIPLIER, 1), "type": "demand"})
        sensors.append({"name": self.thermostats[index]['name'] + " Outdoor cooling", "value": round(self.thermostats[index]['ctOutdoorCoolRequestedDemand'] / DAIKIN_PERCENT_MULTIPLIER, 1), "type": "demand"})
        sensors.append({"name": self.thermostats[index]['name'] + " Outdoor", "value": self.thermostats[index]['ctOutdoorPower'], "type": "power"})
        sensors.append({"name": self.thermostats[index]['name'] + " Outdoor", "value": round(self.thermostats[index]['ctOutdoorFrequencyInPercent'] / DAIKIN_PERCENT_MULTIPLIER, 1), "type": "frequency_percent"})
        sensors.append({"name": self.thermostats[index]['name'] + " Indoor", "value": self.thermostats[index]['tempIndoor'], "type": "temperature"})
        sensors.append({"name": self.thermostats[index]['name'] + " Indoor", "value": self.thermostats[index]['humIndoor'], "type": "humidity"})
        sensors.append({"name": self.thermostats[index]['name'] + " Indoor fan", "value": round(self.thermostats[index]['ctIFCFanRequestedDemandPercent'] / DAIKIN_PERCENT_MULTIPLIER, 1), "type": "demand"})
        sensors.append({"name": self.thermostats[index]['name'] + " Indoor fan", "value": round(self.thermostats[index]['ctIFCCurrentFanActualStatus'] / DAIKIN_PERCENT_MULTIPLIER, 1), "type": "actual_status"})
        sensors.append({"name": self.thermostats[index]['name'] + " Indoor cooling", "value": round(self.thermostats[index]['ctIFCCoolRequestedDemandPercent'] / DAIKIN_PERCENT_MULTIPLIER, 1), "type": "demand"})
        sensors.append({"name": self.thermostats[index]['name'] + " Indoor cooling", "value": round(self.thermostats[index]['ctIFCCurrentCoolActualStatus'] / DAIKIN_PERCENT_MULTIPLIER, 1), "type": "actual_status"})
        sensors.append({"name": self.thermostats[index]['name'] + " Indoor heating", "value": round(self.thermostats[index]['ctIFCHeatRequestedDemandPercent'] / DAIKIN_PERCENT_MULTIPLIER, 1), "type": "demand"})
        sensors.append({"name": self.thermostats[index]['name'] + " Indoor heating", "value": round(self.thermostats[index]['ctIFCCurrentHeatActualStatus'] / DAIKIN_PERCENT_MULTIPLIER, 1), "type": "actual_status"})
        sensors.append({"name": self.thermostats[index]['name'] + " Indoor humidifier", "value": round(self.thermostats[index]['ctIFCHumRequestedDemandPercent'] / DAIKIN_PERCENT_MULTIPLIER, 1), "type": "demand"})
        sensors.append({"name": self.thermostats[index]['name'] + " Indoor dehumidifier", "value": round(self.thermostats[index]['ctIFCDehumRequestedDemandPercent'] / DAIKIN_PERCENT_MULTIPLIER, 1), "type": "demand"})
        sensors.append({"name": self.thermostats[index]['name'] + " Indoor", "value": self.thermostats[index]['ctIndoorPower'], "type": "power"})
        if self.thermostats[index]['aqOutdoorAvailable']:
            sensors.append({"name": self.thermostats[index]['name'] + " Outdoor", "value": self.thermostats[index]['aqOutdoorParticles'], "type": "particle"})
            sensors.append({"name": self.thermostats[index]['name'] + " Outdoor", "value": self.thermostats[index]['aqOutdoorValue'], "type": "score"})
            sensors.append({"name": self.thermostats[index]['name'] + " Outdoor", "value": self.thermostats[index]['aqOutdoorOzone'], "type": "ozone"})
        if self.thermostats[index]['aqIndoorAvailable']:
            sensors.append({"name": self.thermostats[index]['name'] + " Indoor", "value": self.thermostats[index]['aqIndoorParticlesValue'], "type": "particle"})
            sensors.append({"name": self.thermostats[index]['name'] + " Indoor", "value": self.thermostats[index]['aqIndoorValue'], "type": "score"})
            sensors.append({"name": self.thermostats[index]['name'] + " Indoor", "value": self.thermostats[index]['aqIndoorVOCValue'], "type": "VOC"})
            
        return sensors

    async def update(self):
        ''' Get new thermostat data from daikin skyport '''
        self.get_thermostats()

    async def make_request(self, index, body, log_msg_action, *, retry_count=0):
        deviceID = self.thermostats[index]['id']
        url = 'https://api.daikinskyport.com/deviceData/' + deviceID
        header = {'Content-Type': 'application/json;charset=UTF-8',
                  'Authorization': 'Bearer ' + self.access_token}
        _LOGGER.debug("Make Request: Device: %s, Body: %s", deviceID, body)
        try:
            request = requests.put(url, headers=header, json=body)
        except RequestException:
            _LOGGER.warn("Error connecting to Daikin Skyport.  Possible connectivity outage.")
            return None
        if request.status_code == requests.codes.ok:
            return request
        elif (request.status_code == 401 and retry_count == 0 and
              request.json()['error'] == 'authorization_expired'):
            if self.refresh_tokens():
                return self.make_request(body, deviceID, log_msg_action,
                                         retry_count=retry_count + 1)
        else:
            _LOGGER.warn(
                "Error fetching data from Daikin Skyport while attempting to %s: %s",
                log_msg_action, request.json())
            return None

    async def set_hvac_mode(self, index, hvac_mode):
        ''' possible hvac modes are auto (3), auxHeatOnly (4), cool (2), heat (1), off (0) '''
        body = {"mode": hvac_mode}
        log_msg_action = "set HVAC mode"
        return self.make_request(index, body, log_msg_action)

    async def set_thermostat_schedule(self, index, prefix, start, enable, label, heating, cooling):
        ''' Schedule to set the thermostat.
        prefix is the beginning of the JSON key to modify.  It consists of "sched" + [Mon,Tue,Wed,Thu,Fri,Sat,Sun] + "Part" + [1:6] (ex. schedMonPart1)
        start is the beginning of the schedule.  It is an integer value where every 15 minutes from 00:00 is 1 (each hour = 4)
        enable is a boolean to set whether the schedule part is active or not
        label is a name for the part (ex. wakeup, work, etc.)
        heating is the heating set point for the part
        cooling is the cooling set point for the part'''
        body = {prefix + "Time": start,
                prefix + "Enabled": enable,
                prefix + "Label": label,
                prefix + "hsp": heating,
                prefix + "csp": cooling
                }

        log_msg_action = "set thermostat schedule"
        return self.make_request(index, body, log_msg_action)

    async def set_fan_mode(self, index, fan_mode):
        ''' Set fan mode. Values: auto (0), schedule (2), on (1) '''
        body = {"fanCirculate": fan_mode}
        log_msg_action = "set fan mode"
        return self.make_request(index, body, log_msg_action)

    async def set_fan_speed(self, index, fan_speed):
        ''' Set fan speed. Values: low (0), medium (1), high (2) '''
        body = {"fanCirculateSpeed": fan_speed}
        log_msg_action = "set fan speed"
        return self.make_request(index, body, log_msg_action)

    async def set_fan_clean(self, index, active):
        ''' Enable/disable fan clean mode.  This runs the fan at high speed to clear out the air.
        active values are true/false'''
        body = {"oneCleanFanActive": active}
        log_msg_action = "set fan clean mode"
        return self.make_request(index, body, log_msg_action)

    async def set_temp_hold(self, index, cool_temp=None, heat_temp=None,
                      hold_duration=None):
        ''' Set a temporary hold '''
        if hold_duration is None:
            hold_duration = self.thermostats[index]["schedOverrideDuration"]
        if cool_temp is None:
            cool_temp = self.thermostats[index]["cspHome"]
        if heat_temp is None:
            heat_temp = self.thermostats[index]["hspHome"]
        body = {"hspHome": round(heat_temp, 1),
                "cspHome": round(cool_temp, 1),
                "schedOverride": 1,
                "schedOverrideDuration": hold_duration
                }
        log_msg_action = "set hold temp"
        return self.make_request(index, body, log_msg_action)

    async def set_permanent_hold(self, index, cool_temp=None, heat_temp=None):
        ''' Set a climate hold - ie enable/disable schedule. 
        active values are true/false
        hold_duration is NEXT_SCHEDULE'''
        if cool_temp is None:
            cool_temp = self.thermostats[index]["cspHome"]
        if heat_temp is None:
            heat_temp = self.thermostats[index]["hspHome"]
        body = {"hspHome": round(heat_temp, 1),
                "cspHome": round(cool_temp, 1),
                "schedOverride": 0,
                "schedEnabled": False
                }
        log_msg_action = "set permanent hold"
        return self.make_request(index, body, log_msg_action)

    async def set_away(self, index, mode, heat_temp=None, cool_temp=None):
        ''' Enable/Disable the away setting and optionally set the away temps '''
        if heat_temp is None:
            heat_temp = round(self.thermostats[index]["hspAway"], 1)
        if cool_temp is None:
            cool_temp = round(self.thermostats[index]["cspAway"], 1)
        body = {"geofencingAway": mode,
                "hspAway": heat_temp,
                "cspAway": cool_temp
                }

        log_msg_action = "set away mode"
        return self.make_request(index, body, log_msg_action)

    async def resume_program(self, index):
        ''' Resume currently scheduled program '''
        body = {"schedEnabled": True,
                "schedOverride": 0,
                "geofencingAway": False
                }

        log_msg_action = "resume program"
        return self.make_request(index, body, log_msg_action)

    async def set_fan_schedule(self, index, start, stop, interval, speed):
        ''' Schedule to run the fan.  
        start_time is the beginning of the schedule per day.  It is an integer value where every 15 minutes from 00:00 is 1 (each hour = 4)
        end_time is the end of the schedule each day.  Values are same as start_time
        interval is the run time per hour of the schedule. Options are on the full time (0), 5mins (1), 15mins (2), 30mins (3), and 45mins (4) 
        speed is low (0) medium (1) or high (2)'''
        body = {"fanCirculateStart": start,
                "fanCirculateStop": stop,
                "fanCirculateDuration": interval,
                "fanCirculateSpeed": speed
                }

        log_msg_action = "set fan schedule"
        return self.make_request(index, body, log_msg_action)

    async def set_night_mode(self, index, start, stop, enable):
        ''' Set the night mode parameters '''
        body = {"nightModeStart": start,
                "nightModeStop": stop,
                "nightModeEnabled": enable,
                }

        log_msg_action = "set night mode"
        return self.make_request(index, body, log_msg_action)

    async def set_humidity(self, index, humidity_low=None, humidity_high=None):
        ''' Set humidity level'''
        if humidity_low is None:
            humidity_low = self.thermostats[index]["humSP"]
        if humidity_high is None:
            humidity_high = self.thermostats[index]["dehumSP"]
        body = {"dehumSP": humidity_high,
                "humSP": humidity_low
                }

        log_msg_action = "set humidity level"
        return self.make_request(index, body, log_msg_action)

async def request_tokens(user_email, user_password, retry=3, timeout=10):
    ''' Method to request API tokens from skyport '''
    url = 'https://api.daikinskyport.com/users/auth/login'
    header = {'Accept': 'application/json',
                'Content-Type': 'application/json'}
    data = {"email": user_email, "password": user_password}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=header, json=data, timeout=timeout) as r:
                request = await r.json()
                status = r.status
    except ConnectionError:
        if retry > 0:
            return await request_tokens(user_email, user_password, retry=retry - 1, timeout=timeout)
        _LOGGER.error("Error connecting to Daikin Skyport.  Possible connectivity outage."
                    "Could not request token.")
        raise
    except Timeout:
        if retry > 0:
            return await request_tokens(user_email, user_password, retry=retry - 1, timeout=timeout)
        _LOGGER.error("Timed out when connecting to Daikin Skyport for a token.")
        raise
    if status != requests.codes.ok:
        _LOGGER.error("Failed to log in to Daikin Skyport to retrieve token.")
        return None
    
    auth = {
        'access': request['accessToken'],
        'refresh': request['refreshToken'],
    }
    if auth['refresh'] is None:
        _LOGGER.error("Auth did not return a refresh token.")
        return None
    return auth 

async def refresh_tokens(user_email, refresh_token, retry=3, timeout=10):
    ''' Method to refresh API tokens from daikinskyport.com '''
    url = 'https://api.daikinskyport.com/users/auth/token'
    header = {'Accept': 'application/json',
                'Content-Type': 'application/json'}
    data = {'email': user_email,
            'refreshToken': refresh_token}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=header, json=data, timeout=timeout) as r:
                request = await r.json()
                status = r.status
    except ConnectionError:
        if retry > 0:
            return await refresh_tokens(user_email, refresh_token, retry=retry - 1, timeout=timeout)
        _LOGGER.error("Error connecting to Daikin Skyport.  Possible connectivity outage."
                    "Could not request token.")
        return None
    except Timeout:
        if retry > 0:
            return await refresh_tokens(user_email, refresh_token, retry=retry - 1, timeout=timeout)
        _LOGGER.error("Timed out when connecting to Daikin Skyport for a token.")
        return None
    if status != requests.codes.ok:
        _LOGGER.error("Failed to log in to Daikin Skyport to retrieve token.")
        return None
    auth = {
        'access': request['accessToken'],
        'refresh': request['refreshToken'],
    }
    if auth['refresh'] is None:
        _LOGGER.error("Auth did not return a refresh token.")
        return None
    return auth 