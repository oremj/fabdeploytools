from fabric import api
import json


def loadenv(f):
    roles = json.load(open(f))
    api.env.roledefs = roles
    all_hosts = []
    for v in roles.values():
        all_hosts.extend(v)
    api.env.roledefs['all'] = all_hosts
