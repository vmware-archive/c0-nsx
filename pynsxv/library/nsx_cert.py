
import argparse
import ConfigParser
import json
from libutils import get_logical_switch, get_vdsportgroupid, connect_to_vc, check_for_parameters
from libutils import get_datacentermoid, get_edgeresourcepoolmoid, get_edge, get_datastoremoid, get_networkid
from tabulate import tabulate
from nsxramlclient.client import NsxClient
from argparse import RawTextHelpFormatter
from pkg_resources import resource_filename


def create_self_signed_cert(client_session, scope_id, cert, private_key):
    """
    This function adds an Load Balancer Application profile to an ESG

    :type client_session: nsxramlclient.client.NsxClient
    :param client_session: A nsxramlclient session Object
    :type scope_id: str
    :param scope_id: The display name of a Edge Service Gateway used for Load Balancing
    :type cert: file
    :param cert: Cert file with PEM Encoding
    :type private_key: file
    :param private_key: Private key file
    :return: Returns the Object Id of the newly created Cert, False on a failure, and None if the ESG was
             not found in NSX
    :rtype: str
    """
    esg_id, esg_params = get_edge(client_session, scope_id)
    if not esg_id:
        return None

    cert_dict = client_session.extract_resource_body_example('certificateSelfSigned', 'create')

    cert_dict['trustObject']['pemEncoding'] = cert.read()
    cert_dict['trustObject']['privateKey'] = private_key.read()

    result = client_session.create('certificateSelfSigned', uri_parameters={'scopeId': esg_id},
                                   request_body_dict=cert_dict)
    if result['status'] != 201:
        return None
    else:
        return result['certificate']['objectId']

def _create_self_signed_cert(client_session, **kwargs):
    needed_params = ['scope_id', 'cert', 'private_key']
    if not check_for_parameters(needed_params, kwargs):
        return None

    result = create_self_signed_cert(client_session, kwargs['scope_id'], kwargs['cert'], kwargs['private_key'])

    if result and kwargs['verbose']:
        print result
    elif result:
        print 'Certifcate {} created in scope {}'.format(result, kwargs['scope_id'])
    else:
        print 'Certifcate creation failed in scope {}'.format(kwargs['scope_id'])

def contruct_parser(subparsers):
    parser = subparsers.add_parser('cert', description="Functions for certificates",
                                   help="Functions for certificates",
                                   formatter_class=RawTextHelpFormatter)

    parser.add_argument("command", help="""
    create_self_signed: create a self-signed new cert
    """)

    parser.add_argument("-s",
                        "--scope_id",
                        help="Scope Id")
    parser.add_argument("-c",
                        "--cert",
                        help="PEM Enconded certificate",
                        type=argparse.FileType('r'))
    parser.add_argument("-pk",
                        "--private_key",
                        help="Private key for the certificate",
                        type=argparse.FileType('r'))

    parser.set_defaults(func=_cert_main)


def _cert_main(args):
    if args.debug:
        debug = True
    else:
        debug = False

    config = ConfigParser.ConfigParser()
    assert config.read(args.ini), 'could not read config file {}'.format(args.ini)

    try:
        nsxramlfile = config.get('nsxraml', 'nsxraml_file')
    except (ConfigParser.NoSectionError):
        nsxramlfile_dir = resource_filename(__name__, 'api_spec')
        nsxramlfile = '{}/nsxvapi.raml'.format(nsxramlfile_dir)

    client_session = NsxClient(nsxramlfile, config.get('nsxv', 'nsx_manager'),
                               config.get('nsxv', 'nsx_username'), config.get('nsxv', 'nsx_password'), debug=debug)

    try:
        command_selector = {
            'create_self_signed': _create_self_signed_cert,
            }
        command_selector[args.command](client_session, cert=args.cert, scope_id=args.scope_id,
                                       private_key=args.private_key, verbose=args.verbose)
    except KeyError:
        print('Unknown command')


def main():
    main_parser = argparse.ArgumentParser()
    subparsers = main_parser.add_subparsers()
    contruct_parser(subparsers)
    args = main_parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
