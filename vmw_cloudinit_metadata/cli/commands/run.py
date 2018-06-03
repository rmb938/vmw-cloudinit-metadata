import importlib
import json

from clify.daemon import Daemon
from vmw_cloudinit_metadata.drivers.driver import Driver
from vmw_cloudinit_metadata.vspc.server import VSPCServer


class RunMetadata(Daemon):
    def __init__(self):
        super().__init__('run', 'Run the  Metadata Server')
        self.vspc_server = None

    def setup_arguments(self, parser):
        parser.add_argument('--uri', help='The vSPC URI', required=True)
        parser.add_argument('--driver', help='The metadata driver to use', required=True)
        parser.add_argument('--driver-opts', help='Driver configuration options', type=json.loads, default={})

    def run(self, args) -> int:

        driver = self.load_driver(args.driver, args.driver_opts)

        self.vspc_server = VSPCServer(args.uri, driver)
        self.vspc_server.start()

        return 0

    def on_shutdown(self, signum=None, frame=None):
        self.logger.info("Shutting down the Metadata Server")
        if self.vspc_server is not None:
            self.vspc_server.stop()

    def load_driver(self, driver_string, opts):
        if ':' not in driver_string:
            raise ValueError("Driver does not contain a module and class. "
                             "Must be in the following format: 'my.module:MyClass'")

        driver_mod, driver_klass, *_ = driver_string.split(":")
        try:
            driver_mod = importlib.import_module(driver_mod)
        except ImportError:
            self.logger.exception("Could not import driver's module: " + driver_mod)
            raise

        try:
            driver_klass = getattr(driver_mod, driver_klass)
        except AttributeError:
            self.logger.exception("Could not get driver's module class: " + driver_klass)
            raise

        if not issubclass(driver_klass, Driver):
            raise ValueError("Driver class is not a subclass of '%s:%s'" % (Driver.__module__, Driver.__name__))

        return driver_klass(opts)
