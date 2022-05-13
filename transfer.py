import os
import sys
import datetime

from tzlocal import get_localzone
from icloudpd.download import download_media

from pycloud import gDrive, iCloud, PyCloudLogger

USERNAME = None
PASSWORD = None
COOKIE_DIR = '~/.pyicloud'
DOWNLOAD_DIR = './Photos'
FOLDER_STRUCTURE = '{:%Y/%m}'

FROM = datetime.date(2020, 1, 1)
TO = datetime.date(2020, 2, 1)

drive = gDrive()
cloud = iCloud(
    cookie_dir=COOKIE_DIR,
    download_dir=DOWNLOAD_DIR,
    folder_structure=FOLDER_STRUCTURE).login(
    USERNAME,
    PASSWORD
)

log = PyCloudLogger(name='transfer.py')

while True:
    try:
        # album = cloud.get_album('All Photos')
        album = cloud.get_album(input('Enter an album name:\n>'))
        if album:
            cloud.info(f'Retrieved album {album.name}')
            break
    except KeyboardInterrupt as e:
        log.info('Exiting script')
        sys.exit(0)

photos = album.fetch_photos(date_start=FROM, date_end=TO)
cloud.info(f'Fetched photos from {album.name}')

# All directories will be made by the icloudpd.download.download_media() function
download_dir = os.path.join(cloud.download_dir,
                            f'PyCloud Photo Transfer {datetime.datetime.today().date()}')

success, failed = [], []
for photo in photos:
    if photo.size > drive.available_storage:
        # If not enough space, go to the next photo/video as it might be small enough
        continue

    try:
        created_date = photo.created.astimezone(get_localzone())
    except (ValueError, OSError):
        log.error(
            "Could not convert photo created date to local timezone (%s)" % photo.created)
        created_date = photo.created

    date_path = cloud.folder_structure.format(created_date)
    download_path = os.path.normpath(os.path.join(download_dir, date_path, photo.filename))

    downloaded = download_media(
        cloud.api,
        photo,
        download_path,
        size='original'
    )
    if downloaded:
        cloud.info("Downloaded {} to {}".format(
                photo.filename,
                date_path))
    else:
        log.error(f"Failed to download photo {photo.filename} from iCloud")
        failed.append(photo)
        continue

    upload_id = drive.get_date_folder(date_path)
    file = drive.add_file(download_path, parent_id=upload_id)
    if not file.uploaded:
        log.error(
            f'Failed to upload photo {photo.filename} to Google Drive folder {date_path}'
        )
        failed.append(photo)
        file = None
        os.remove(download_path)
        continue

    else:
        drive.info(f'Uploaded {photo.filename} to folder {date_path}')
        file = None
        os.remove(download_path)

    deleted = cloud.delete_photo(photo)
    if not deleted:
        failed.append(photo)

log.info(f'Finish transferring photos from album {album.name}')
if failed:
    for content in failed:
        log.debug('Failed: %s' % content.id)

log.info('Exiting script...')
sys.exit(0)



