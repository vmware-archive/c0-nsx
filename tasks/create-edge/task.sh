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
alias pynsxv_local="python pynsxv/cli.py"

LABWIRES="labwire-proto-01 labwire-proto-02"


for labwire in $LABWIRES; do
  pynsxv_local lswitch -n $labwire create
done

pynsxv_local esg create -n $NSX_EDGE_GEN_NAME -pg "$ESG_DEFAULT_UPLINK_PG_1"

pynsxv_local esg cfg_interface -n $NSX_EDGE_GEN_NAME --portgroup "$ESG_DEFAULT_UPLINK_PG_1" \
  --vnic_index 0 --vnic_type uplink --vnic_name "External" \
  --vnic_ip 10.193.99.170 --vnic_mask 255.255.255.0

pynsxv_local esg cfg_interface -n $NSX_EDGE_GEN_NAME --logical_switch my-test-switch \
  --vnic_index 1 --vnic_type internal --vnic_name transit \
  --vnic_ip 192.168.10.1 --vnic_mask 255.255.255.0

# Configure firewall + default gw + static route
pynsxv_local esg set_fw_status -n $NSX_EDGE_GEN_NAME --fw_default accept

pynsxv_local esg set_dgw -n $NSX_EDGE_GEN_NAME --next_hop $ESG_DEFAULT_UPLINK_PG_1

pynsxv_local esg add_route -n $NSX_EDGE_GEN_NAME --route_net 10.1.0.0/22 --next_hop 172.16.1.2

# Enable load balancing
pynsxv_local lb enable_lb -n $NSX_EDGE_GEN_NAME
# Create lb app profile

pynsxv_local lb add_profile -n $NSX_EDGE_GEN_NAME --profile_name appprofile --protocol HTTP

# create lb pool
pynsxv_local lb add_pool -n $NSX_EDGE_GEN_NAME --pool_name pool_web --transparent true

# create lb vip
pynsxv_local esg cfg_interface -n $NSX_EDGE_GEN_NAME --vnic_index 0 --vnic_ip 20.20.20.2 --vnic_mask 255.255.255.0 --vnic_secondary_ips 20.20.20.6

pynsxv_local lb add_vip -n $NSX_EDGE_GEN_NAME --vip_name vip_app --pool_name pool_app --profile_name appprofile --vip_ip 172.16.1.6 --protocol HTTP --port 80
