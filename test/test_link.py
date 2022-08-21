import multiprocessing
import sys
import unittest

from linktester.link import EthtoolCapture, InterfaceLister, Client, Server


class LinktesterTestCase(unittest.TestCase):

    def test_get_interfaces(self):
        ifaces = InterfaceLister()
        iface_list = ifaces.get_interfaces()
        self.assertIsNotNone(iface_list)
        self.assertGreater(len(iface_list), 0)

    def test_ethtool(self):
        """
        This test uses the first active interface your test machine has available
        :return:
        """
        ethtool = EthtoolCapture(InterfaceLister().get_interfaces()[0])
        captured = ethtool.capture()
        self.assertIsNotNone(captured)
        self.assertGreater(len(captured), 0)
        self.assertIn('tx_errors', captured)

    def test_client_and_server(self):
        """
        Start both a server and a client and get the results.
        :return:
        """

        def start_server():
            server = Server(verbose=True)
            print(f"Starting server {server}", file=sys.stderr)
            server.start()
            print(f"Stopping server {server}", file=sys.stderr)

        process = multiprocessing.Process(target=start_server, args=())
        process.start()
        process.join(timeout=10)  # Enough time for the server to start ...
        client = Client(duration=5, verbose=True)
        client_result = client.start()
        self.assertIsNotNone(client_result)
        print(client_result.json)


if __name__ == '__main__':
    unittest.main()
