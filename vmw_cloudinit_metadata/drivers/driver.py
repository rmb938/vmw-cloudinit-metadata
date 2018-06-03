import logging
from abc import ABCMeta, abstractmethod
from typing import Optional

from vmw_cloudinit_metadata.vspc.vm_client import VMClient, InstanceData


class Driver(object):
    __metaclass__ = ABCMeta

    def __init__(self, opts):
        self.logger = logging.getLogger("%s.%s" % (self.__module__, self.__class__.__name__))
        self.options = self.parse_options(opts)

    def new_client(self, vm_name, writer):
        return VMClient(vm_name, writer, self)

    @abstractmethod
    def parse_options(self, opts):
        raise NotImplemented

    @abstractmethod
    def get_instance(self, vm_name) -> Optional[InstanceData]:
        raise NotImplemented
