# WORKFLOW

### TODO: A LOT HAVE CHANGED

## Check phase

### Not checked for a reason

1. Have all the required privileges
    Can't tell unleses they offer read access to some IAM resources 

### Checks

1. Authenticates as the identity (Role or Cred)
2. Both subnet are in their CIDRs respectively
3. No conflict between routed CIDRs
4. SG belongs to the same VPC as subnet
5. EIP are not attached, belongs to VPC in the same region


## AWS Provisioning

### Programmatic Calls

1. Allocate EIP on both sides if needed
2. Create Route Tables on both sides if needed
3. Create Security Groups on both sides if needed
4. Launch EC2 instance with 

### EC2::UserData

1. run `yum update -y`
2. install openswan
4. Push config to `conn-to-server.conf` and `conn-to-client` under /etc/ipsec.d/

## Login and run

Login to both servers

### IPSec

1. Push password to both sides under /etc/ipsec.d
2. Enable ipsec.d inclusion with `sed -i 's/^#include \/etc\/ipsec.d\//include \/etc\/ipsec.d\//' /etc/ipsec.conf`
3. `chkconfig ipsec on` on both sides
4. `service ipsec start` on both sides

### Kernel settings

1. Run the following snipped to enable ip forwarding on both sides
`sed -i "s@net.ipv4.ip_forward = 0@net.ipv4.ip_forward = 1\nnet.ipv4.conf.all.accept_redirects = 0\nnet.ipv4.conf.all.send_redirects = 0@" /etc/sysctl.conf`
2. Run `service network restart`

### NAT

1. turn on SNAT on server by running
`iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE`
2. If DNAT is required, run in client (local IP and ports)
`iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 80 -j DNAT --to-destination 10.0.1.51:80`
3. Write config to /etc/iptables-config

## Lastly

1. Enforce destination IP's on server SG
2. Delete temporary ssh private key
3. Restart ipsec service a few times
3. logout from system
4. Remove SSH from SG's

