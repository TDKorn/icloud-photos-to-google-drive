import os
import sys
import datetime

from tzlocal import get_localzone
from icloudpd.download import download_media

from icloud_gdrive.gdrive import gDrive
from icloud_gdrive import iCloudScraper, logger

USERNAME = None
PASSWORD = None
COOKIE_DIR = '~/.pyicloud'
DOWNLOAD_DIR = './Photos'
FOLDER_STRUCTURE = '{:%Y/%m}'

FROM = datetime.date(2020, 1, 1)
TO = datetime.date(2020, 2, 1)

drive = gDrive()
cloud = iCloudScraper(
    cookie_dir=COOKIE_DIR,
    download_dir=DOWNLOAD_DIR,
    folder_structure=FOLDER_STRUCTURE).login(
    USERNAME,
    PASSWORD
)

while True:
    try:
        # album = cloud.get_album('All Photos')
        album = cloud.get_album(input('Enter an album name:\n>'))
        if album:
            logger.info(f'Retrieved album {album.name}')
            break
    except KeyboardInterrupt as e:
        logger.info('Exiting script')
        sys.exit(0)

# tqdm_kwargs = {
#     "total": len(photos),
#     "ascii": True
# }
# logger.set_tqdm(tqdm(photos, **tqdm_kwargs))

photos = album.fetch_photos(date_start=FROM, date_end=TO)
logger.info(f'Fetched photos from {album.name}')

# All directories will be made by the icloudpd.download.download_media() function
download_dir = os.path.join(cloud.download_dir,
                            f'PyCloud Photo Transfer {datetime.datetime.today().date()}')

success, failed = [], []
for photo in photos:
    try:
        created_date = photo.created.astimezone(get_localzone())
    except (ValueError, OSError):
        logger.error(
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
        logger.info(
            "Successfully downloaded %s to local folder %s",
            photo.filename,
            date_path
        )
    else:
        logger.error(f"Failed to download photo {photo.filename}")
        failed.append(photo)
        continue

    upload_id = drive.get_date_folder(date_path)
    file = drive.add_file(download_path, parent_id=upload_id)
    if not file.uploaded:
        logger.error(
            f'Failed to upload photo {photo.filename} to Google Drive folder {date_path}'
        )
        failed.append(photo)
        file = None
        os.remove(download_path)
        continue

    else:
        logger.info(f'Uploaded {photo.filename} to Google Drive folder {date_path}')
        file = None
        os.remove(download_path)

    deleted = cloud.delete_photo(photo)
    if not deleted:
        failed.append(photo)

logger.info(f'Finish transferring photos from album {album.name}')
if failed:
    logger.info('Writing failed log...')
    with open(os.path.join(download_dir, 'Failed Transfers.txt'), 'w') as f:
        f.write(
            '\n'.join(photo.id for photo in failed),
        )

logger.info('Exiting script...')
sys.exit(0)



