#!/usr/bin/env python3
"""
Script to test the quality of a network link between 2 servers, using Iperf3 and ethtool.
More [details](https://github.com/josevnz/linktester/blob/main/README.md)?
Author: Jose Vicente Nunez
"""
import sys
from argparse import ArgumentParser
from rich.console import Console
from rich.traceback import install
from linktester.link import DEFAULT_IPERF_PORT, DEFAULT_DURATION, Client, EthtoolCapture, InterfaceLister
from linktester.validation import EnvironmentChecker, EthtoolComparator

DEFAULT_INTERFACE = InterfaceLister().get_interfaces()[0]

if __name__ == "__main__":
    install(show_locals=True)
    error_console = Console(stderr=True)
    console = Console()
    try:
        EnvironmentChecker.check_environment()
    except ValueError as ve:
        error_console.print_exception(show_locals=True)
        sys.exit(100)

    PARSER = ArgumentParser(description=__doc__)
    PARSER.add_argument(
        '--port',
        action='store',
        default=DEFAULT_IPERF_PORT,
        help=f"Override default iperf3 port {DEFAULT_IPERF_PORT}"
    )
    PARSER.add_argument(
        '--remote_server',
        action='store',
        required=True,
        help='The remote server that is running `iperf3 --server`'
    )
    PARSER.add_argument(
        '--duration',
        action='store',
        default=DEFAULT_DURATION,
        help=f"Default duration of the test. Default=({DEFAULT_DURATION} seconds"
    )
    PARSER.add_argument(
        '--verbose',
        action='store_true',
        default=False,
        help="Enable verbose mode"
    )
    PARSER.add_argument(
        '--interface',
        action='store',
        required=False,
        default=DEFAULT_INTERFACE,
        help=f"Default interface to monitor and bind with iperf. Default={DEFAULT_INTERFACE}"
    )

    ARGS = PARSER.parse_args()
    with console.pager():
        client = Client(
            verbose=ARGS.verbose,
            duration=ARGS.duration,
            port=ARGS.port,
            server_hostname=ARGS.remote_server
        )

        ethtool_first = EthtoolCapture(ARGS.interface)
        first_capture = ethtool_first.capture()
        results = client.start()
        ethtool_second = EthtoolCapture(ARGS.interface)
        second_capture = ethtool_first.capture()

        first = EthtoolComparator(first_capture)
        second = EthtoolComparator(second_capture)
        cmp_results = first.compare(second)
        if ARGS.verbose:
            console.print(f"Iperf stats {results}")
        if len(cmp_results) > 0:
            console.print(f"The following counters had problems: {cmp_results}")
            sys.exit(100)
    sys.exit(0)
