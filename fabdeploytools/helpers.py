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
