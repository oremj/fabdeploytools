def get_region():
    from boto.utils import get_instance_identity
    return get_instance_identity()['document']['region']


def connect_to(connector):
    return connector(get_region())


def connect_to_s3():
    from boto.s3 import connect_to_region
    return connect_to(connect_to_region)


def connect_to_ec2():
    from boto.ec2 import connect_to_region
    return connect_to(connect_to_region)
