# Automating network testing with Iperf3

TCP/IP Networking is a complex topic; it gets really tricky when you are trying to nail down issues like performance, or troubleshooting a problem.

In any case it helps to have tools that can help you to confirm your suspicious or better probe than there is no problem at all; One of those is the Open Source [iperf3](https://github.com/esnet/iperf): 

> iperf is a tool for active measurements of the maximum achievable bandwidth on IP networks. It supports tuning of various parameters related to timing, protocols, and buffers. For each test it reports the measured throughput / bitrate, loss, and other parameters.

Here you will learn how to do the following:

* Inspect bandwidth issues with Iperf3 between 2 endpoints
* Test UDP multicast connectivity (protocols like PTP use it for time synchronization)
* Uncover CRC errors on a network interface (I want to also show what you can do with ethtool and tcpdump to confirm that traffic is indeed dropped by a bad network interface or cable)
* And how to automate to write more complex scripts using Python 3.
* As a bonus will briefly explain CPU affinity and why it may matter to iperf3

You will need to have the following:

* A Linux distribution (all my examples were executed on a Fedora server)
* Ability to run commands as root (Using [SUDO](https://www.sudo.ws/) for example)
* _Basic_ understanding of networking principles

Installing iperf is a simple as doing this on Fedora: ```sudo dnf install -y iperf3```

Without further delay let's get started.

# Measuring bandwidth and jitter

So let's start by defining/ remembering a few things:

* **Throughput**: measures how many packets arrive at their destinations successfully.
* **Network bandwidth** is defined as the maximum transfer throughput capacity of a network.
* **Jitter**: Is the time delay between when a signal is transmitted and when it is received. Good connections have consistent response time.
* **TCP** is a *reliable protoco*l, guarantees arrival of packets on the same order they were sent.
* **UDP** _doesn't have a handshake protocol_ like TCP; It is faster than TCP but if a packet is lost it won't be resent and there is no guarantee on the order packets will arrive.  

Iperf3 works by running a client and a server that talk to each other; For our demostration will run as  follows:

* Client and server binding to the wired ethernet interface (I will not use the Wireless interfaces as they are more prone to jitter due external noise)
* Test will use defaults (port, TCP connection unless we override with the flag ```--udp``` on the client)

Also, will confirm if the following is true:
* The switch in between the 2 machines supports 1000 Mbits/sec connections, and the interfaces are also configured at that capacity.
* Full-duplex mode (send and receive data on the card simultaneously. Will confirm with another tool called ethtool, will explain how it works in a bit)

Running the server:
```shell
josevnz@raspberrypi:~$ sudo ethtool eth0|rg -e 'Speed|Duplex'
	Speed: 1000Mb/s
	Duplex: Full
josevnz@raspberrypi:~$ ip --oneline address|rg 192
2: eth0    inet 192.168.1.11/24 brd 192.168.1.255 scope global dynamic eth0\       valid_lft 2090sec preferred_lft 2090sec
josevnz@raspberrypi:~$ iperf3 --server --bind 192.168.1.11 -affinity 1
-----------------------------------------------------------
Server listening on 5201
-----------------------------------------------------------
```

And now the client:

```shell
[josevnz@dmaf5 ~]$ sudo ethtool eno1|rg -e 'Speed|Duplex'
	Speed: 1000Mb/s
	Duplex: Full
[josevnz@dmaf5 ~]$ iperf3 --client raspberrypi --bind 192.168.1.28 --affinity 1
Connecting to host raspberrypi, port 5201
[  5] local 192.168.1.28 port 47609 connected to 192.168.1.11 port 5201
[ ID] Interval           Transfer     Bitrate         Retr  Cwnd
[  5]   0.00-1.00   sec   111 MBytes   932 Mbits/sec    0   2.79 MBytes       
[  5]   1.00-2.00   sec   110 MBytes   923 Mbits/sec    0   2.98 MBytes       
...     
- - - - - - - - - - - - - - - - - - - - - - - - -
[ ID] Interval           Transfer     Bitrate         Retr
[  5]   0.00-10.00  sec  1021 MBytes   857 Mbits/sec    0             sender
[  5]   0.00-9.95   sec  1020 MBytes   860 Mbits/sec                  receiver

iperf Done.
```

Let's digest the results:
* Zero retries (Retr column). That is good and expected
* Bitrate is around 860 Mbits/sec. The link speed is close to the theoretical bandwidth; Switches have a limit of how much traffic the backplane can handle.
* TCP guarantees losses packet transmission so Jitter is not reported here.

If you reverse the test (client is now server, server is now client) you should see similar results.

# Testing UDP bandwidth 

To test UDP we do the following on the client only:

```shell
[josevnz@dmaf5 ~]$ iperf3 --client raspberrypi --bind 192.168.1.28 --udp --affinity 1
Connecting to host raspberrypi, port 5201
[  5] local 192.168.1.28 port 47985 connected to 192.168.1.11 port 5201
[ ID] Interval           Transfer     Bitrate         Total Datagrams
[  5]   0.00-1.00   sec   129 KBytes  1.05 Mbits/sec  91  
[  5]   1.00-2.00   sec   127 KBytes  1.04 Mbits/sec  90  
[  5]   2.00-3.00   sec   129 KBytes  1.05 Mbits/sec  91  
...
- - - - - - - - - - - - - - - - - - - - - - - - -
[ ID] Interval           Transfer     Bitrate         Jitter    Lost/Total Datagrams
[  5]   0.00-10.00  sec  1.25 MBytes  1.05 Mbits/sec  0.000 ms  0/906 (0%)  sender
[  5]   0.00-9.99   sec  1.25 MBytes  1.05 Mbits/sec  0.028 ms  0/906 (0%)  receiver
```

* Bit-rate is much closer to the theoretical bandwidth. Also, no packet loss, which is great!
* UDP doesn't guarantee packet loss, so Lost datagrams and Jitter are reported (and they have good values).

Now, you may be wondering what is that '--affinity' flag? We didn't really need it here to test the bandwidth on this simple example but will give us an excuse to talk about affinity.

## Quick detour: CPU Affinity, NUMA, isolcpus

If you were curious and checked the documentation and examples of iperf you probably saw references to [CPU or Processor affinity](https://en.wikipedia.org/wiki/Processor_affinity);

So what is it? from the Wikipedia site:

> Enables the binding and unbinding of a process or a thread to a central processing unit (CPU) or a range of CPUs, so that the process or thread will execute only on the designated CPU or CPUs rather than any CPU.

### Why would I want to '_pin_' my process to a specific group of CPU's? 

No instance with pinned CPUs can use the CPUs of another pinned instance, thus preventing resource contention between instances. Non-Uniform Memory Access or NUMA allows multiple CPUs to share L1, L2, L3 caches, and main memory.

If you are using [NUMA hardware](https://en.wikipedia.org/wiki/Non-uniform_memory_access) to ensure you are always [using the memory that is closest to the CPU](https://www.redhat.com/en/blog/driving-fast-lane-cpu-pinning-and-numa-topology-awareness-openstack-compute)

How does a server with several NUMA nodes look like? You can find out with ```lscpu| rg NUMA```:

```shell
[josevnz@dmaf5 ~]$ lscpu|rg NUMA
NUMA node(s):                    2
NUMA node0 CPU(s):               0-7
NUMA node1 CPU(s):               8-15
```

Here you have a 16 CPU server, with 2 NUMA nodes (this is a simplified example, a machine with HyperThreading enabled looks different. Depending on the application [you may decide to disable it](https://bitsum.com/tips-and-tweaks/spreading-the-load/))

Keep in mind than CPU affinity can be used not just to increase networking performance [but also disk](https://support.mellanox.com/s/article/howto-efficiently-utilize-multiple-cores-with-tgt-block-storage). 

Coming back to iperf3, you can pin it to a specific cpu using ```-A, --affinity```, for example CPU 3 (Numbered 0 to n-1):

```shell
# Equivalent of running iperf3 with numactl: /bin/numactl --physcpubind=2 iperf3 -c remotehost
iperf3 --affinity 2 --client remotehost
```

Keep in mind that you may also need to tell the operating system to avoid running host processes on this CPU's, so you if you use Grubby you can do this with [isolcpus](https://www.kernel.org/doc/Documentation/admin-guide/kernel-parameters.txt):

```shell
# Find the default kernel
sudo grubby --default-kernel
# Use that information and add isolcpus parameter, then reboot
sudo grubby --update-kernel=/boot/vmlinuz-5.14.18-100.fc33.x86_64 --args="isolcpus=2"
sudo shutdown -r now 'Updated kernel isolcpus, need to reboot'
```

Again, this is not needed to troubleshoot a networking issue, but it may come handy if you want to make iperf3 behave like one of your fine-tuned applications.

**This is a [complex topic](https://www.intel.com/content/dam/develop/external/us/en/documents/3-5-memmgt-optimizing-applications-for-numa-184398.pdf)**, so get a cup of coffee (or two) and get ready to start reading.

# Using Iperf3 to detect Dropped packets, CRC errors

A [CRC error](https://en.wikipedia.org/wiki/Cyclic_redundancy_check) is caused by a faulty physical device (network card, switch port, cable) or a mismatch on Full/Half duplex configurations between 2 devices; These are sometimes difficult to track on switches with cut-through mode which means it forwards received errors out of all ports.

This is a simplified scenario, where we want to make sure a new network card connection works without CRC errors, rx/tx errors (so the card, cable and switch port are OK).

With that in mind we see that we could do a simple test to ensure our link health is good:

* Capture the status of the CRC, dropped packets errors on the network card we are testing
* Run Iperf on TCP mode for a longer time than usual
* Capture again the network card CRC stats. 

* If the difference is greater than zero then:

1. Check the full duplex on both the card and switch port (ethtool ) 
2. Replace the cable
3. Then reseat or replace the network card
4. Then change the port on the switch

But you get the picture; iperf3 will help us to "burn" the link and trigger any unwanted behaviour before we use this interface in production.

Time to see this in action, say we take a first snapshot on our iperf3 server:

```shell
josevnz@raspberrypi:~$ sudo ethtool --statistics  eth0| rg -i -e 'dropped|error'
     rx_errors: 0
     tx_errors: 0
     rx_dropped: 0
     tx_dropped: 0
     rxq0_errors: 0
     rxq0_dropped: 0
     rxq1_errors: 0
     rxq1_dropped: 0
     rxq2_errors: 0
     rxq2_dropped: 0
     rxq3_errors: 0
     rxq3_dropped: 0
     rxq16_errors: 0
     rxq16_dropped: 0
```
Then the client
```shell
[josevnz@dmaf5 ~]$ sudo ethtool --statistics  eno1| rg -i -e 'dropped|errors'
     tx_errors: 0
     rx_errors: 0
     align_errors: 0
```

Run the Iperf3 server:
```shell
josevnz@raspberrypi:~$ iperf3 --server --bind 192.168.1.11
-----------------------------------------------------------
Server listening on 5201
-----------------------------------------------------------
```

Run the client,  for 120 seconds:
```shell
[josevnz@dmaf5 ~]$ iperf3 --client raspberrypi --bind 192.168.1.28 --time 120 
Connecting to host raspberrypi, port 5201
[  5] local 192.168.1.28 port 41337 connected to 192.168.1.11 port 5201
[ ID] Interval           Transfer     Bitrate         Retr  Cwnd
[  5]   0.00-1.00   sec   111 MBytes   934 Mbits/sec    0   2.94 MBytes       
[  5]   1.00-2.00   sec   111 MBytes   933 Mbits/sec    0   2.95 MBytes       
[  5]   2.00-3.00   sec   111 MBytes   933 Mbits/sec    0   2.95 MBytes       
...
- - - - - - - - - - - - - - - - - - - - - - - - -
[ ID] Interval           Transfer     Bitrate         Retr
[  5]   0.00-120.00 sec  11.0 GBytes   787 Mbits/sec    0             sender
[  5]   0.00-119.70 sec  11.0 GBytes   789 Mbits/sec                  receiver
# Measure again ...
[josevnz@dmaf5 ~]$ sudo ethtool --statistics  eno1| rg -i -e 'dropped|errors'
     tx_errors: 0
     rx_errors: 0
     align_errors: 0
```

Good. Now let's talk about another tool we have been using to get the network interface statistics, ethtool.

## What is ethtool?

> [ethtool](https://en.wikipedia.org/wiki/Ethtool) is the primary means in Linux kernel-based operating systems (primarily Linux and Android) for displaying and modifying the parameters of network interface controllers (NICs) and their associated device driver software from application programs running in userspace.

Little trivia question for you (after you're done checking the man page for ethtool):

1. What does the ```sudo ethtool -g eno1``` command does?
2. And this one?: ```sudo ethtool -s eno1 speed 1000 duplex full autoneg on```

This is another tool that you should have in your toolset. 

# Automating Iperf3 with Python 3

If you notice, Iperf3 has also a library that allows you to integrate this tool with other languages like Python:

```shell
[josevnz@dmaf5 ~]$ rpm -qil iperf3|rg libiperf
/usr/lib64/libiperf.so.0
/usr/lib64/libiperf.so.0.0.0
/usr/share/man/man3/libiperf.3.gz
```

There are several bindings for Python out there:

* [Iperf3 Python](https://github.com/thiezn/iperf3-python) has an API to integrate Iperf3 with Python, using those bindings.
* [Ethtool Python3](https://github.com/fedora-python/python-ethtool) is available but is marked as deprecated. So for what we need, will use it :-).

I will not cover their API here, but rather point you to the source code of a python script that uses iperf3 and ethtool to detect network errors (as we did manually early on). Below you can see it
running.

Please check out [the repository](https://github.com/josevnz/linktester) and run the script, you will be amazed how easy is to automate a few tasks with Python.

# What you can do next?

Learning never stops, so here are a few pointers and observations to keep you going:

* [Fasterdata](https://fasterdata.es.net/performance-testing/network-troubleshooting-tools/iperf/) has more examples on how to use iperf with different parameters
* Still curious about how to use CPU affinity? Check the RedHat [Systemd documentation](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/managing_monitoring_and_updating_the_kernel/assembly_configuring-cpu-affinity-and-numa-policies-using-systemd_managing-monitoring-and-updating-the-kernel), it has very useful examples
* Be aware that isolcpus is considered deprecated and usage of [cpuset](https://man7.org/linux/man-pages/man7/cpuset.7.html) is recommended; Please refer to the following discussion to see how to play with [cpuset](https://stackoverflow.com/questions/11111852/how-to-shield-a-cpu-from-the-linux-scheduler-prevent-it-scheduling-threads-onto)
* You know now how you can write your own troubleshooting scripts with the Iperf3 Python API. You should probably write now an iperf3 [server](https://iperf3-python.readthedocs.io/en/latest/modules.html#server) that can show the results using to a web browser (Maybe combine it with [FastAPI](https://fastapi.tiangolo.com/)?)
