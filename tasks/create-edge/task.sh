#!/bin/bash -eux

echo "Creating edge"

cat << EOF > pynsxv/nsx.ini
[nsxv]
nsx_manager = $NSX_EDGE_GEN_NSX_MANAGER_ADDRESS
nsx_username = $NSX_EDGE_GEN_NSX_MANAGER_ADMIN_USER
nsx_password = $NSX_EDGE_GEN_NSX_MANAGER_ADMIN_PASSWD

[vcenter]
vcenter = $VCENTER_HOST
vcenter_user = $VCENTER_USR
vcenter_passwd = $VCENTER_PWD

[defaults]
transport_zone = $NSX_EDGE_GEN_NSX_MANAGER_TRANSPORT_ZONE
datacenter_name = $VCENTER_DATA_CENTER
edge_datastore =  $NSX_EDGE_GEN_EDGE_DATASTORE
edge_cluster = $NSX_EDGE_GEN_EDGE_CLUSTER
EOF

pushd pynsxv

python pynsxv/cli.py lswitch -n my-test-switch create
python pynsxv/cli.py esg create -n my_test_esg -pg "$ESG_DEFAULT_UPLINK_PG_1"
