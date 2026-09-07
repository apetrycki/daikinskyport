"""Tests for Daikin Skyport air-quality sensor units."""

import asyncio
import importlib.util
import sys
from enum import StrEnum
from pathlib import Path
from types import ModuleType

import pytest


SENSOR_PATH = (
    Path(__file__).parents[1] / "custom_components" / "daikinskyport" / "sensor.py"
)


def _module(name: str, **attributes: object) -> ModuleType:
    module = ModuleType(name)
    for attribute, value in attributes.items():
        setattr(module, attribute, value)
    return module


@pytest.fixture
def sensor_module(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Load the sensor platform with the Home Assistant API surface it uses."""

    class UnitOfDensity(StrEnum):
        MICROGRAMS_PER_CUBIC_METER = "μg/m³"

    class UnitOfPower(StrEnum):
        WATT = "W"

    class UnitOfRatio(StrEnum):
        PARTS_PER_MILLION = "ppm"
        PARTS_PER_BILLION = "ppb"

    class UnitOfTemperature(StrEnum):
        CELSIUS = "°C"

    class UnitOfVolumeFlowRate(StrEnum):
        CUBIC_FEET_PER_MINUTE = "ft³/min"

    class SensorDeviceClass:
        AQI = "aqi"
        CO2 = "carbon_dioxide"
        HUMIDITY = "humidity"
        OZONE = "ozone"
        PM1 = "pm1"
        PM10 = "pm10"
        PM25 = "pm25"
        POWER = "power"
        TEMPERATURE = "temperature"
        VOLATILE_ORGANIC_COMPOUNDS = "volatile_organic_compounds"

    class SensorEntity:
        pass

    class SensorEntityDescription:
        pass

    class SensorStateClass:
        MEASUREMENT = "measurement"

    class Placeholder:
        pass

    modules = {
        "homeassistant": _module("homeassistant"),
        "homeassistant.components": _module("homeassistant.components"),
        "homeassistant.components.sensor": _module(
            "homeassistant.components.sensor",
            SensorDeviceClass=SensorDeviceClass,
            SensorEntity=SensorEntity,
            SensorEntityDescription=SensorEntityDescription,
            SensorStateClass=SensorStateClass,
        ),
        "homeassistant.config_entries": _module(
            "homeassistant.config_entries", ConfigEntry=Placeholder
        ),
        "homeassistant.const": _module(
            "homeassistant.const",
            PERCENTAGE="%",
            UnitOfDensity=UnitOfDensity,
            UnitOfPower=UnitOfPower,
            UnitOfRatio=UnitOfRatio,
            UnitOfTemperature=UnitOfTemperature,
            UnitOfVolumeFlowRate=UnitOfVolumeFlowRate,
        ),
        "homeassistant.core": _module(
            "homeassistant.core", HomeAssistant=Placeholder
        ),
        "homeassistant.helpers": _module("homeassistant.helpers"),
        "homeassistant.helpers.device_registry": _module(
            "homeassistant.helpers.device_registry", DeviceInfo=dict
        ),
        "homeassistant.helpers.entity": _module(
            "homeassistant.helpers.entity", Entity=Placeholder
        ),
        "homeassistant.helpers.entity_platform": _module(
            "homeassistant.helpers.entity_platform", AddEntitiesCallback=Placeholder
        ),
        "homeassistant.helpers.update_coordinator": _module(
            "homeassistant.helpers.update_coordinator", CoordinatorEntity=Placeholder
        ),
        "custom_components": _module("custom_components"),
        "custom_components.daikinskyport": _module(
            "custom_components.daikinskyport", DaikinSkyportData=Placeholder
        ),
        "custom_components.daikinskyport.const": _module(
            "custom_components.daikinskyport.const",
            _LOGGER=None,
            DOMAIN="daikinskyport",
            COORDINATOR="coordinator",
        ),
    }
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)

    spec = importlib.util.spec_from_file_location(
        "custom_components.daikinskyport.sensor", SENSOR_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("sensor_type", "value", "unit_class", "unit_name", "unit_value"),
    [
        ("CO2", 415, "UnitOfRatio", "PARTS_PER_MILLION", "ppm"),
        ("VOC", 123, "UnitOfRatio", "PARTS_PER_BILLION", "ppb"),
        (
            "ozone",
            80,
            "UnitOfDensity",
            "MICROGRAMS_PER_CUBIC_METER",
            "μg/m³",
        ),
        (
            "particle",
            5,
            "UnitOfDensity",
            "MICROGRAMS_PER_CUBIC_METER",
            "μg/m³",
        ),
        (
            "PM25",
            12,
            "UnitOfDensity",
            "MICROGRAMS_PER_CUBIC_METER",
            "μg/m³",
        ),
        (
            "PM10",
            24,
            "UnitOfDensity",
            "MICROGRAMS_PER_CUBIC_METER",
            "μg/m³",
        ),
    ],
)
def test_air_quality_sensor_preserves_unit_and_value(
    sensor_module: ModuleType,
    sensor_type: str,
    value: int,
    unit_class: str,
    unit_name: str,
    unit_value: str,
) -> None:
    """Each migrated sensor retains its native unit and unmodified value."""

    class FakeSkyport:
        thermostats = [{"id": "test-id", "model": "test-model"}]

        def get_sensors(self, index: int) -> list[dict[str, object]]:
            assert index == 0
            return [{"name": "Outdoor", "type": sensor_type, "value": value}]

    class FakeData:
        daikinskyport = FakeSkyport()
        device_info: dict[str, object] = {}

        async def _async_update_data(self) -> None:
            return None

    expected_unit = getattr(getattr(sensor_module, unit_class), unit_name)
    sensor = sensor_module.DaikinSkyportSensor(
        FakeData(), "Outdoor", sensor_type, 0
    )

    asyncio.run(sensor.async_update())

    assert sensor.native_unit_of_measurement is expected_unit
    assert sensor.native_unit_of_measurement == unit_value
    assert sensor.native_value == value
