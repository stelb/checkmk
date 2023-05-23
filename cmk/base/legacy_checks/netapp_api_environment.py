#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="no-untyped-def"

from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.check_legacy_includes.netapp_api import maybefloat, netapp_api_parse_lines
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info

# <<<netapp_api_environment:sep(9)>>>
# sensor-name PSU1 FAULT  sensor-type discrete    node-name BIN-CL1-N1    discrete-sensor-value OK    discrete-sensor-state normal    threshold-sensor-state normal


def _parse_netapp_api_environment(info):
    def item_func(name, values):
        try:
            return "%(node-name)s / %(sensor-name)s" % values
        except KeyError:
            return name

    return netapp_api_parse_lines(info, item_func=item_func)


def discover_api_environment(predicate=None):
    """Discovery function factory accepting 'key' function.

    :param predicate:
        A function which takes the parsed item-data and evaluates to True if this particular
        parsed item should be discovered. Returning False will not discover the item.

    :return:
        A function which takes a parsed item and discovers it or not, depending on the predicate.
    """

    def discovery_netapp_api_environment(parsed):
        for item_name, values in parsed.items():
            if predicate is None:
                yield item_name, None
            elif predicate(values):
                yield item_name, None
            else:
                continue

    return discovery_netapp_api_environment


def check_netapp_api_environment_discrete(item, _no_params, parsed):
    if not (data := parsed.get(item)):
        return

    sensor_value = data.get("discrete-sensor-value")
    if sensor_value is None:
        return

    # According to the documentation the states may vary depending on the platform,
    # but will always include "normal" and "failed"
    sensor_state = data["discrete-sensor-state"]
    if sensor_state == "normal":
        state = 0
    else:
        state = 2

    yield state, "Sensor state: %s, Sensor value: %s" % (sensor_state, sensor_value)


def check_netapp_api_environment_threshold(item, _no_params, parsed):
    """Check a service giving continuous values and boundaries of said"""

    def _perf_key(_key):
        return _key.replace("/", "").replace(" ", "_").replace("__", "_").lower()

    # We don't want mV or mA, but V or A as this is what the metrics are built for.
    def _scale(val, _unit):
        if val is not None and _unit.lower() in ("mv", "ma"):
            val /= 1000.0
        return val

    def _scale_unit(_unit):
        return {"mv": "v", "ma": "a"}.get(_unit.lower(), _unit.lower())

    if not (data := parsed.get(item)):
        return

    sensor_value = maybefloat(data.get("threshold-sensor-value"))
    if sensor_value is None:
        return

    # NOTE
    # sensor_type may be fru, discrete (see other check), fan, thermal, current or voltage.
    # (Also battery_life, unknown and counter, but these are currently not used.)
    unit = data.get("value-units", "")

    # fmt: off
    levels = (_scale(maybefloat(data.get('warning-high-threshold')), unit),
              _scale(maybefloat(data.get('critical-high-threshold')), unit),
              _scale(maybefloat(data.get('warning-low-threshold')), unit),
              _scale(maybefloat(data.get('critical-low-threshold')), unit))
    # fmt: on

    sensor_type = data["sensor-type"]
    sensor_name = data["sensor-name"]

    if sensor_type == "thermal":
        yield check_temperature(
            _scale(sensor_value, unit),
            _no_params,
            _perf_key("netapp_environment_thermal_%s" % (sensor_name,)),
            dev_unit=_scale_unit(unit),
            dev_levels=levels[:2],
            dev_levels_lower=levels[2:],
        )
        return

    if sensor_type == "fan":
        # we don't want to see decimal rpms
        human_readable_func = int
    else:
        # We want to see the voltage and current in more detail
        human_readable_func = None

    yield check_levels(
        _scale(sensor_value, unit),
        sensor_type,  # coincidentally the same as ours. (current, voltage, fan)
        levels,
        unit=_scale_unit(unit),
        human_readable_func=human_readable_func,
    )


check_info["netapp_api_environment"] = LegacyCheckDefinition(
    check_function=check_netapp_api_environment_discrete,
    discovery_function=discover_api_environment(
        lambda v: v["sensor-name"].startswith("PSU") and v["sensor-name"].endswith(" FAULT")
    ),
    parse_function=_parse_netapp_api_environment,
    service_name="PSU Controller %s",
    check_ruleset_name="hw_psu",
)


def _is_fan(_sensor_name) -> bool:
    return _sensor_name is not None and "fan" in _sensor_name.lower()


check_info["netapp_api_environment.fan_faults"] = LegacyCheckDefinition(
    check_function=check_netapp_api_environment_discrete,
    discovery_function=discover_api_environment(
        lambda v: _is_fan(v.get("sensor-name")) and v["sensor-name"].endswith(" Fault")
    ),
    parse_function=_parse_netapp_api_environment,
    service_name="Fan Controller %s",
    check_ruleset_name="hw_fans",
)

check_info["netapp_api_environment.temperature"] = LegacyCheckDefinition(
    check_function=check_netapp_api_environment_threshold,
    discovery_function=discover_api_environment(lambda v: v.get("sensor-type") == "thermal"),
    parse_function=_parse_netapp_api_environment,
    service_name="System Temperature %s",
    check_ruleset_name="temperature",
)

check_info["netapp_api_environment.fans"] = LegacyCheckDefinition(
    check_function=check_netapp_api_environment_threshold,
    discovery_function=discover_api_environment(lambda v: v.get("sensor-type") == "fan"),
    parse_function=_parse_netapp_api_environment,
    service_name="System Fans %s",
    check_ruleset_name="hw_fans",
)

check_info["netapp_api_environment.voltage"] = LegacyCheckDefinition(
    check_function=check_netapp_api_environment_threshold,
    discovery_function=discover_api_environment(
        lambda v: v.get("sensor-type") == "voltage" and v.get("value-units")
    ),
    parse_function=_parse_netapp_api_environment,
    service_name="System Voltage %s",
    check_ruleset_name="voltage",
)

check_info["netapp_api_environment.current"] = LegacyCheckDefinition(
    check_function=check_netapp_api_environment_threshold,
    discovery_function=discover_api_environment(
        lambda v: v.get("sensor-type") == "current" and v.get("value-units")
    ),
    parse_function=_parse_netapp_api_environment,
    service_name="System Currents %s",
)
