import functools
import os
from ConfigParser import SafeConfigParser


config = SafeConfigParser()
config.read('/etc/fabdeploytools.ini')


def get_opt(section, opt, getter=config.get, default=None):
    if not config.has_option(section, opt):
        return default

    return getter(section, opt)

get_bool = functools.partial(get_opt, getter=config.getboolean,
                             default=False)

use_yum = get_bool('global', 'use_yum')

pip_cache = os.getenv('FABDEPLOYTOOLS_PIP_CACHE', '/tmp/pip-cache')
