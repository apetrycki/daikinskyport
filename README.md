# daikinskyport
API and Home Assistant component for accessing a DaikinOne+ Thermostat

This is currently a work in progress but most functions are supported.  Now welcoming feedback for features and bugs.  This was mostly taken from the ecobee code and modified.

To use, clone into `<config directory>/custom_components/daikinskyport`.

Add this to your configuration.yaml:
```
daikinskyport:
  email: <your email>
  password: <your password>
```

TBD:  
Fix services - not sure what I'm doing wrong, it looks to me the same as the ecobee  
Get rid of time on weather forecast  
Would like to understand more of the parameters in the API and get them documented  
