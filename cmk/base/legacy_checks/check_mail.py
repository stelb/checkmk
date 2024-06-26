#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.check_mail import general_check_mail_args_from_params
from cmk.base.config import active_check_info

CHECK_IDENT = "check_mail"


def check_mail_arguments(params):
    """
    >>> for a in check_mail_arguments({
    ...     'service_description': 'Email',
    ...     'fetch': ('IMAP', {
    ...       'server': 'imap.gmx.de',
    ...       'auth': ('basic', ('me@gmx.de', ('password', 'p4ssw0rd'))),
    ...       'connection': {'disable_tls': True, 'port': 123}}),
    ...     'forward': {'facility': 2, 'application': None, 'host': 'me.too@checkmk.com',
    ...     'cleanup': True}}):
    ...   print(a)
    --fetch-protocol=IMAP
    --fetch-server=imap.gmx.de
    --fetch-port=123
    --fetch-username=me@gmx.de
    --fetch-password=p4ssw0rd
    --forward-ec
    --forward-facility=2
    --forward-host=me.too@checkmk.com
    --cleanup=delete
    """
    args: list[str | tuple[str, str, str]] = general_check_mail_args_from_params(
        CHECK_IDENT, params
    )

    if "forward" in params:
        forward = params["forward"]
        args.append("--forward-ec")

        if forward.get("method"):
            args.append(f"--forward-method={forward['method']}")

        if forward.get("match_subject"):
            args.append(f"--match-subject={forward['match_subject']}")

        # int - can be 0
        if "facility" in forward:
            args.append(f"--forward-facility={forward['facility']}")

        if forward.get("host"):
            args.append(f"--forward-host={forward['host']}")

        if forward.get("application"):
            args.append(f"--forward-app={forward['application']}")

        # int - can be 0
        if "body_limit" in forward:
            args.append(f"--body-limit={forward['body_limit']}")

        if isinstance(forward.get("cleanup"), bool):  # can never be False
            args.append("--cleanup=delete")

        elif isinstance(forward.get("cleanup"), str):
            move_to_subfolder = forward["cleanup"]
            args.append(f"--cleanup={move_to_subfolder}")

    return args


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just run this file from your IDE and dive into the code.
    import doctest

    assert not doctest.testmod().failed
else:
    active_check_info["mail"] = {
        "command_line": f"{CHECK_IDENT} $ARG1$",
        "argument_function": check_mail_arguments,
        "service_description": lambda params: params["service_description"],
    }
