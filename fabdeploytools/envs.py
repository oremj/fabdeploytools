import json
import re

from fabric import api


def expand_hosts(hosts):
    new_hosts = []
    for host in hosts:
        m = re.search('(.*)\[(\d+):(\d+)\](.*)', host)
        if m:
            lower = int(m.group(2))
            upper = int(m.group(3))
            head, tail = m.group(1, 4)
            if lower < upper:
                for j in range(lower, upper + 1):
                    new_hosts.append("{0}{1}{2}".format(head, j, tail))
        else:
            new_hosts.append(host)

    return new_hosts


def loadenv(f):
    roles = json.load(open(f))
    for role, hosts in roles.iteritems():
        roles[role] = expand_hosts(hosts)

    api.env.roledefs = roles
    all_hosts = []
    for v in roles.values():
        all_hosts.extend(v)
    api.env.roledefs['all'] = all_hosts
