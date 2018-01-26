
import argparse
import ConfigParser
import json
from libutils import get_logical_switch, get_vdsportgroupid, connect_to_vc, check_for_parameters
from libutils import get_datacentermoid, get_edgeresourcepoolmoid, get_edge, get_datastoremoid, get_networkid
from tabulate import tabulate
from nsxramlclient.client import NsxClient
from argparse import RawTextHelpFormatter
from pkg_resources import resource_filename


def add_nat_rule(client_session, esg_name, nat_type, original_ip, translated_ip):
    """
    This function adds an Load Balancer Application profile to an ESG

    :type client_session: nsxramlclient.client.NsxClient
    :param client_session: A nsxramlclient session Object
    :type esg_name: str
    :param esg_name: The display name of a Edge Service Gateway used for Load Balancing
    :type original_ip: str
    :param original_ip: Original IP Address
    :type translated_ip: str
    :param translated_ip: Translated IP Address
    :return: Returns the Object Id of the newly created NAT Rule and None if the ESG was
             not found in NSX
    :rtype: str
    """
    esg_id, esg_params = get_edge(client_session, esg_name)
    if not esg_id:
        return None

    nat_dict = client_session.extract_resource_body_example('edgeNatRules', 'create')
    #{'natRules': {'natRule': {'vnic': None, 'protocol': None, 'description': None,
    #'loggingEnabled': None, 'translatedAddress': None, 'enabled': None, 'originalAddress': None,
    #'translatedPort': None, 'action': None, 'originalPort': None}}}
    del nat_dict['natRules']['natRule']['translatedPort']
    del nat_dict['natRules']['natRule']['originalPort']

    nat_dict['natRules']['natRule']['vnic'] = '0'
    nat_dict['natRules']['natRule']['protocol'] = 'tcp'
    nat_dict['natRules']['natRule']['description'] = ''
    nat_dict['natRules']['natRule']['loggingEnabled'] = 'false'
    nat_dict['natRules']['natRule']['translatedAddress'] = translated_ip
    nat_dict['natRules']['natRule']['enabled'] = 'true'
    nat_dict['natRules']['natRule']['originalAddress'] = original_ip
    nat_dict['natRules']['natRule']['action'] = nat_type

    result = client_session.create('edgeNatRules', uri_parameters={'edgeId': esg_id},
                                   request_body_dict=nat_dict)
    if result['status'] != 201:
        return None
    else:
        print result
        return result['objectId']

def _add_nat_rule(client_session, **kwargs):
    needed_params = ['esg_name', 'nat_type', 'original_ip', 'translated_ip']
    if not check_for_parameters(needed_params, kwargs):
        return None

    result = add_nat_rule(client_session, kwargs['esg_name'], kwargs['nat_type'], kwargs['original_ip'], kwargs['translated_ip'])

    if result and kwargs['verbose']:
        print result
    elif result:
        print 'NAT Rule created for {}'.format(result, kwargs['esg_name'])
    else:
        print 'NAT Rule creation failed for {}'.format(kwargs['esg_name'])

def contruct_parser(subparsers):
    parser = subparsers.add_parser('nat', description="Functions for NAT",
                                   help="Functions for NAT",
                                   formatter_class=RawTextHelpFormatter)

    parser.add_argument("command", help="""
    add_nat: create a new NAT Rule
    """)

    parser.add_argument("-n",
                        "--esg_name",
                        help="Edge Name")
    parser.add_argument("-t",
                        "--nat_type",
                        help="Type of NAT Rule (SNAT or DNAT)")
    parser.add_argument("-o",
                        "--original_ip",
                        help="Original IP Address")
    parser.add_argument("-tip",
                        "--translated_ip",
                        help="Translated IP Address")

    parser.set_defaults(func=_nat_main)


def _nat_main(args):
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
            'add_nat': _add_nat_rule,
            }
        command_selector[args.command](client_session, esg_name=args.esg_name, original_ip=args.original_ip,
                                       translated_ip=args.translated_ip, verbose=args.verbose, nat_type=args.nat_type)
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
