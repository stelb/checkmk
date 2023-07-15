#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from typing import Any, Iterable, Mapping

from cmk.base.check_api import get_average, get_rate, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import contains, OIDEnd, SNMPTree
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

Section = Mapping[str, int]

CheckResult = Iterable[tuple[int, str, list]]

DiscoveryResult = Iterable[tuple[None, dict]]


def parse_pfsense_counter(string_table: StringTable) -> Section:
    names = {
        "1.0": "matched",
        "2.0": "badoffset",
        "3.0": "fragment",
        "4.0": "short",
        "5.0": "normalized",
        "6.0": "memdrop",
    }

    parsed = {}
    for end_oid, counter_text in string_table:
        parsed[names[end_oid]] = int(counter_text)
    return parsed


def discovery_pfsense_counter(section: Section) -> DiscoveryResult:
    return [(None, {})]


def check_pfsense_counter(
    _no_item: None, params: Mapping[str, Any], section: Section
) -> CheckResult:
    namestoinfo = {
        "matched": "Packets that matched a rule",
        "badoffset": "Packets with bad offset",
        "fragment": "Fragmented packets",
        "short": "Short packets",
        "normalized": "Normalized packets",
        "memdrop": "Packets dropped due to memory limitations",
    }

    this_time = time.time()

    if params.get("average"):
        backlog_minutes = params["average"]
        yield 0, "Values averaged over %d min" % params["average"], []
    else:
        backlog_minutes = None

    for what in section:
        rate = get_rate("pfsense_counter-%s" % what, this_time, section[what])
        perfrate = ("fw_packets_" + what, rate)

        if backlog_minutes:
            avgrate = get_average("pfsense_counter-%srate" % what, this_time, rate, backlog_minutes)
            check_against = avgrate
            perfavg = ("fw_avg_packets_" + what, avgrate)
        else:
            perfavg = None
            check_against = rate
        infotext = "%s: %.2f pkts/s" % (namestoinfo[what], check_against)

        status = 0
        if params.get(what):
            warn, crit = params[what]
            perfrate += params[what]
            if perfavg:
                perfavg += params[what]
            levelstext = " (warn/crit at %.2f/%.2f pkts/s)" % (warn, crit)
            if crit and check_against >= crit:
                status = 2
                infotext += levelstext
            elif warn and check_against >= warn:
                status = 1
                infotext += levelstext

        perfdata = [perfrate]
        if perfavg:
            perfdata.append(perfavg)

        yield status, infotext, perfdata


check_info["pfsense_counter"] = LegacyCheckDefinition(
    detect=contains(".1.3.6.1.2.1.1.1.0", "pfsense"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12325.1.200.1",
        oids=[OIDEnd(), "2"],
    ),
    parse_function=parse_pfsense_counter,
    service_name="pfSense Firewall Packet Rates",
    discovery_function=discovery_pfsense_counter,
    check_function=check_pfsense_counter,
    check_ruleset_name="pfsense_counter",
    check_default_parameters={
        "badoffset": (100.0, 10000.0),
        "short": (100.0, 10000.0),
        "memdrop": (100.0, 10000.0),
        "normalized": (100.0, 10000.0),
        "fragment": (100.0, 10000.0),
        "average": 3,
    },
)
