import logging
import re
import subprocess
from typing import Dict, Set, List

from iperf3 import iperf3, TestResult

from linktester import LinkError
from linktester.validation import ethtool as ethtool_cmd, ip

LOCALHOST = '127.0.0.1'
DEFAULT_IPERF_PORT = 5201
DEFAULT_DURATION = 60


class InterfaceLister:
    """
    Pase the output of the active network interfaces with an assigned IP. For example:
    (Iperf3) [josevnz@dmaf5 Iperf3]$ /usr/sbin/ip --oneline address
    1: lo    inet 127.0.0.1/8 scope host lo\\       valid_lft forever preferred_lft forever
    1: lo    inet6 ::1/128 scope host \\       valid_lft forever preferred_lft forever
    3: eno1    inet 192.168.1.30/24 brd 192.168.1.255 scope global dynamic noprefixroute eno1\\       valid_lft 1879sec preferred_lft 1879sec
    3: eno1    inet6 fd22:4e39:e630:1:1937:89d4:5cbc:7a8d/64 scope global noprefixroute \\       valid_lft forever preferred_lft forever
    3: eno1    inet6 fe80::3f7d:217e:9952:9cdb/64 scope link noprefixroute \\       valid_lft forever preferred_lft forever
    4: wlp4s0    inet 192.168.1.31/24 brd 192.168.1.255 scope global dynamic noprefixroute wlp4s0\\       valid_lft 1883sec preferred_lft 1883sec
    4: wlp4s0    inet6 fd22:4e39:e630:1:e711:3539:b731:10dd/64 scope global noprefixroute \\       valid_lft forever preferred_lft forever
    4: wlp4s0    inet6 fe80::bee5:d01a:abce:a775/64 scope link noprefixroute \\       valid_lft forever preferred_lft forever
    5: virbr0    inet 192.168.122.1/24 brd 192.168.122.255 scope global virbr0\\       valid_lft forever preferred_lft forever
    7: docker0    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0\\       valid_lft forever preferred_lft forever
    """

    def __init__(self):
        self.ip = [ip, '--oneline', 'address']

    def get_interfaces(self) -> List[str]:
        """
        This method will skip loopback and virtual interfaces on purpose
        :return:
        """
        completed: subprocess.CompletedProcess = subprocess.run(capture_output=True, args=self.ip)
        completed.check_returncode()
        captured: Set[str] = set([])
        for line in bytes.decode(completed.stdout).split('\n'):
            tokens = line.strip().split(' ')
            if len(tokens) < 2:
                continue
            if not re.search("docker\\d+|wlp\\d+|virbr\\d+|lo", tokens[1]):
                captured.add(tokens[1])
        return list(captured)


class EthtoolCapture:
    """
    This class knows how to parse input like this:
    NIC statistics:
     tx_packets: 237892
     rx_packets: 415812
     tx_errors: 0
     rx_errors: 0
     rx_missed: 0
     align_errors: 0
     tx_single_collisions: 0
     tx_multi_collisions: 0
     unicast: 317814
     broadcast: 24192
     multicast: 73806
     tx_aborted: 0
     tx_underrun: 0
    """

    interesting_keys = {
        'tx_errors',
        'rx_errors',
        'rx_missed',
        'align_errors',
        'tx_aborted',
        'tx_underrun',
        'rx_dropped',
        'tx_dropped',
        'rx_crc'
    }

    @staticmethod
    def parse_results(results: str):
        captured: dict[str, int] = {}
        for line in results.split('\n'):
            tokens = line.strip().split(':')
            if len(tokens) < 2:
                continue
            if tokens[0] in EthtoolCapture.interesting_keys:
                captured[tokens[0]] = int(tokens[1])
        return captured

    def __init__(self, interface: str):
        self.ethtool_args = [ethtool_cmd, '--statistics', interface]
        self.interesting_keys = {'tx_errors', 'rx_errors', 'rx_missed', 'align_errors', 'tx_aborted', 'tx_underrun'}

    def capture(self) -> Dict[str, int]:
        """
        Parse the output of ethtool
        :return:
        """
        completed: subprocess.CompletedProcess = subprocess.run(capture_output=True, args=self.ethtool_args)
        completed.check_returncode()
        captured: dict[str, int] = EthtoolCapture.parse_results(bytes.decode(completed.stdout))
        return captured


class Server:
    """
    Small variation of the server, used for unit testing against localhost.
    Next version may swan a server for you automatically on the remote host
    """

    def __init__(
            self,
            *,
            verbose: bool = False,
            port: int = DEFAULT_IPERF_PORT,
            bind_address: str = LOCALHOST,
            forever: bool = False
    ):
        server = iperf3.Server()
        server.verbose = verbose
        server.port = port
        server.bind_address = bind_address
        self.server = server
        self.forever = forever
        self.verbose = verbose
        self.bind_address = bind_address
        self.port = port

    def start(self):
        if self.verbose:
            logging.info("Starting server")
        while True:
            self.server.run()
            if not self.forever:
                break
        if self.verbose:
            logging.info("Shutting down server")

    def __str__(self) -> str:
        return f"Server: bind_address={self.bind_address}, port={self.bind_address}, forever={self.forever}"


class Client:
    def __init__(
            self,
            *,
            duration: int = DEFAULT_DURATION,
            verbose: bool = False,
            reverse: bool = False,
            port: int = DEFAULT_IPERF_PORT,
            bind_address: str = None,
            server_hostname: str = LOCALHOST
    ):
        client = iperf3.Client()
        client.duration = 1
        if bind_address:
            client.bind_address = bind_address
        client.server_hostname = server_hostname
        client.duration = duration
        client.port = port
        client.zerocopy = True
        client.verbose = verbose
        client.reverse = reverse
        self.client = client
        self.verbose = verbose
        self.server_hostname = server_hostname
        self.bind_address = bind_address
        self.duration = duration
        self.port = port

    def start(self) -> TestResult:
        results = self.client.run()
        if results.error:
            raise LinkError(f"{self.server_hostname}:{self.port}, bind_address (override):{self.bind_address}, results.error")
        if self.verbose:
            logging.info(results)
        return results

    def __str__(self) -> str:
        return f"Client: server_hostname={self.server_hostname}, port={self.bind_address}, duration={self.duration}"
