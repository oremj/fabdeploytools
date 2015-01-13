import os
from distutils.core import setup


data_files = []

if os.path.isdir('/etc/bash_completion.d'):
    data_files.append(('/etc/bash_completion.d',
                       ['contrib/bash-completion/clusterrun']))

setup(
    name='fabdeploytools',
    version='0.0.6',
    description='Deploy tools for fabric',
    author='Jeremy Orem',
    author_email='oremj@mozilla.com',
    packages=['fabdeploytools'],
    scripts=['scripts/clusterrun'],
    data_files=data_files
)
