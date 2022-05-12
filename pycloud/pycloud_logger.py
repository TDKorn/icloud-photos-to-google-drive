import logging

from pycloud import *

logging.basicConfig(filename='pycloud.log', level=logging.DEBUG)

f"|[iCloud]|: U: 800MB | 38 Files | 193.4GB/200GB ||--||--|| Delete photo.filename ]|"

class pycloudLogger:

    def __init__(self, obj: object):
        self.obj = obj

        if isinstance(obj, iCloudScraper):
            self.name = 'iCloud'
        elif isinstance(obj, gDrive):
            self.name = 'gDrive'
        else:
            self.name = str(obj.__class__).split()[1].strip('>\'')

    def format_msg(self, msg):
        msg = "|[{name}]|: {used_storage}/{total_storage} ||--||--|| {message} ]|".format(
            name=self.name,
            used_storage=self.obj.used_storage,
            total_storage=self.obj.total_storage,
            message=msg
        )

        self.logger = self.setup_logger()


class gDriveLogger:

    def __init__(self, gDrive):
        self.gDrive = gDrive
        self.drive = gDrive.drive
        self.logger = self.setup_logger()
        self.format = "|[gDrive]|: D: {} | {} Files | {used_storage}/{total_storage}||--||--|| %(message)s ]|"

    def setup_logger(self):
        logger = logging.getLogger("gDrive")
        for handler in logger.handlers:
            if handler.name ==  'gDrive_stdoutLogger':
                return logger

        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S")
        stdout_handler = logging.StreamHandler(stream=sys.stdout)
        stdout_handler.setLevel(logging.INFO)
        stdout_handler.setFormatter(formatter)
        stdout_handler.name = "gDrive_stdoutLogger"
        logger.addHandler(stdout_handler)
        return logger

    def format_msg(self, msg):
        new_msg = "|[gDrive]|: D: {} | {} Files | {}/{} ||--||--|| {} ]|".format(
            "599MB",
            "38",
            # self.gDrive.downloaded_bytes,
            # self.gDrive.downloaded_files,
            self.gDrive.used_storage,
            self.gDrive.total_storage,
            msg
        )
        return new_msg

    def info(self, msg):
        msg = self.format_msg(msg)
        self.logger.info(msg)


def gdsfsdDriveLogger(drive):
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s |[gDrive]|: D: 800MB | 38 Files | {used_storage}/{total_storage}||--||--|| %(message)s ]|",
        datefmt="%Y-%m-%d %H:%M:%S")
        "%(asctime)s %(threadName)-11s %(levelname)-10s %(message)s")















