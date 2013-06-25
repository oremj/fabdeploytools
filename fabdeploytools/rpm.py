import os
import time
from tempfile import NamedTemporaryFile

from fabric.api import lcd, local, run, put


class RPMBuild:
    def __init__(self, name, env, ref, build_id=None,
                 install_dir=None, cluster=None, domain=None,
                 http_root=None):
        """
        name: codename of project e.g. "zamboni"
        env: prod, stage, dev, etc
        build_id: typically a unix timestamp
        ref: git ref of project to be packaged
        install_dir: where package will be installed
        cluster, domain: if cluster and domain are present install_dir will
                         be constructed
        http_root: where packages with be hosted. if cluster and domain are
                   defined location will be http_root/$cluster/$domain/$package
        """
        self.name = name
        self.env = env
        self.build_id = build_id if build_id else str(int(time.time()))
        self.ref = ref[:10]
        if install_dir:
            self.install_dir = install_dir
        elif cluster and domain:
            self.install_dir = os.path.join('/data', cluster, 'www', domain)
        else:
            raise Exception('Either install_dir or cluster '
                            'and domain must be defined')

        if cluster and domain and http_root:
            self.http_root = os.path.join(http_root, cluster, domain)
        else:
            self.http_root = http_root

        self.package_name = 'deploy-%s-%s' % (self.name, self.env)
        full_name = 'deploy-{0.name}-{0.env}-{0.build_id}-{0.ref}'.format(self)
        self.package_filename = os.path.join('/tmp',
                                             '%s.rpm' % full_name)

        self.install_to = os.path.join(self.install_dir, full_name)

    def build_rpm(self, project_dir, package_dirs=None):
        """Builds an rpm and returns the filename:
           project_dir: root of package
           package_dirs: which directories inside project_dir will be installed
        """
        if not package_dirs:
            package_dirs = ['.']

        cur_sym = os.path.join(self.install_dir, 'current')

        after_install = NamedTemporaryFile(delete=False)
        after_install.write('ln -sfn {0} {1}'.format(self.install_to, cur_sym))
        after_install.close()

        local('fpm -s dir -t rpm -n "{0.package_name}" '
              '--rpm-compression none '
              '-p "{0.package_filename}" '
              '-v "{0.build_id}" '
              '--iteration "{0.ref}" '
              '--after-install "{3}" '
              '--directories / '
              '-x "*.git" -x "*.svn" -x "*.pyc" '
              '-C {1} --prefix "{0.install_to}" '
              '{2}'.format(self,
                           project_dir,
                           ' '.join(package_dirs),
                           after_install.name))

        os.unlink(after_install.name)

    def install_package(self):
        """installs package on remote hosts. roles or hosts must be set"""

        put(self.package_filename, self.package_filename)
        run('rpm -i %s' % self.package_filename)
        run('rm -f %s' % self.package_filename)

        self.cleanup_packages()

    def cleanup_packages(self, keep=4):
        installed = run('rpm -q {0}'.format(self.package_name)).split()
        installed.sort()

        for i in installed[:-keep]:
            if self.build_id not in i:
                run('rpm -e %s' % i)

    def clean(self):
        local('rm -f %s' % self.package_filename)

    def update_package_server(self, rpm=None):
        """rpm: path to latest rpm"""

        if not self.http_root:
            raise Exception('http_root is not defined.')

        if not rpm:
            rpm = self.package_filename

        if not os.path.isfile(rpm):
            raise Exception('rpm does not exist.')

        latest_sym = os.path.join(self.http_root, 'LATEST')
        prev_sym = os.path.join(self.http_root, 'PREVIOUS')
        package = os.path.join(self.http_root, os.path.basename(rpm))

        with lcd(self.http_root):
            local('mkdir -p %s' % self.http_root)
            local('cp {0} {1}'.format(rpm, package))
            local('[[ -h {0} ]] && '
                  'ln -snf $(readlink {0}) {1}'.format(latest_sym, prev_sym))
            local('ln -snf {0} {1}'.format(package, latest_sym))
