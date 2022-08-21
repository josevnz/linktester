import sys
import unittest

from linktester import BrokenEnvironment, TextLoader
from linktester.link import EthtoolCapture
from linktester.validation import EnvironmentChecker, EthtoolComparator


class ValidationTestCase(unittest.TestCase):

    def test_check_environment(self):
        try:
            EnvironmentChecker.check_environment()
        except BrokenEnvironment as be:
            self.fail(be)

    def test_ethtool_comparison(self):
        first_txt = TextLoader.load('ethtool-eth0-first.txt')
        self.assertIsNotNone(first_txt)
        first_result = EthtoolCapture.parse_results(first_txt)
        self.assertIsNotNone(first_result)
        self.assertLess(0, len(first_result))
        first = EthtoolComparator(first_result)
        second_txt = TextLoader.load('ethtool-eth0-second.txt')
        second_result = EthtoolCapture.parse_results(second_txt)
        second = EthtoolComparator(second_result)
        cmp_results = first.compare(second)

        # Expected to have errors
        self.assertIsNotNone(cmp_results)
        self.assertLess(0, len(cmp_results))
        for key in cmp_results:
            self.assertLess(0, cmp_results[key])
        print(f"{cmp_results}", file=sys.stderr)

        # Reset the counters, should have no errors
        second_result = {'rx_errors': 0, 'tx_errors': 0, 'rx_dropped': 0, 'tx_dropped': 0, 'rx_crc': 0}
        second = EthtoolComparator(second_result)
        cmp_results = first.compare(second)
        self.assertIsNotNone(cmp_results)
        self.assertEqual(0, len(cmp_results))


if __name__ == '__main__':
    unittest.main()
