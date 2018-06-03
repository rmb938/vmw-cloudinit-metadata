from vmw_cloudinit_metadata.cli.app import MetadataApplication
from vmw_cloudinit_metadata.cli.commands.run import RunMetadata


def main():
    app = MetadataApplication()
    RunMetadata().register(app)
    app.run()
