vmw-cloudinit-metadata
######################

Library and Tool to run a Cloud-Init NoCloud compatible metadata server for VMWare VCenter

VSPC
****

The application uses serial ports on virtual machines configured to use the network,
with the direction configured to client, the port uri configured to any string and the vSPC
URI configured to :code:`telnet://$ADDRESS:13370`

Usage
=====

.. code:: 

   vmw-cloudinit-metadata run --uri my-metadata --driver vmw_cloudinit_metadata.drivers.file:FileDriver --driver-opts '{"directory": "/some/directory/here"}'

Drivers
*******

The application can use various different drivers to load cloud-init metadata.

Custom drivers can be made by implementing the :code:`vmw_cloudinit_metadata.drivers.driver:Driver` interface.

File Driver
===========

The file dirver looks in the given path for yaml files with the name of the VM.

Options
-------

.. code::

   directory - path to yaml definition files


Example
-------

.. code::

   my-vm.yaml

   ---
   metadata:
     ami-id: my-image
     instance-id: my-instance
     region: us-east1
     availability-zone: us-east1-a
     tags:
       - a
       - b
       - c
     public-keys:
       - ssh....
     hostname: myhostnamehere
   network:
     address: 192.168.1.1
     netmask: 255.255.255.0
     gateway: 192.168.1.254
     search: 'example.com'
     nameservers:
       - 8.8.8.8
       - 8.8.4.4
   userdata: |
     #cloud-config
     growpart:
       mode: auto
       devices: ['/']
       ignore_growroot_disabled: false


Serial Communication
********************

All serial communication is done using "packets". All packets start with the string :code:`!!`
followed the by packet code, then the symbol :code:`#` followed by base64 encoded data.
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    The data returned is compatible with `Cloud-Init NoCloud <https://cloudinit.readthedocs.io/en/latest/topics/datasources/nocloud.html>`_

Example
=======

Client Sends

.. code::

   !!REQUEST_METADATA#


Server Response

.. code::

   !!RESPONSE_METADATA#ew0KICAgICJhbWktaWQiOiAibXktaW1hZ2UiLA0KICAgICJpbnN0YW5jZS1pZCI6ICJteS1pbnN0YW5jZSIsDQogICAgInJlZ2lvbiI6ICJteS1yZWdpb24iLA0KICAgICJhdmFpbGFiaWxpdHktem9uZSI6ICJteS16b25lIiwNCiAgICAidGFncyI6IFsiYSIsICJiIiwgImMiXSwNCiAgICAicHVibGljLWtleXMiOiBbDQogICAgICAgICJwdWJsaWMtc3NoLWtleS1oZXJlIg0KICAgIF0sDQogICAgImhvc3RuYW1lIjogIm15LWhvc3RuYW1lIiwNCiAgICAibG9jYWwtaG9zdG5hbWUiOiAibXktaG9zdG5hbWUiDQp9


After decoding the base64 data the response contains the following:

.. code::

   {
     "ami-id": "my-image",
     "instance-id": "my-instance",
     "region": "my-region",
     "availability-zone": "my-zone",
     "tags": ["a", "b", "c"],
     "public-keys": [
       "public-ssh-key-here"
     ],
     "hostname": "my-hostname",
     "local-hostname": "my-hostname"
   }

Packets
=======

:code:`REQUEST_METADATA`
------------------

Client requests instance metadata

:code:`REQUEST_NETWORKDATA`
---------------------

Client requests instance network data

:code:`REQUEST_USERDATA`
------------------

Client requests instance user data

:code:`RESPONSE_METADATA`
-------------------

Server responds with instance metadata

Example:

.. code::

   {
     "ami-id": "my-image",
     "instance-id": "my-instance",
     "region": "my-region",
     "availability-zone": "my-zone",
     "tags": ["a", "b", "c"],
     "public-keys": [
       "public-ssh-key-here"
     ],
     "hostname": "my-hostname",
     "local-hostname": "my-hostname"
   }


:code:`RESPONSE_NETWORKDATA`
----------------------

Server responds with instance networkdata

Example:

.. code::

   version: 1
   config:
   - type: physical
     name: eth0
     subnets:
     - type: static
       address: 192.168.1.1
       netmask: 255.255.255.0
       gateway: 192.168.1.254
       dns_search:
       - example.com
       dns_nameservers:
       - 8.8.8.8
       - 8.8.4.4



:code:`RESPONSE_USERDATA`
-------------------

Server responds with instance userdata

Example:

.. code::

   #cloud-config
   growpart:
     mode: auto
     devices: ['/']
     ignore_growroot_disabled: false
