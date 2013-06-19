import os
from tempfile import NamedTemporaryFile

from fabric.api import local, run, put


class RPMBuild:
    def __init__(self, name, env, ref, build_id, install_dir):
        """
        name: codename of project e.g. "zamboni"
        env: prod, stage, dev, etc
        build_id: typically a unix timestamp
        ref: git ref of project to be packaged
        install_dir: where package will be installed
        """
        self.name = name
        self.env = env
        self.build_id = build_id
        self.ref = ref[:10]
        self.install_dir = install_dir

        self.package_name = 'deploy-%s-%s' % (self.name, self.env)
        full_name = 'deploy-{0.name}-{0.env}-{0.build_id}-{0.ref}'.format(self)
        self.package_filename = os.path.join('/tmp',
                                             '%s.rpm' % full_name)

        self.install_to = os.path.join(install_dir, full_name)

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
