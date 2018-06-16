import base64
import enum
import ipaddress
import json
import logging

import yaml
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_ssh_public_key
from schematics import Model
from schematics.exceptions import ConversionError, ValidationError
from schematics.types import StringType, BaseType
from schematics.types.compound import ModelType, ListType, DictType

from vmw_cloudinit_metadata.vspc.async_telnet import CR


class IPv4AddressType(BaseType):
    def __init__(self, allow_reserved=False, **kwargs):
        super().__init__(**kwargs)
        self.allow_reserved = allow_reserved

    def to_native(self, value, context=None):
        if not isinstance(value, ipaddress.IPv4Address):
            try:
                value = ipaddress.IPv4Address(value)
            except ValueError as e:
                raise ConversionError(e.__str__())

        if value.is_multicast:
            raise ConversionError("Cannot use a multicast (RFC 3171) IPv4 Address")

        if value.is_unspecified:
            raise ConversionError("Cannot use an unspecified (RFC 5735) IPv4 Address")

        if self.allow_reserved is False and value.is_reserved:
            raise ConversionError("Cannot use a reserved (IETF reserved) IPv4 Address")

        if value.is_loopback:
            raise ConversionError("Cannot use a loopback (RFC 3330) IPv4 Address")

        if value.is_link_local:
            raise ConversionError("Cannot use a link local (RFC 3927) IPv4 Address")

        return value

    def to_primitive(self, value, context=None):
        return str(value)


class InstanceMetadata(Model):
    ami_id = StringType(required=True)
    instance_id = StringType(required=True)
    region = StringType(required=True)
    availability_zone = StringType(required=True)
    tags = DictType(StringType, default=dict)
    public_keys = ListType(StringType, default=list)
    hostname = StringType(required=True)

    def validate_public_keys(self, data, value):
        for key in value:
            try:
                load_ssh_public_key(key.encode(), default_backend())
            except ValueError:
                raise ValidationError("public_key could not be decoded or is not in the proper format")
            except UnsupportedAlgorithm:
                raise ValidationError("public_key serialization type is not supported")

        return value


class InstanceNetworkData(Model):
    address = IPv4AddressType(required=True)
    netmask = IPv4AddressType(allow_reserved=True, required=True)
    gateway = IPv4AddressType(required=True)
    search = ListType(StringType, default=list)
    nameservers = ListType(IPv4AddressType, required=True, min_size=1)


class InstanceData(Model):
    metadata = ModelType(InstanceMetadata, required=True)
    network = ModelType(InstanceNetworkData, required=True)
    userdata = StringType(default="#cloud-config\n{}")


class PacketCode(enum.Enum):
    # Incoming packets
    REQUEST_METADATA = 'REQUEST_METADATA'
    REQUEST_NETWORKDATA = 'REQUEST_NETWORKDATA'
    REQUEST_USERDATA = 'REQUEST_USERDATA'
    # Outgoing packets
    RESPONSE_METADATA = 'RESPONSE_METADATA'
    RESPONSE_NETWORKDATA = 'RESPONSE_NETWORKDATA'
    RESPONSE_USERDATA = 'RESPONSE_USERDATA'


class VMClient(object):

    def __init__(self, vm_name, writer, driver):
        self.logger = logging.getLogger("%s.%s" % (self.__module__, self.__class__.__name__))
        self.vm_name = vm_name
        self.vm_bios_uuid = None
        self.vm_vc_uuid = None
        self.writer = writer
        self.driver = driver

    async def write_metadata(self):

        instance_data: InstanceData = self.driver.get_instance(self)
        if instance_data is None:
            return
        instance_metadata: InstanceMetadata = instance_data.metadata

        metadata = {
            'ami-id': instance_metadata.ami_id,
            'instance-id': instance_metadata.instance_id,
            'region': instance_metadata.region,
            'availability-zone': instance_metadata.availability_zone,
            'tags': instance_metadata.tags,
            'public-keys': instance_metadata.public_keys,
            'hostname': instance_metadata.hostname,
            'local-hostname': instance_metadata.hostname,
        }

        await self.write(PacketCode.RESPONSE_METADATA, json.dumps(metadata))

    async def write_userdata(self):
        instance_data: InstanceData = self.driver.get_instance(self)
        if instance_data is None:
            return

        userdata: str = instance_data.userdata
        userdata = userdata.lstrip().rstrip()

        await self.write(PacketCode.RESPONSE_USERDATA, userdata)

    async def write_networkdata(self):
        instance_data: InstanceData = self.driver.get_instance(self)
        if instance_data is None:
            return
        instance_network: InstanceNetworkData = instance_data.network

        nameservers = []
        for s in instance_network.nameservers:
            nameservers.append(str(s))

        networkdata = {
            'version': 1,
            'config': [
                {
                    "type": "physical",
                    "name": "eth0",
                    "subnets": [
                        {
                            "type": "static",
                            "address": str(instance_network.address),
                            "netmask": str(instance_network.netmask),
                            "gateway": str(instance_network.gateway),
                            "dns_search": instance_network.search,
                            "dns_nameservers": nameservers
                        }
                    ]
                }
            ]
        }

        await self.write(PacketCode.RESPONSE_NETWORKDATA, yaml.safe_dump(networkdata, default_flow_style=False))

    async def write(self, packet_code, data):
        b64data = base64.b64encode(data.encode()).decode('ascii')
        packet_data = "!!" + packet_code.value + "#" + b64data + '\n'
        self.writer.write(packet_data.encode() + CR)
        await self.writer.drain()

    async def process_packets(self, packet_code, data):
        try:
            packet_code = PacketCode(packet_code)
        except ValueError:
            self.logger.error("Received unknown packet code '%s' from vm '%s'" % (packet_code, self.vm_name))
            return

        self.logger.debug("Received packet code '%s' from vm '%s'" % (packet_code, self.vm_name))

        if packet_code == PacketCode.REQUEST_METADATA:
            await self.write_metadata()
        elif packet_code == PacketCode.REQUEST_USERDATA:
            await self.write_userdata()
        elif packet_code == PacketCode.REQUEST_NETWORKDATA:
            await self.write_networkdata()
