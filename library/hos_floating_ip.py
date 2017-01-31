#!/usr/bin/python

from ansible.module_utils.basic import *
import json
import os_client_config
import fcntl

# Yes I know, global variables are evil, but non-working APIs such as shade
# aren't angels either ...
module = None
compute_client = None
network_client = None

def main():
  global module
  global compute_client
  global network_client

  compute_client = os_client_config.make_client("compute")
  network_client = os_client_config.make_client("network")
  fields = {
    "server": {"required": True, "type": "str"},
    "fixed_address": {"type": "str"},
    "state": {
      "default": "present",
      "choices": ["present", "absent"],
      "type": "str"
    },
    "network": {"required": True, "type": "str"},
    "reuse": { "default": True, "type": "bool" }
  }
  module = AnsibleModule(argument_spec=fields)
  server = module.params["server"]
  fixed_address = module.params["fixed_address"]
  lock_file = open("/tmp/hos_lock", 'w')
  fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
  if not fixed_address:
    fixed_address = nova_get_server_fixed_address(server)
  network = module.params["network"]
  reuse = module.params["reuse"]
  state = module.params["state"]

  curr_ips = neutron_list_floating_ips()
  fl = [ r for r in curr_ips if r["fixed_ip_address"] == fixed_address ]
  if state == "absent":
    ensure_not_linked(fl)
  else:
    available_ips = [ r for r in curr_ips if not r["fixed_ip_address"] ]
    ensure_linked(fl, available_ips, fixed_address, network, reuse)
  lock_file.close()

def ensure_not_linked(matching_ips):
  global module
  if len(matching_ips) > 0:
    f = matching_ips[0]
    neutron_disassociate_floating_ip(f["id"])
    module.exit_json(changed=True, address_info={})
  else:
    module.exit_json(changed=False, address_info={})

def ensure_linked(matching_ips, available_ips, fixed_address, network, reuse):
  global module
  if len(matching_ips) > 0:
    f = matching_ips[0]
    module.exit_json(changed=False, address_info=f)
  else:
    # Pick up an available floating IP in the list or allocate a new one
    if reuse and len(available_ips) > 0:
      f = available_ips[0]
    else:
      f = neutron_allocate_floating_ip(network)
    # Now associate the chosen floating IP
    neutron_associate_floating_ip(f["id"], neutron_port_id(fixed_address))
    module.exit_json(changed=True, address_info=f)

def neutron_list_floating_ips():
  global module
  global network_client
  try:
    return network_client.list_floatingips()["floatingips"]
  except Exception as e:
    module.fail_json(msg=e)

def neutron_allocate_floating_ip(network):
  global module
  global network_client

  try:
    network_client.create_floatingip(
      { "floatingip": {"floating_network_id": neutron_network_id(network)} })
  except Exception as e:
    module.fail_json(msg=e)

def neutron_network_id(name):
  """
  Query neutron for all existing networks and return the id of the one matching
  the provided name
  """
  global module
  global network_client

  try:
    networks = network_client.list_networks()["networks"]
    mn = [ n["id"] for n in networks if n["name"] == name ]
    if len(mn) == 1:
      return mn[0]
    else:
      module.fail_json(msg="Can't find single network for " + name)
  except Exception as e:
    module.fail_json(msg=e)

def neutron_port_id(fixed_address):
  """
  Query neutron for all existing ports and return the id of the one matching
  the provided fixed IP address
  """
  global module
  global network_client

  try:
    ports = network_client.list_ports()["ports"]
    p = [ r["id"] for r in ports
            if any(s for s in r["fixed_ips"] if s["ip_address"] == fixed_address) ]
    if len(p) == 1:
      return p[0]
    else:
      module.fail_json(msg="Can't find single port for " + fixed_address)
  except Exception as e:
    module.fail_json(msg=e)

def neutron_associate_floating_ip(floating_ip_id, port_id):
  global module
  global network_client

  try:
    network_client.update_floatingip(
      floating_ip_id,
      { "floatingip": { "port_id": port_id} })
  except Exception as e:
    module.fail_json(msg=e)

def neutron_disassociate_floating_ip(floating_ip_id):
  global module
  global network_client

  try:
    network_client.update_floatingip({ "floatingip": {"id": floating_ip_id} })
  except Exception as e:
    module.fail_json(msg=e)

def nova_associate_floating_ip(floating_ip, server):
  import subprocess
  global module
  cmd = ["nova", "floating-ip-associate", server, floating_ip]
  p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  out,err = p.communicate()
  if err != "":
    module.fail_json(msg=err)

def nova_get_server_fixed_address(server):
  global module
  global compute_client

  try:
    s = compute_client.servers.find(name=server)
    fixed_addresses = []
    for n,p in s.addresses.items():
      fixed_addresses.extend([a["addr"] for a in p if a["OS-EXT-IPS:type"] == "fixed"])
    if len(fixed_addresses) > 0:
      return fixed_addresses[0]
    else:
      module.fail_json(msg="Could not find a fixed address for server " + server)
  except Exception as inst:
    module.fail_json("Could not find server " + server)

if __name__ == "__main__":
  main()

