#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import socket
import sys

GPU = 'GPU'
PGA = 'PGA'
DEVS = 'DEVS'
SENTINEL = object()


class Device(object):
    REGISTRY = {}

    class __metaclass__(type):
        def __init__(cls, name, bases, dict):
            if cls.__name__ != 'Device':
                cls.REGISTRY[cls.__name__] = cls

    def __new__(cls, data, *args, **kwargs):
        if cls != Device:
            return object.__new__(cls, *args, **kwargs)

        new_cls = None
        for key in data:
            new_cls = cls.REGISTRY.get(key)
            if new_cls is not None:
                break

        if new_cls is None:
            raise TypeError('Unknown Device (%s)' % data)

        return new_cls(data, *args, **kwargs)

    def __init__(self, data):
        self._data = data

        self.accepted = data['Accepted']
        self.enabled = data['Enabled'] == 'Y'
        self.mh = data['Total MH']
        self.rejected = data['Rejected']
        self.temperature = data['Temperature']
        self.utility = data['Utility']
        self.uptime = data['Device Elapsed']

    @property
    def ident(self):
        return self._data[self.__class__.__name__]


class GPU(Device):
    pass


class PGA(Device):
    pass


class CGMiner(object):
    def __init__(self, host='localhost', port=4028):
        self._host = host
        self._port = int(port)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __call__(self, command, parameter=None):
        cmd = {'command': command}

        if parameter is not None:
            cmd['parameter'] = parameter

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self._host, self._port))
        sock.send(json.dumps(cmd))

        buff = ''
        chunk = sock.recv(4096)

        while len(chunk) != 0:
            buff = buff + chunk
            chunk = sock.recv(4096)

        sock.close()
        buff = buff.replace('\x00', '')
        return json.loads(buff)

    @property
    def devs(self):
        data = self('devs')
        if DEVS not in data:
            return []

        return [Device(dev) for dev in data[DEVS]]


def configure(cgminer):
    lines = []
    add = lines.append
    devs = cgminer.devs

    add('multigraph cgminer_hashrate')
    add('graph_category mining')
    add('graph_title Hashrate')
    add('graph_vlabel Hash/s')
    add('graph_args --base 1000 --lower-limit 0')

    for dev in devs:
        dev_type = dev.__class__.__name__
        prefix = '%s_%s' % (dev_type.lower(), dev.ident)

        add('%s.label %s %s' % (prefix, dev_type, dev.ident))
        add('%s.type DERIVE' % prefix)
        add('%s.min 0' % prefix)
        add('%s.draw AREASTACK' % prefix)

    add('multigraph cgminer_utility')
    add('graph_category mining')
    add('graph_title Utility')
    add('graph_vlabel Shares/Min')

    for dev in devs:
        dev_type = dev.__class__.__name__
        prefix = '%s_%s' % (dev_type.lower(), dev.ident)

        add('%s.label %s %s' % (prefix, dev_type, dev.ident))
        add('%s.type GAUGE' % prefix)
        add('%s.draw LINE' % prefix)

    add('multigraph cgminer_temperature')
    add('graph_category mining')
    add('graph_title Temperature')
    add('graph_vlabel Degrees Celsius')

    for dev in devs:
        dev_type = dev.__class__.__name__
        prefix = '%s_%s' % (dev_type.lower(), dev.ident)

        add('%s.label %s %s' % (prefix, dev_type, dev.ident))
        add('%s.type GAUGE' % prefix)
        add('%s.draw LINE' % prefix)

    add('multigraph cgminer_accepted')
    add('graph_category mining')
    add('graph_title Accepted')
    add('graph_vlabel Shares')

    for dev in devs:
        dev_type = dev.__class__.__name__
        prefix = '%s_%s' % (dev_type.lower(), dev.ident)

        add('%s.label %s %s' % (prefix, dev_type, dev.ident))
        add('%s.type COUNTER' % prefix)
        add('%s.draw AREASTACK' % prefix)

    add('multigraph cgminer_rejected')
    add('graph_category mining')
    add('graph_title Rejected')
    add('graph_vlabel Shares')

    for dev in devs:
        dev_type = dev.__class__.__name__
        prefix = '%s_%s' % (dev_type.lower(), dev.ident)

        add('%s.label %s %s' % (prefix, dev_type, dev.ident))
        add('%s.type COUNTER' % prefix)
        add('%s.draw AREASTACK' % prefix)

    return lines


def fetch(cgminer):
    lines = []
    add = lines.append
    devs = cgminer.devs

    add('multigraph cgminer_hashrate')

    for dev in devs:
        dev_type = dev.__class__.__name__
        prefix = '%s_%s' % (dev_type.lower(), dev.ident)
        add('%s.value %d' % (prefix, dev.mh * 1e6))

    add('multigraph cgminer_utility')

    for dev in cgminer.devs:
        dev_type = dev.__class__.__name__
        prefix = '%s_%s' % (dev_type.lower(), dev.ident)
        add('%s.value %f' % (prefix, dev.utility))

    add('multigraph cgminer_temperature')

    for dev in cgminer.devs:
        dev_type = dev.__class__.__name__
        prefix = '%s_%s' % (dev_type.lower(), dev.ident)
        add('%s.value %f' % (prefix, dev.temperature))

    add('multigraph cgminer_accepted')

    for dev in cgminer.devs:
        dev_type = dev.__class__.__name__
        prefix = '%s_%s' % (dev_type.lower(), dev.ident)
        add('%s.value %d' % (prefix, dev.accepted))

    add('multigraph cgminer_rejected')

    for dev in cgminer.devs:
        dev_type = dev.__class__.__name__
        prefix = '%s_%s' % (dev_type.lower(), dev.ident)
        add('%s.value %d' % (prefix, dev.rejected))

    return lines


if __name__ == '__main__':
    host = os.getenv("host", "localhost")
    port = int(os.getenv("port", 4028))

    cgminer = CGMiner(host, port)

    if len(sys.argv) == 2 and sys.argv[1] == 'config':
        data = configure
    else:
        data = fetch

    print '\n'.join(data(cgminer))
