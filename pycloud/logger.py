import logging
import sys
from pycloud.utils import convert_bytes
logging.basicConfig(filename='pycloud.log', level=logging.DEBUG)


class PyCloudLogger:

    def __init__(self, obj=None, name=None):
        self.obj = obj
        self.name = name

        if not self.name:
            if not self.obj:  # If no name or object is provided, there's nothing to work with
                raise AttributeError('Must provide either a name or an object')
            else:
                # If no name provided but object is provided, assign name based on class of the object
                self.name = str(obj.__class__).split()[1].strip('>\'')

        self.logger = self.setup_logger()

    def setup_logger(self):
        logger = logging.getLogger(name=self.name)
        handler_name = f'{self.name}_stdoutLogger'

        for handler in logger.handlers:
            if handler.name == handler_name:
                return logger

        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)-2s  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S")
        stdout_handler = logging.StreamHandler(stream=sys.stdout)
        stdout_handler.setFormatter(formatter)
        stdout_handler.setLevel(logging.INFO)
        stdout_handler.name = handler_name
        logger.addHandler(stdout_handler)

        return logger

    def format_msg(self, msg):
        new_msg = "|[{name}]|:{tabs}{message}".format(
            name=self.name,
            tabs='\t\t\t',
            message=msg
        )
        if hasattr(self.obj, 'used_storage') and hasattr(self.obj, 'total_storage'):
            # Google Drive API provides information about storage usage
            new_msg += "\t  ||  [{used:.2f}/{total:.2f}GB] ".format(
                used = convert_bytes(self.obj.used_storage, 'GB'),
                total = convert_bytes(self.obj.total_storage, 'GB')
            )
        return new_msg

    def info(self, msg):
        return self.logger.info(
            self.format_msg(msg)
        )

    def debug(self, msg):
        return self.logger.debug(
            self.format_msg(msg)
        )

    def warning(self, msg):
        return self.logger.warning(
            self.format_msg(msg)
        )

    def error(self, msg):
        return self.logger.error(
            self.format_msg(msg)
        )
