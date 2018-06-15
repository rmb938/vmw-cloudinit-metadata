import os
import os.path
from typing import Optional

import yaml
from schematics import Model
from schematics.exceptions import DataError
from schematics.types import StringType

from vmw_cloudinit_metadata.drivers.driver import Driver
from vmw_cloudinit_metadata.vspc.vm_client import InstanceData


class FileOptions(Model):
    directory = StringType(required=True)


class FileDriver(Driver):

    def parse_options(self, opts):
        options = FileOptions(opts)
        options.validate()

        return options

    def get_instance(self, vm_client) -> Optional[InstanceData]:
        vm_name = vm_client.vm_name
        file_path = os.path.join(self.options.directory, vm_name + ".yaml")
        if os.path.isfile(file_path) is False:
            self.logger.error("Could not find metadata file (%s) for VM %s" % (file_path, vm_name))
            return None

        with open(file_path, 'r') as f:
            try:
                raw_data = yaml.safe_load(f)
            except yaml.YAMLError:
                self.logger.exception("Metadata file %s is not valid yaml." % file_path)
                return None

            try:
                instance_data = InstanceData(raw_data)
                instance_data.validate()
            except DataError:
                self.logger.exception("Error parsing instance metadata file %s" % file_path)
                return None
        return instance_data

    def __init__(self, opts):
        super().__init__(opts)
