from shutil import which
from typing import Dict

from linktester import BrokenEnvironment

ethtool = "/sbin/ethtool"
iperf3 = "/bin/iperf3"
ip = "/sbin/ip"


class EnvironmentChecker:

    @staticmethod
    def check_environment():
        for binary in [ethtool, iperf3, ip]:
            if not which(binary):
                raise BrokenEnvironment(f"Missing the following required binary: {binary}")


class EthtoolComparator:

    def __init__(self, results: Dict[str, int]):
        self.results = results

    def compare(self, other) -> Dict[str, int]:
        comparison: Dict[str, int] = {}
        if not isinstance(other, EthtoolComparator):
            raise ValueError(f"Cannot compare {self} with {other}")
        for key in self.results:
            if key not in other.results:
                raise ValueError(f"The following key is missing from the second run results: {key}. First run: {key}={self.results[key]}")
            diff = abs(self.results[key] - other.results[key])
            if diff > 0:
                comparison[key] = diff
        return comparison
