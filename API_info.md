The first step to interfacing with a Daikin Skyport thermostat is to login:
```
curl --location --request POST "https://api.daikinskyport.com/users/auth/login" \
--header "Accept: application/json" \
--header "Content-Type: application/json" \
--data '{"email": "<email>", "password": "<password>"}'
```

This uses the email and password registered with the DaikinOne+ Home app to connect and returns access and refresh tokens:
```
{"accessToken":"<token>","accessTokenExpiresIn":3600,"refreshToken":"<token>","tokenType":"Bearer"}
```

You can now verify your access token by running:
```
curl --location --request GET "https://api.daikinskyport.com/users/me" \
--header "Accept: application/json" \
--header "Authorization: Bearer <access token>"
```

Which returns:
```
{"id":"<some UUID-type string>","name":"<first> #<last>","email":"<email>"}
```

To refresh a token:
```
curl --location --request POST "https://api.daikinskyport.com/users/auth/token" \
--header "Accept: application/json" \
--header "Content-Type: application/json" \
--data '{"email": "<email>", "refreshToken": "<refresh token>"}'
```

Once you have an access token, you can connect and retrieve what locations are available to the account:
```
curl --location --request GET "https://api.daikinskyport.com/locations" \
--header "Accept: application/json" \
--header "Authorization: Bearer <access token>"
```

which returns:
```
[{"id":"<UUID of location>","name":"<Location Name>","address":"<street address>","city":"<city>",
"province":"<state/province>","postalCode":"<zip code>",
"country":"<country>","timeZone":"America/New_York","latitude":<lat>,"longitude":<long>,"hasOwner":true}]
```

And retrieve the devices:
```
curl --location --request GET "https://api.daikinskyport.com/devices" \
--header "Accept: application/json" \
--header "Authorization: Bearer <access token>"
```

Which returns:
```
[{"id":"<UUID of the device>","locationId":"<UUID of location>","name":"<name of device>",
"model":"ONEPLUS","firmwareVersion":"1.4.5","createdDate":1563568617,"hasOwner":true,"hasWrite":true}]
```

Once you know the device ID, you can use it to probe the device:
```
curl --location --request GET "https://api.daikinskyport.com/deviceData/<UUID of device>" \
--header "Accept: application/json" \
--header "Authorization: Bearer <access token>"
```

Which returns (truncated):
```
{"sysFault7Date":0,
"quietModeActive":1,
"alertDehumFilterRuntime":0,
"runtimeDay7Date":0,
"modeForceOff":false,
"schedWedPart1Label":"wake",
"schedSatPart6csp":27,
"fault4Date":0,
"schedWedPart2Action":0,
"oneCleanFanSpeed":1,
"schedTuePart4Label":"sleep",
"schedMonPart2csp":25.6,
"ctAHHumidificationFanSpeedPercent":255,
"ctHumidifierControl":2,
"ctIFCHumRequestedDemandPercent":255,
"schedSunPart3Label":"home",
"ctOutdoorCapacityPriority":255,
"messageHistory9Text":"",
"modeEmHeatAvailable":true,
"schedMonPart6Action":0,
"ctOutdoorSuctionTemperature":660,
"ctOutdoorHeatMaxRPS":585,
"schedMonPart3Action":0,
"schedSunPart3hsp":20,
"schedTuePart3Enabled":true,
"hspHome":17.2,
...
"ctOutdoorHeatRequestedDemand":0,
"alertDehumFilterRuntimeLimit":0,
"fault24Level":255,
"messageHistory7Type":0,
"equipmentCapability":0,
"statType":"production"}
```

There are almost 900 elements when I probe my thermostat.  Some abbreviations used when looking at the data:
```
ct = cooling temperature
ht = heating temperature
sp = set point
csp = cooling set point
hsp = heating set point
sched = schedule
hum = humidity/humidifier
```

How times work:
They decided to be weird with how times work. Basically every 1=15mins. So midnight (00:00) is 0, 00:15=1, 08:00=8x4=32, etc.

To set configuration:
```
curl --location --request PUT "https://api.daikinskyport.com/deviceData/<device UUID>" \
--header "Accept: application/json" \
--header "Content-Type: application/json" \
--data '{"geofencingAway": "False", "schedEnabled": "False","schedOverride":0,"cspHome":24.4}'
```

Set a temperature hold:
```
"geofencingAway": Set whether geofencing is in away mode, true/false
"schedEnabled": Set if thermostat goes off schedule or manual set point, true=schedule, false=set point
"schedOverride": integer, unknown (TBD)
"cspHome": cooling set point, temperature in C, one decimal place
"hspHome": heating set point, temperature in C, one decimal place
```

Set the operating mode:
```
“mode”: 2 is cool, 3 is auto, 1 is heat, 0 is off, emergency heat is 4
```

Set screen brightness:
```
“displayBrightness”: 0-100, percentage
```

Night mode:
```
“nightModeEnabled”: Enable night mode, True/False
“nightModeLightBarAllowed”: true/false
“nightModeStart”: (see times)
“nightModeStop”: (see times)
```

Sensors:
```
“tempIndoor”: current indoor temperature, in C
“tempOutdoor”: current outdoor temperature, in C
“humIndoor”: current indoor humidity, in %
“humOutdoor”: current outdoor humidity, in %
"cspActive": current cooling set point, in C
"hspActive": current heating set point, in C
"cspSched": current cooling set point for the schedule, in C
"hspSched": current heating set point for the schedule, in C
"fanCirculateActive": current status of fan circulation, true/false
"oneCleanFanActive": current status of One Clean Fan, true/false
“nightModeActive”: current status of night mode, True/False
“weatherTodayTempC”: forecast of the temps for today
“weatherTodayIcon”: tstorms, partlycloudy, (these are all I have right now)
“weatherTodayCond”: text description of conditions
“weatherTodayHum”: humidity forecast
“weatherDay[n]TempC”: forecast of the temps for days 1-5 (ex. weatherDay1TempC)
“weatherDay[n]Icon”: tstorms, partlycloudy, (these are all I have right now)
“weatherDay[n]Cond”: text description of conditions
“weatherDay[n]Hum”: humidity forecast
“ctAHFanCurrentDemandStatus”: looks like a %, current fan demand
“ctAHFanRequestedDemand”: looks like a %, the requested fan demand by thermostat
“ctAHCurrentIndoorAirflow”: maybe CFM?, current airflow
```
[n]: Forecast day 1 through 5

There are plenty of other sensors, but those are probably the most relevant to most people.

Fan:
```
“fanCirculate”: 0=off, 1=always on, 2=schedule, manual fan control
“fanCirculateDuration”: 0=entire schedule, 1=5mins, 2=15mins, 3=30mins, 4=45mins runs the fan for this amount of time every hour in schedule
```

OneClean (Air Quality) settings:
```
“oneCleanFanActive”: true/false runs the fan at high speed for 3 hours
"oneCleanFanSpeed": fan clean fan speed, integer, unknown (TBD)
"oneCleanFanDuration": duration of fan clean, integer, hours
"oneCleanParticleTrigger": particulate sensor threshold to run air cleaning, integer
```

Schedule:
```
"sched[DoW]Part[n]Label": text label
"sched[DoW]Part[n]Action": integer, currently unknown (TBD)
"sched[DoW]Part[n]Time": integer time (see time note)
"sched[DoW]Part[n]csp": cooling set point, temperature in C, one decimal place
"sched[DoW]Part[n]Enabled": enable or disable the schedule block, true/false
"sched[DoW]Part[n]hsp": heating set point, temperature in C, one decimal place
"schedOverrideDuration": how long the manual set point should last, time? (TBD)
"schedEnabled": set if the schedule is enabled or manual set point, true/false
```
[DoW]: Day of week - Mon, Tue, Wed, Thu, Fri, Sat, Sun
[n]: Sequential number from 1 to 4 used to associate the parameters to the schedule block

Humidity Settings:
```
"humSP": humidity set point, percent
"dehumSP": dehumidification set point, percent
```

Away Settings:
```
"hspAway": heat set point while away, temperature in C, one decimal place
"cspAway": cooling set point while away, temperature in C, one decimal place
"geofencingEnabled": set if geofencing is enabled for away settings, true/false

Determining unit capabilities:
"ctOutdoorNoofCoolStages": number of cooling stages, integer
"ctOutdoorNoofHeatStages": number of heating stages, integer
"ctSystemCapEmergencyHeat": true if heating element is installed


