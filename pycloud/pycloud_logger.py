import logging

import icloud_gdrive

logging.basicConfig(filename='pycloud.log', level=logging.DEBUG)

f"|[iCloud]|: U: 800MB | 38 Files | 193.4GB/200GB ||--||--|| Delete photo.filename ]|"

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















