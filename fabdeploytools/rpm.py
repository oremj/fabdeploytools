import os

from fabric.api import local


class RPMBuild:
    def __init__(self, name, env, build_id):
        """
        name: codename of project e.g. "zamboni"
        env: prod, stage, dev, etc
        build_id: typically a unix timestamp
        """
        self.name = name
        self.env = env
        self.build_id = build_id

    def get_package_name(self, ref):
        return 'deploy-%s-%s-%s-%s' % (self.name, self.env,
                                       self.build_id, ref)

    def build_rpm(self, ref, project_dir, install_dir, package_dirs=None):
        """Builds an rpm and returns the filename:
           ref: git ref of project to be packaged
           project_dir: root of package
           install_dir: where package will be installed
           package_dirs: which directories inside project_dir will be installed
        """
        if not package_dirs:
            package_dirs = ['.']

        name = self.get_package_name(ref)
        filename = os.path.join('/tmp', '%s.rpm' % name)
        install_to = os.path.join(install_dir, name)

        local('fpm -s dir -t rpm -n "%s" '
              '--rpm-compression none '
              '-p "%s" '
              '--directories / '
              '-x "*.git" -x "*.svn" -x "*.pyc" '
              '-C %s --prefix "%s" '
              '%s' % (name,
                      filename,
                      project_dir,
                      install_to,
                      ' '.join(package_dirs)))

        return filename
