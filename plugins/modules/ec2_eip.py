#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: ec2_eip
version_added: 5.0.0
short_description: manages EC2 elastic IP (EIP) addresses.
description:
  - This module can allocate or release an EIP.
  - This module can associate/disassociate an EIP with instances or network interfaces.
  - This module was originally added to C(community.aws) in release 1.0.0.
options:
  device_id:
    description:
      - The id of the device for the EIP.
      - Can be an EC2 Instance id or Elastic Network Interface (ENI) id.
      - When specifying an ENI id, I(in_vpc) must be C(true)
      - The C(instance_id) alias was removed in release 6.0.0.
    required: false
    type: str
  public_ip:
    description:
      - The IP address of a previously allocated EIP.
      - When I(state=present) and device is specified, the EIP is associated with the device.
      - When I(state=absent) and device is specified, the EIP is disassociated from the device.
    aliases: [ ip ]
    type: str
  state:
    description:
      - When C(state=present), allocate an EIP or associate an existing EIP with a device.
      - When C(state=absent), disassociate the EIP from the device and optionally release it.
    choices: ['present', 'absent']
    default: present
    type: str
  in_vpc:
    description:
      - Allocate an EIP inside a VPC or not.
      - Required if specifying an ENI with I(device_id).
    default: false
    type: bool
  reuse_existing_ip_allowed:
    description:
      - Reuse an EIP that is not associated to a device (when available), instead of allocating a new one.
    default: false
    type: bool
  release_on_disassociation:
    description:
      - Whether or not to automatically release the EIP when it is disassociated.
    default: false
    type: bool
  private_ip_address:
    description:
      - The primary or secondary private IP address to associate with the Elastic IP address.
    type: str
  allow_reassociation:
    description:
      -  Specify this option to allow an Elastic IP address that is already associated with another
         network interface or instance to be re-associated with the specified instance or interface.
    default: false
    type: bool
  tag_name:
    description:
      - When I(reuse_existing_ip_allowed=true), supplement with this option to only reuse
        an Elastic IP if it is tagged with I(tag_name).
    type: str
  tag_value:
    description:
      - Supplements I(tag_name) but also checks that the value of the tag provided in I(tag_name) matches I(tag_value).
    type: str
  public_ipv4_pool:
    description:
      - Allocates the new Elastic IP from the provided public IPv4 pool (BYOIP)
        only applies to newly allocated Elastic IPs, isn't validated when I(reuse_existing_ip_allowed=true).
    type: str
extends_documentation_fragment:
  - amazon.aws.common.modules
  - amazon.aws.region.modules
  - amazon.aws.tags
  - amazon.aws.boto3

author:
  - "Rick Mendes (@rickmendes) <rmendes@illumina.com>"
notes:
  - There may be a delay between the time the EIP is assigned and when
    the cloud instance is reachable via the new address. Use wait_for and
    pause to delay further playbook execution until the instance is reachable,
    if necessary.
  - This module returns multiple changed statuses on disassociation or release.
    It returns an overall status based on any changes occurring. It also returns
    individual changed statuses for disassociation and release.
  - Support for I(tags) and I(purge_tags) was added in release 2.1.0.
"""

EXAMPLES = r"""
# Note: These examples do not set authentication details, see the AWS Guide for details.

- name: associate an elastic IP with an instance
  amazon.aws.ec2_eip:
    device_id: i-1212f003
    ip: 93.184.216.119

- name: associate an elastic IP with a device
  amazon.aws.ec2_eip:
    device_id: eni-c8ad70f3
    ip: 93.184.216.119

- name: associate an elastic IP with a device and allow reassociation
  amazon.aws.ec2_eip:
    device_id: eni-c8ad70f3
    public_ip: 93.184.216.119
    allow_reassociation: true

- name: disassociate an elastic IP from an instance
  amazon.aws.ec2_eip:
    device_id: i-1212f003
    ip: 93.184.216.119
    state: absent

- name: disassociate an elastic IP with a device
  amazon.aws.ec2_eip:
    device_id: eni-c8ad70f3
    ip: 93.184.216.119
    state: absent

- name: allocate a new elastic IP and associate it with an instance
  amazon.aws.ec2_eip:
    device_id: i-1212f003

- name: allocate a new elastic IP without associating it to anything
  amazon.aws.ec2_eip:
    state: present
  register: eip

- name: output the IP
  ansible.builtin.debug:
    msg: "Allocated IP is {{ eip.public_ip }}"

- name: provision new instances with ec2
  amazon.aws.ec2:
    keypair: mykey
    instance_type: c1.medium
    image: ami-40603AD1
    wait: true
    group: webserver
    count: 3
  register: ec2

- name: associate new elastic IPs with each of the instances
  amazon.aws.ec2_eip:
    device_id: "{{ item }}"
  loop: "{{ ec2.instance_ids }}"

- name: allocate a new elastic IP inside a VPC in us-west-2
  amazon.aws.ec2_eip:
    region: us-west-2
    in_vpc: true
  register: eip

- name: output the IP
  ansible.builtin.debug:
    msg: "Allocated IP inside a VPC is {{ eip.public_ip }}"

- name: allocate eip - reuse unallocated ips (if found) with FREE tag
  amazon.aws.ec2_eip:
    region: us-east-1
    in_vpc: true
    reuse_existing_ip_allowed: true
    tag_name: FREE

- name: allocate eip - reuse unallocated ips if tag reserved is nope
  amazon.aws.ec2_eip:
    region: us-east-1
    in_vpc: true
    reuse_existing_ip_allowed: true
    tag_name: reserved
    tag_value: nope

- name: allocate new eip - from servers given ipv4 pool
  amazon.aws.ec2_eip:
    region: us-east-1
    in_vpc: true
    public_ipv4_pool: ipv4pool-ec2-0588c9b75a25d1a02

- name: allocate eip - from a given pool (if no free addresses where dev-servers tag is dynamic)
  amazon.aws.ec2_eip:
    region: us-east-1
    in_vpc: true
    reuse_existing_ip_allowed: true
    tag_name: dev-servers
    public_ipv4_pool: ipv4pool-ec2-0588c9b75a25d1a02

- name: allocate eip from pool - check if tag reserved_for exists and value is our hostname
  amazon.aws.ec2_eip:
    region: us-east-1
    in_vpc: true
    reuse_existing_ip_allowed: true
    tag_name: reserved_for
    tag_value: "{{ inventory_hostname }}"
    public_ipv4_pool: ipv4pool-ec2-0588c9b75a25d1a02
"""

RETURN = r"""
allocation_id:
  description: allocation_id of the elastic ip
  returned: on success
  type: str
  sample: eipalloc-51aa3a6c
public_ip:
  description: an elastic ip address
  returned: on success
  type: str
  sample: 52.88.159.209
"""

from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from ansible_collections.amazon.aws.plugins.module_utils.ec2 import AnsibleEC2Error
from ansible_collections.amazon.aws.plugins.module_utils.ec2 import allocate_address as allocate_ip_address
from ansible_collections.amazon.aws.plugins.module_utils.ec2 import associate_address
from ansible_collections.amazon.aws.plugins.module_utils.ec2 import describe_addresses
from ansible_collections.amazon.aws.plugins.module_utils.ec2 import describe_instances
from ansible_collections.amazon.aws.plugins.module_utils.ec2 import describe_network_interfaces
from ansible_collections.amazon.aws.plugins.module_utils.ec2 import disassociate_address
from ansible_collections.amazon.aws.plugins.module_utils.ec2 import ensure_ec2_tags
from ansible_collections.amazon.aws.plugins.module_utils.ec2 import release_address
from ansible_collections.amazon.aws.plugins.module_utils.modules import AnsibleAWSModule
from ansible_collections.amazon.aws.plugins.module_utils.tagging import boto3_tag_specifications
from ansible_collections.amazon.aws.plugins.module_utils.transformation import ansible_dict_to_boto3_filter_list


class EipError(Exception):
    pass


def associate_ip_and_device(
    ec2,
    module: AnsibleAWSModule,
    address: Optional[Dict[str, str]],
    private_ip_address: Optional[str],
    device_id: str,
    allow_reassociation: bool,
    is_instance: bool = True,
) -> bool:
    if address_is_associated_with_device(ec2, module, address, device_id, is_instance):
        return False

    # If we're in check mode, nothing else to do
    if not module.check_mode:
        if is_instance:
            try:
                params = dict(
                    InstanceId=device_id,
                    AllowReassociation=allow_reassociation,
                )
                if private_ip_address:
                    params["PrivateIpAddress"] = private_ip_address
                if (address or {}).get("Domain") == "vpc":
                    params["AllocationId"] = (address or {}).get("AllocationId")
                else:
                    params["PublicIp"] = (address or {}).get("PublicIp")
                res = associate_address(ec2, **params)
            except AnsibleEC2Error as e:
                msg = f"Couldn't associate Elastic IP address with instance '{device_id}'"
                module.fail_json_aws(e, msg=msg)
        else:
            params = dict(
                NetworkInterfaceId=device_id,
                AllocationId=(address or {}).get("AllocationId"),
                AllowReassociation=allow_reassociation,
            )

            if private_ip_address:
                params["PrivateIpAddress"] = private_ip_address

            try:
                res = associate_address(ec2, **params)
            except AnsibleEC2Error as e:
                msg = f"Couldn't associate Elastic IP address with network interface '{device_id}'"
                module.fail_json_aws(e, msg=msg)
        if not res:
            module.fail_json(msg="Association failed.")

    return True


def disassociate_ip_and_device(
    ec2,
    module: AnsibleAWSModule,
    address: Optional[Dict[str, Union[str, List[Dict[str, str]]]]],
    device_id: str,
    is_instance: bool = True,
) -> bool:
    if not address_is_associated_with_device(ec2, module, address, device_id, is_instance):
        return False

    # If we're in check mode, nothing else to do
    if not module.check_mode:
        try:
            if (address or {}).get("Domain") == "vpc":
                disassociate_address(ec2, association_id=(address or {}).get("AssociationId"))
            else:
                # TODO: fix this, 'PublicIP' argument has been deprecated for function 'disassociate_address'
                disassociate_address(ec2, public_ip=(address or {}).get("PublicIp"))
        except AnsibleEC2Error as e:
            module.fail_json_aws(e, msg="Dissassociation of Elastic IP failed")

    return True


def find_address(
    ec2, module: AnsibleAWSModule, public_ip: Optional[str], device_id: Optional[str], is_instance: bool = True
) -> Optional[Dict[str, Union[str, List[Dict[str, str]]]]]:
    """Find an existing Elastic IP address"""
    filters = None
    kwargs = {}

    if public_ip:
        kwargs["PublicIps"] = [public_ip]
    elif device_id:
        if is_instance:
            filters = [{"Name": "instance-id", "Values": [device_id]}]
        else:
            filters = [{"Name": "network-interface-id", "Values": [device_id]}]

    if filters:
        kwargs["Filters"] = filters
    elif not filters and public_ip is None:
        return None

    try:
        addresses = describe_addresses(ec2, **kwargs)
        if not addresses:
            if module.params.get("state") == "absent":
                module.exit_json(changed=False, disassociated=False, released=False)
            return None
    except AnsibleEC2Error as e:
        module.fail_json_aws(e, msg="Couldn't obtain list of existing Elastic IP addresses")

    if len(addresses) == 1:
        return addresses[0]
    elif len(addresses) > 1:
        msg = f"Found more than one address using args {kwargs} Addresses found: {addresses}"
        module.fail_json(msg=msg)
    return None


def address_is_associated_with_device(
    ec2,
    module: AnsibleAWSModule,
    address: Optional[Dict[str, str]],
    device_id: str,
    is_instance: bool = True,
) -> bool:
    """Check if the elastic IP is currently associated with the device"""
    result = find_address(ec2, module, (address or {}).get("PublicIp"), device_id, is_instance)
    if result:
        if is_instance and result.get("InstanceId", False) == device_id:
            return True
        if not is_instance and result.get("NetworkInterfaceId", False) == device_id:
            return True
    return False


def allocate_address(
    ec2,
    module,
    domain,
    reuse_existing_ip_allowed,
    check_mode,
    tags,
    search_tags=None,
    public_ipv4_pool=None,
):
    """Allocate a new elastic IP address (when needed) and return it"""
    if not domain:
        domain = "standard"

    if reuse_existing_ip_allowed:
        filters = []
        filters.append({"Name": "domain", "Values": [domain]})

        if search_tags is not None:
            filters += ansible_dict_to_boto3_filter_list(search_tags)

        try:
            all_addresses = describe_addresses(ec2, Filters=filters)
        except AnsibleEC2Error as e:
            module.fail_json_aws(e, msg="Couldn't obtain list of existing Elastic IP addresses")

        if domain == "vpc":
            unassociated_addresses = [a for a in all_addresses if not a.get("AssociationId", None)]
        else:
            unassociated_addresses = [a for a in all_addresses if not a["InstanceId"]]
        if unassociated_addresses:
            return unassociated_addresses[0], False

    if public_ipv4_pool:
        return (
            allocate_address_from_pool(
                ec2,
                module,
                domain,
                check_mode,
                public_ipv4_pool,
                tags,
            ),
            True,
        )

    params = {"Domain": domain}
    if tags:
        params["TagSpecifications"] = boto3_tag_specifications(tags, types="elastic-ip")

    changed = True
    result = None
    try:
        if not check_mode:
            result = allocate_ip_address(ec2, **params)
    except AnsibleEC2Error as e:
        module.fail_json_aws(e, msg="Couldn't allocate Elastic IP address")
    return result, changed


def release_ip_address(ec2, module, address):
    """Release a previously allocated elastic IP address"""

    # If we're in check mode, nothing else to do
    changed = True
    if not module.check_mode:
        try:
            changed = release_address(ec2, allocation_id=address["AllocationId"])
        except AnsibleEC2Error as e:
            module.fail_json_aws(e, msg="Couldn't release Elastic IP address")

    return changed


def find_device(ec2, module: AnsibleAWSModule, device_id: str, is_instance: bool = True) -> Optional[Dict[str, Any]]:
    """Attempt to find the EC2 instance and return it"""

    result = None
    if is_instance:
        try:
            reservations = describe_instances(ec2, InstanceIds=[device_id])
        except AnsibleEC2Error as e:
            module.fail_json_aws(e, msg="Couldn't get list of instances")

        if len(reservations) == 1:
            instances = reservations[0]["Instances"]
            if len(instances) == 1:
                result = instances[0]
    else:
        try:
            interfaces = describe_network_interfaces(ec2, NetworkInterfaceIds=[device_id])
        except AnsibleEC2Error as e:
            module.fail_json_aws(e, msg="Couldn't get list of network interfaces.")
        if len(interfaces) == 1:
            result = interfaces[0]
    return result


def ensure_present(
    ec2,
    module,
    domain,
    address,
    private_ip_address,
    device_id,
    reuse_existing_ip_allowed,
    allow_reassociation,
    check_mode,
    tags,
    is_instance=True,
):
    changed = False

    # Return the EIP object since we've been given a public IP
    if not address:
        if check_mode:
            return {"changed": True}

        address, changed = allocate_address(
            ec2,
            module,
            domain,
            reuse_existing_ip_allowed,
            check_mode,
            tags,
        )

    if device_id:
        # Allocate an IP for instance since no public_ip was provided
        if is_instance:
            instance = find_device(ec2, module, device_id)
            if reuse_existing_ip_allowed:
                if instance["VpcId"] and len(instance["VpcId"]) > 0 and domain is None:
                    msg = "You must set 'in_vpc' to true to associate an instance with an existing ip in a vpc"
                    module.fail_json(msg=msg)

            # Associate address object (provided or allocated) with instance
            changed |= associate_ip_and_device(ec2, module, address, private_ip_address, device_id, allow_reassociation)
        else:
            instance = find_device(ec2, module, device_id, is_instance=False)
            # Associate address object (provided or allocated) with instance
            changed |= associate_ip_and_device(
                ec2, module, address, private_ip_address, device_id, allow_reassociation, is_instance=False
            )

    return {"changed": changed, "public_ip": address["PublicIp"], "allocation_id": address["AllocationId"]}


def ensure_absent(ec2, module: AnsibleAWSModule, address, device_id, is_instance=True) -> bool:
    if not address:
        return False

    # disassociating address from instance
    if device_id:
        if is_instance:
            return disassociate_ip_and_device(ec2, module, address, device_id)
        else:
            return disassociate_ip_and_device(ec2, module, address, device_id, is_instance=False)
    # releasing address
    else:
        return release_ip_address(ec2, module, address)


def allocate_address_from_pool(
    ec2,
    module,
    domain,
    check_mode,
    public_ipv4_pool,
    tags,
):
    # type: (Any, AnsibleAWSModule, str, bool, str, Dict) -> Optional[Dict]
    """Overrides botocore's allocate_address function to support BYOIP"""
    if check_mode:
        return None

    params = {}

    if domain is not None:
        params["Domain"] = domain

    if public_ipv4_pool is not None:
        params["PublicIpv4Pool"] = public_ipv4_pool

    if tags:
        params["TagSpecifications"] = boto3_tag_specifications(tags, types="elastic-ip")

    try:
        result = allocate_ip_address(ec2, **params)
    except AnsibleEC2Error as e:
        module.fail_json_aws(e, msg="Couldn't allocate Elastic IP address")
    return result


def generate_tag_dict(module, tag_name, tag_value):
    # type: (AnsibleAWSModule, str, str) -> Optional[Dict]
    """Generates a dictionary to be passed as a filter to Amazon"""
    result = None
    if tag_name and not tag_value:
        if tag_name.startswith("tag:"):
            tag_name = tag_name.strip("tag:")
        result = {"tag-key": tag_name}

    elif tag_name and tag_value:
        if not tag_name.startswith("tag:"):
            tag_name = "tag:" + tag_name
        result = {tag_name: tag_value}

    elif tag_value and not tag_name:
        module.fail_json(msg="parameters are required together: ('tag_name', 'tag_value')")

    return result


def check_is_instance(device_id, in_vpc):
    if not device_id:
        return False
    if device_id.startswith("i-"):
        return True

    if device_id.startswith("eni-") and not in_vpc:
        raise EipError("If you are specifying an ENI, in_vpc must be true")

    return False


def main():
    argument_spec = dict(
        device_id=dict(required=False),
        public_ip=dict(required=False, aliases=["ip"]),
        state=dict(required=False, default="present", choices=["present", "absent"]),
        in_vpc=dict(required=False, type="bool", default=False),
        reuse_existing_ip_allowed=dict(required=False, type="bool", default=False),
        release_on_disassociation=dict(required=False, type="bool", default=False),
        allow_reassociation=dict(type="bool", default=False),
        private_ip_address=dict(),
        tags=dict(required=False, type="dict", aliases=["resource_tags"]),
        purge_tags=dict(required=False, type="bool", default=True),
        tag_name=dict(),
        tag_value=dict(),
        public_ipv4_pool=dict(),
    )

    module = AnsibleAWSModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_by={
            "private_ip_address": ["device_id"],
        },
    )

    ec2 = module.client("ec2")

    device_id = module.params.get("device_id")
    public_ip = module.params.get("public_ip")
    private_ip_address = module.params.get("private_ip_address")
    state = module.params.get("state")
    in_vpc = module.params.get("in_vpc")
    domain = "vpc" if in_vpc else None
    reuse_existing_ip_allowed = module.params.get("reuse_existing_ip_allowed")
    release_on_disassociation = module.params.get("release_on_disassociation")
    allow_reassociation = module.params.get("allow_reassociation")
    tag_name = module.params.get("tag_name")
    tag_value = module.params.get("tag_value")
    public_ipv4_pool = module.params.get("public_ipv4_pool")
    tags = module.params.get("tags")
    purge_tags = module.params.get("purge_tags")

    try:
        is_instance = check_is_instance(device_id, in_vpc)
    except EipError as e:
        module.fail_json(msg=str(e))

    # Tags for *searching* for an EIP.
    search_tags = generate_tag_dict(module, tag_name, tag_value)

    try:
        if device_id:
            address = find_address(ec2, module, public_ip, device_id, is_instance=is_instance)
        else:
            address = find_address(ec2, module, public_ip, None)

        if state == "present":
            if device_id:
                result = ensure_present(
                    ec2,
                    module,
                    domain,
                    address,
                    private_ip_address,
                    device_id,
                    reuse_existing_ip_allowed,
                    allow_reassociation,
                    module.check_mode,
                    tags,
                    is_instance=is_instance,
                )
                if "allocation_id" not in result:
                    # Don't check tags on check_mode here - no EIP to pass through
                    module.exit_json(**result)
            else:
                if address:
                    result = {
                        "changed": False,
                        "public_ip": address["PublicIp"],
                        "allocation_id": address["AllocationId"],
                    }
                else:
                    address, changed = allocate_address(
                        ec2,
                        module,
                        domain,
                        reuse_existing_ip_allowed,
                        module.check_mode,
                        tags,
                        search_tags,
                        public_ipv4_pool,
                    )
                    if address:
                        result = {
                            "changed": changed,
                            "public_ip": address["PublicIp"],
                            "allocation_id": address["AllocationId"],
                        }
                    else:
                        # Don't check tags on check_mode here - no EIP to pass through
                        result = {"changed": changed}
                        module.exit_json(**result)

            result["changed"] |= ensure_ec2_tags(
                ec2, module, result["allocation_id"], resource_type="elastic-ip", tags=tags, purge_tags=purge_tags
            )
        else:
            if device_id:
                disassociated = ensure_absent(ec2, module, address, device_id, is_instance=is_instance)

                if release_on_disassociation and disassociated:
                    changed = release_ip_address(ec2, module, address)
                    result = {
                        "changed": True,
                        "disassociated": disassociated,
                        "released": changed,
                    }
                else:
                    result = {
                        "changed": disassociated,
                        "disassociated": disassociated,
                        "released": False,
                    }
            else:
                changed = release_ip_address(ec2, module, address)
                result = {"changed": changed, "disassociated": False, "released": changed}

    except AnsibleEC2Error as e:
        module.fail_json_aws_error(e)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
