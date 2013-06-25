from fabric.api import lcd, local, task


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


@task
def create_venv(venv, pyrepo, requirements):
    """venv: directory where venv should be placed"""
    local('virtualenv --distribute --never-download %s' % venv)
    pip_install_reqs(venv, pyrepo, requirements)
    local('rm -f %s/lib/python2.6/no-global-site-packages.txt' % venv)
    local('{0}/bin/python /usr/bin/virtualenv '
          '--relocatable {0}'.format(venv))
