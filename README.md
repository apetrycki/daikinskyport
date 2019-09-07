# daikinskyport
API and Home Assistant component for accessing a DaikinOne+ Thermostat

This is currently a work in progress but most useful functions are supported.  Now welcoming feedback for features and bugs.  This was mostly taken from the ecobee code and modified.

To use, copy the ```__init__.py``` from the root to site-packages/daikinskyport/ and the daikinskyport folder to your components (custom_components did not work for me, I think due to the import not finding it there) folder.

Add this to your configuration.yaml:
```
daikinskyport:
  email: <your email>
  password: <your password>
```

Right now I have only implemented the climate entity, but will include sensors and weather in the future.
