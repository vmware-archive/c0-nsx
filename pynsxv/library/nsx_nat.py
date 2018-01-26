
import argparse
import ConfigParser
import json
from libutils import get_logical_switch, get_vdsportgroupid, connect_to_vc, check_for_parameters
from libutils import get_datacentermoid, get_edgeresourcepoolmoid, get_edge, get_datastoremoid, get_networkid
from tabulate import tabulate
from nsxramlclient.client import NsxClient
from argparse import RawTextHelpFormatter
from pkg_resources import resource_filename


def add_snat_rule(client_session, esg_name, source, translated_source):
    """
    This function adds an Load Balancer Application profile to an ESG

    :type client_session: nsxramlclient.client.NsxClient
    :param client_session: A nsxramlclient session Object
    :type esg_name: str
    :param esg_name: The display name of a Edge Service Gateway used for Load Balancing
    :type source: str
    :param source: Source IP Address
    :type translated_source: str
    :param translated_source: Translated Source IP Address
    :return: Returns the Object Id of the newly created SNAT Rule and None if the ESG was
             not found in NSX
    :rtype: str
    """
    esg_id, esg_params = get_edge(client_session, esg_name)
    if not esg_id:
        return None

    nat_dict = client_session.extract_resource_body_example('edgeNatRules', 'create')

    del nat_dict['natRule']['dnatMatchSourceAddress']
    del nat_dict['natRule']['translatedPort']
    del nat_dict['natRule']['originalPort']
    del nat_dict['natRule']['dnatMatchSourcePort']

    nat_dict['natRule']['action'] = 'snat'
    nat_dict['natRule']['vnic'] = '0'
    nat_dict['natRule']['protocol'] = 'tcp'
    nat_dict['natRule']['description'] = ''
    nat_dict['natRule']['loggingEnabled'] = 'false'
    nat_dict['natRule']['originalAddress'] = source
    nat_dict['natRule']['translatedAddress'] = translated_source
    nat_dict['natRule']['snatMatchSourceAddress'] = 'any'
    nat_dict['natRule']['snatMatchSourcePort'] = 'any'

    result = client_session.create('edgeNatRules', uri_parameters={'edgeId': esg_id},
                                   request_body_dict=nat_dict)
    if result['status'] != 201:
        return None
    else:
        return result['objectId']

def _add_snat_rule(client_session, **kwargs):
    needed_params = ['esg_name', 'source', 'translated_source']
    if not check_for_parameters(needed_params, kwargs):
        return None

    result = add_snat_rule(client_session, kwargs['esg_name'], kwargs['source'], kwargs['translated_source'])

    if result and kwargs['verbose']:
        print result
    elif result:
        print 'SNAT Rule created for {}'.format(result, kwargs['esg_name'])
    else:
        print 'SNAT Rule creation failed for {}'.format(kwargs['esg_name'])

def contruct_parser(subparsers):
    parser = subparsers.add_parser('nat', description="Functions for NAT",
                                   help="Functions for NAT",
                                   formatter_class=RawTextHelpFormatter)

    parser.add_argument("command", help="""
    add_snat: create a new SNAT Rule
    """)

    parser.add_argument("-n",
                        "--esg_name",
                        help="Edge Name")
    parser.add_argument("-s",
                        "--source",
                        help="Source IP Address")
    parser.add_argument("-ts",
                        "--translated_source",
                        help="Translated Source IP Address")

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
        print 'command is {}'.format(args.command)
        command_selector = {
            'add_snat': _add_snat_rule,
            }
        print command_selector
        command_selector[args.command](client_session, esg_name=args.esg_name, source=args.source,
                                       translated_source=args.translated_source, verbose=args.verbose)
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
