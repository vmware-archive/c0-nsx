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

pynsxv_local() {
  python pynsxv/cli.py "$@"
}

get_cidr() {
  IP=$1
  MASK=$2
  FIRST_THREE=$(echo $IP|cut -d. -f 1,2,3)
  echo "$FIRST_THREE.0/$MASK"
}

# Create logical switches
for labwire_id in $(seq $NUM_LOGICAL_SWITCHES); do
  pynsxv_local lswitch -n "labwire-proto-0$labwire_id" create
done

# Create an edge
pynsxv_local esg create -n $NSX_EDGE_GEN_NAME -pg "$ESG_DEFAULT_UPLINK_PG_1"

# Connect the edge to a backbone
pynsxv_local esg cfg_interface \
  -n $NSX_EDGE_GEN_NAME \
  --portgroup "$ESG_DEFAULT_UPLINK_PG_1" \
  --vnic_index 0 --vnic_type uplink --vnic_name "uplink" \
  --vnic_ip $ESG_DEFAULT_UPLINK_IP_1 --vnic_mask 25 \
  --vnic_secondary_ips $ESG_DEFAULT_UPLINK_SECONDARY_IPS

# Attach logical switches to an edge
subnets=(10 20 24 28 32)
masks=(26 22 22 22 22)
for labwire_id in $(seq $NUM_LOGICAL_SWITCHES); do
  pynsxv_local esg cfg_interface -n $NSX_EDGE_GEN_NAME --logical_switch "labwire-proto-0$labwire_id" \
    --vnic_index $labwire_id --vnic_type internal --vnic_name vnic$labwire_id \
    --vnic_ip "192.168.${subnets[$labwire_id-1]}.1" --vnic_mask "${masks[$labwire_id-1]}"
done

# Configure firewall
pynsxv_local esg set_fw_status -n $NSX_EDGE_GEN_NAME --fw_default accept

pynsxv_local esg routing_ospf -n $NSX_EDGE_GEN_NAME \
  --vnic_ip $ESG_DEFAULT_UPLINK_IP_1 \
  -area 3505 -auth_type md5 -auth_value ospfarea3505


# Enable load balancing
pynsxv_local lb enable_lb -n $NSX_EDGE_GEN_NAME

# Create lb app profile for http
pynsxv_local lb add_profile \
  -n $NSX_EDGE_GEN_NAME \
  --profile_name pcf-http \
  --protocol HTTP \
  -x true

  # Create lb app profile for https
  pynsxv_local lb add_profile \
    -n $NSX_EDGE_GEN_NAME \
    --profile_name pcf-https \
    --protocol HTTPS \
    -x true

  #Add monitor for http
  pynsxv_local lb add_monitor \
    -n $NSX_EDGE_GEN_NAME \
    --mon_name monitor-pcf-http \
    --method GET \
    --url "/health" \
    --protocol HTTP

  #Add monitor for https
  pynsxv_local lb add_monitor \
    -n $NSX_EDGE_GEN_NAME \
    --mon_name monitor-pcf-https \
    --method GET \
    --url "/health" \
    --protocol HTTPS

# create lb pool
pynsxv_local lb add_pool -n $NSX_EDGE_GEN_NAME \
  --pool_name gortr-pool \
  --algorithm round-robin \
  --monitor monitor-pcf-http

# add members to pool
pynsxv_local lb add_member \
  -n $NSX_EDGE_GEN_NAME \
  --pool_name gortr-pool \
  --member_name gortr-100 \
  --member 192.168.20.100 \
  --port 80 \
  --monitor_port 8080 \
  --weight 1

pynsxv_local lb add_member \
  -n $NSX_EDGE_GEN_NAME \
  --pool_name gortr-pool \
  --member_name gortr-101 \
  --member 192.168.20.101 \
  --port 80 \
  --monitor_port 8080 \
  --weight 1

pynsxv_local lb add_member \
  -n $NSX_EDGE_GEN_NAME \
  --pool_name gortr-pool \
  --member_name gortr-102 \
  --member 192.168.20.102 \
  --port 80 \
  --monitor_port 8080 \
  --weight 1

# create app rules
pynsxv_local lb add_rule \
  -n $NSX_EDGE_GEN_NAME \
  -rn "option httplog" \
  -rs "option httplog"

pynsxv_local lb add_rule \
  -n $NSX_EDGE_GEN_NAME \
  -rn "reqadd X-Forwarded-Proto:\ https" \
  -rs "reqadd X-Forwarded-Proto:\ https"

  pynsxv_local lb add_rule \
    -n $NSX_EDGE_GEN_NAME \
    -rn "reqadd X-Forwarded-Proto:\ http" \
    -rs "reqadd X-Forwarded-Proto:\ http"


# create lb vip for http
pynsxv_local lb add_vip \
  -n $NSX_EDGE_GEN_NAME \
  --vip_name gortr-http \
  --pool_name gortr-pool \
  --profile_name pcf-http \
  --vip_ip $ESG_GO_ROUTER_UPLINK_IP_1  \
  --protocol HTTP \
  --port 80

  # create lb vip for https
pynsxv_local lb add_vip \
  -n $NSX_EDGE_GEN_NAME \
  --vip_name gortr-https \
  --pool_name gortr-pool \
  --profile_name pcf-https \
  --vip_ip $ESG_GO_ROUTER_UPLINK_IP_1  \
  --protocol HTTPS \
  --port 443
