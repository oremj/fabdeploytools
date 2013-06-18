import os

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
        self.ref = ref
        self.install_dir = install_dir

        self.package_prefix = 'deploy-%s-%s' % (self.name, self.env)
        self.package_name = '%s-%s-%s' % (self.package_prefix,
                                          self.build_id, self.ref)
        self.package_filename = os.path.join('/tmp',
                                             '%s.rpm' % self.package_name)

        self.install_to = os.path.join(install_dir, self.package_name)

    def build_rpm(self, project_dir, package_dirs=None):
        """Builds an rpm and returns the filename:
           project_dir: root of package
           package_dirs: which directories inside project_dir will be installed
        """
        if not package_dirs:
            package_dirs = ['.']

        local('fpm -s dir -t rpm -n "%s" '
              '--rpm-compression none '
              '-p "%s" '
              '--directories / '
              '-x "*.git" -x "*.svn" -x "*.pyc" '
              '-C %s --prefix "%s" '
              '%s' % (self.package_name,
                      self.package_filename,
                      project_dir,
                      self.install_to,
                      ' '.join(package_dirs)))

    def install_package(self):
        """installs package on remote hosts. roles or hosts must be set"""
        cur_sym = os.path.join(self.install_dir, 'current')

        put(self.package_filename, self.package_filename)
        run('rpm -i %s' % self.package_filename)
        run('ln -sfn {0} {1}'.format(self.install_to, cur_sym))
        run('rm -f %s' % self.package_filename)

        self.cleanup_packages()

    def cleanup_packages(self, keep=4):
        installed = run('rpm -qa {0}-*'.format(self.package_prefix)).split()
        installed.sort()

        for i in installed[:-keep]:
            if self.build_id not in i:
                run('rpm -e %s' % i)

    def clean(self):
        local('rm -f %s' % self.package_filename)
