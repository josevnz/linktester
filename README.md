# What is linktester?

[![Downloads](https://pepy.tech/badge/linktester)](https://pepy.tech/project/linktester)

linktester is a small link test application that uses iperf3 and ethtool to look for errors, problems on
a network link. You could use it for example to test a new physical connection between a new card you installed
on a server and an existing machine.

## How does it work

The way is works is simple:

* Capture statistics on the card using ethtool
* Wait for a remote iperf3 server to start. Once is up, send TCP traffic to trigger for a few minutes any unwanted behaviour.
* Capture statistics on the card using ethtool a second time and compare error counters
* Report back

# Requirements

* iperf3 and iperf3 libraries (most distributions have RPM, DEB packages) 
* Python3
* Rest of the dependencies will be installed with PIP and a virtual environment: rich, python3-iperf3

For example, on Fedora (or any RPM based system) you can install the dependencies as follows:

```shell
sudo dnf -y install iperf3 python3-ethtool libnl
```

On a Debian based distribution:

```shell
sudo apt-get install -y python3-ethtool iperf3
```

## Virtual environment

I do recommend you use a virtual environment for the installation:

```shell
python3 -m virtualenv $HOME/virtualenv/linktester
. $HOME/virtualenv/linktester/bin/activate
```

For the rest of the installation instructions I will assume you have activated your virtual environment as explained above.

# Installation

Once all the base bindings are installed then you can proceed to install from Pypi.org:

```shell
pip install linktester
```

# Developers

If you want to contribute features you can do this:

```shell
python3 -m virtualenv $HOME/virtualenv/linktester
. $HOME/virtualenv/linktester/bin/activate
git clone git@github.com:josevnz/linktester.git
python setup.py develop
```

# Bugs

Please report any bugs on the official linktester page
