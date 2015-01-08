import hashlib
import os

from fabric.api import (execute, lcd, local, parallel,
                        put, roles, run, sudo, task)
from .rpm import RPMBuild
from . import config
from time import sleep


@task
def git_update(src_dir, ref):
    with lcd(src_dir):
        local('git fetch')
        local('git fetch -t')
        local('git reset --hard %s' % ref)
        local('git submodule sync')
        local('git submodule update --init --recursive')
        local("git submodule foreach 'git submodule sync --quiet'")
        local("git submodule foreach "
              "'git submodule update --init --recursive'")


@task
def git_info(src_dir):
    with lcd(src_dir):
        local('git status')
        local('git log -1')


@task
def pip_install_reqs(venv, pyrepo, requirements):
    local('%s/bin/pip install --exists-action=w --no-deps --no-index '
          '--download-cache=/tmp/pip-cache -f %s '
          '-r %s' % (venv, pyrepo, requirements))

    local('%s/bin/pip install --exists-action=w --no-deps --no-index '
          '--download-cache=/tmp/pip-cache -f %s '
          'virtualenv' % (venv, pyrepo))


@task
def create_venv(venv, pyrepo, requirements, update_on_change=False,
                rm_first=True):
    """venv: directory where venv should be placed
       update_on_change: only update venv if requirements have changed
       rm_first: rm -rf the virtualenv first."""

    md5_file = os.path.join(venv, 'MD5SUM')
    md5sum = hashlib.md5(open(requirements).read()).hexdigest()
    if update_on_change:
        try:
            f = open(md5_file)
            if f.read() == md5sum:
                print "Virtualenv is current"
                return
        except IOError:
            pass

    # only rm if venv is in the path, for safety
    if rm_first and 'venv' in venv:
        local('rm -rf %s' % venv)

    local('virtualenv --python=python --distribute --never-download %s' % venv)
    pip_install_reqs(venv, pyrepo, requirements)

    local('rm -f %s/lib/python2.{6,7}/no-global-site-packages.txt' % venv)
    local('{0}/bin/python {0}/bin/virtualenv '
          '--relocatable {0}'.format(venv))

    with open(md5_file, 'w') as f:
        f.write(md5sum)


def git_ref(app):
    """app: location of app. Returns currently installed ref"""
    with lcd(app):
        return local('git rev-parse HEAD', capture=True)


@task
def git_latest_tag(app=os.getcwd()):
    """app: location of app. Returns latest tag"""
    with lcd(app):
        local('git fetch')
        local('git fetch -t')
        return local('git describe --abbrev=0 --tags', capture=True)


def get_app_dirs(fabfile):
    """If fabfile is at /tmp/domain/app_dir/fabfile.py, this will return
       /tmp/domain, /tmp/domain/app_dir

       Typically called as get_app_dirs(__file__) from fabfile.py
    """
    APP = os.path.dirname(os.path.abspath(fabfile))
    ROOT = os.path.dirname(APP)
    return ROOT, APP


def build_rpm(name, env, cluster, domain, root, app_dir=None, s3_bucket=None,
              use_sudo=False, package_dirs=None):

    if app_dir is None:
        app_dir = name

    if package_dirs is None:
        package_dirs = [app_dir]

    r = RPMBuild(name=name, env=env, cluster=cluster, domain=domain,
                 use_sudo=use_sudo, s3_bucket=s3_bucket,
                 ref=git_ref(os.path.join(root, app_dir)))
    r.build_rpm(root, package_dirs)

    return r


def local_install(rpm_file):
    local('yum -q -y --disableplugin=rhnplugin install "%s"' % rpm_file)


def deploy_from_file(rpm_file, deploy_roles=None, use_sudo=False,
                     use_yum=config.use_yum):
    _run = sudo if use_sudo else run

    if deploy_roles is None:
        deploy_roles = ['web']

    rpm_name_version = local('rpm -q %s' % rpm_file, capture=True)

    @task
    @roles(*deploy_roles)
    @parallel
    def install():
        if use_yum:
            _run('yum -q -y '
                 '--disableplugin=rhnplugin '
                 '--disablerepo=* --enablerepo=deploytools install '
                 '{0}'.format(rpm_name_version))
        else:
            remote_rpm_file = os.path.join('/tmp', os.path.basename(rpm_file))
            put(rpm_file, remote_rpm_file)
            _run('yum -q -y --disableplugin=rhnplugin '
                 'install "%s"' % remote_rpm_file)
            _run('rm -f %s', remote_rpm_file)

    execute(install)


def deploy(name, env, cluster, domain, root, app_dir=None, s3_bucket=None,
           use_sudo=False, deploy_roles='web', package_dirs=None,
           use_yum=config.use_yum):
    """
    root: package root, e.g., '/data/www/www.test.com'
    app_dir: relative to root e.g., 'testapp', defaults to "name"
    package_dirs: relative to root, which dirs to include in the package.
    """

    if app_dir is None:
        app_dir = name

    if package_dirs is None:
        package_dirs = [app_dir]

    r = RPMBuild(name=name, env=env, cluster=cluster, domain=domain,
                 use_sudo=use_sudo, s3_bucket=s3_bucket, use_yum=use_yum,
                 ref=git_ref(os.path.join(root, app_dir)))
    r.build_rpm(root, package_dirs)

    if deploy_roles == 'local':
        r.local_install()
    else:
        r.deploy(deploy_roles)
    r.clean()

    return r


def restart_uwsgi(uwsgis, role_list='web'):
    @task
    @roles(role_list)
    def restart_uwsgis():
        for u in uwsgis:
            run('kill -HUP $(supervisorctl pid uwsgi-%s)' % u)
        sleep(2)

    execute(restart_uwsgis)


def scl_enable(name):
    def prepend_env(envname, new):
        if os.environ.get(envname):
            new = ":".join([new, os.environ[envname]])
        os.environ[envname] = new

    prepend_env('PATH', os.path.join('/opt/rh', name, 'root/usr/bin'))
    prepend_env('LD_LIBRARY_PATH',
                os.path.join('/opt/rh', name, 'root/usr/lib64'))
    prepend_env('XDG_DATA_DIRS',
                os.path.join('/opt/rh/', name, 'root/usr/share'))
    prepend_env('PKG_CONFIG_PATH',
                os.path.join('/opt/rh/', name, 'root/usr/lib64/pkgconfig'))
