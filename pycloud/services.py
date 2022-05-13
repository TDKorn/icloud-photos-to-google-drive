import os
import sys
import calendar

from datetime import datetime
from abc import abstractmethod, ABC

from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

from icloudpd.authentication import authenticate, TwoStepAuthRequiredError
from pyicloud_ipd.services.photos import PhotoAsset

from pycloud.utils import FilterAlbum
from pycloud.logger import PyCloudLogger


class CloudService(ABC):

    def __init__(self, name):
        self.name = name
        self.logger = PyCloudLogger(obj=self, name=name)
        self._total_storage = None

    """Leaving these properties out until I can get iCloud storage space information"""
    # @property
    # @abstractmethod
    # def used_storage(self):
    #     pass
    #
    # @property
    # @abstractmethod
    # def total_storage(self):
    #     pass

    def info(self, msg):
        return self.logger.info(msg)

    def debug(self, msg):
        return self.logger.debug(msg)

    def error(self, msg):
        return self.logger.error(msg)


class gDrive(CloudService):
    FOLDER = 'application/vnd.google-apps.folder'

    def __init__(self, drive=None):
        super().__init__(name='gDrive')
        self.drive = drive
        self.folders = {}

        if not self.drive:
            self.drive = self.get_drive()

        self.initialize_folders()

    @staticmethod
    def get_drive():
        auth = GoogleAuth()
        auth.LocalWebserverAuth()
        drive = GoogleDrive(auth)
        return drive

    def initialize_folders(self):
        if self.upload_dir:
            # If root upload directory is already created, map it, and its subfolders, to their folder ids
            self.folders['upload'] = self.upload_dir['id']
            self.map_folders(self.upload_dir)
        else:
            # If root upload dir hasn't been created, we create it
            upload_dir = self.new_folder('PyCloud Drive', parent_id='root', key='upload')
            if not upload_dir.uploaded:
                self.error('Unable to initialize PyCloud Drive root upload folder')
                raise RuntimeError('Unable to initialize PyCloud Drive root upload folder')
            else:
                # After creating, there's nothing to map; new_folder() maps automatically
                self.info('Created PyCloud Drive root upload folder')
                return

    def map_folders(self, root):
        """Given a root directory, recursively map the ids of its subdirectories"""
        folders = self.get_folder_contents(root['id'])['folders']
        if not folders:
            # No subdirectories to map
            return

        for folder in folders:
            # If there's subdirectories, recursively map them to their folder ids
            name, id = folder['title'], folder['id']
            try:
                # If it's a month folder, convert month name to integer value
                month = str(datetime.strptime(name, "%B").month).zfill(2)
            except ValueError:
                month = None

            if month:  # Month folder dict key format is "YYYY/mm", need the name of parent(year) folder
                year_dir = self.drive.CreateFile({'id': folder['parents'][0]['id']})
                year_dir.FetchMetadata()
                year = year_dir['title']
                key = f'{year}/{month}'

            else:  # Any other folder's dict key is just the folder name
                key = name

            self.folders[key] = id
            self.map_folders(folder)

    def get_date_folder(self, date):
        """Get ID of the folder corresponding to a date in "YYYY/mm" format. Creates the folder if needed."""
        if self.folders.get(date):
            return self.folders[date]

        year, month = date.split('/')
        if year not in self.folders:
            # Both year and month folders need to be made
            year_dir = self.new_folder(
                name=year,
                parent_id=self.upload_dir['id']
            )
            if not year_dir.uploaded:
                self.error('Unable to create folder %s' % year)
                raise RuntimeError('Unable to create folder %s' % year)
            else:
                self.info('Created year folder for %s' % year)

        # Year folder exists. Creating month folder now
        month_name = calendar.month_name[int(month.lstrip('0'))]
        month_dir = self.new_folder(
            name=month_name,
            parent_id=self.folders[year],
            key=date
        )
        if month_dir.uploaded:
            self.info(f'Created month folder {month_name} for {date}')
            return self.get_date_folder(date)
        else:
            self.error(f'Unable to create month folder {month_name} for {date}')
            raise RuntimeError(f'Unable to create month folder {month_name} for {date}')

    def new_folder(self, name, parent_id='root', key=None):
        folder = self.drive.CreateFile(
            {
                'title': name,
                'parents': [
                    {
                        "kind": "drive#fileLink",
                        "id": parent_id
                    }
                ],
                "mimeType": gDrive.FOLDER
            }
        )
        folder.Upload()
        if folder.uploaded:
            key = key if key else name
            self.folders[key] = folder['id']
            self.info(f'Created folder {name}')
            return folder
        else:
            self.error(f'Failed to create folder {name}')
            print(f'Failed to create folder {name}')
            return False

    def add_file(self, filepath, title=None, parent_id=None):
        file = self.drive.CreateFile()
        if parent_id:
            file['parents'] = [
                {
                    "kind": "drive#fileLink",
                    "id": parent_id
                }
            ]
        if not title:
            title = os.path.basename(filepath)

        file['title'] = title
        file.SetContentFile(filepath)
        file.Upload()
        if file.uploaded:
            return file
        return False

    def get_folder(self, title, parent_id):
        """Search for folders by title within a given folder"""
        for folder in self.get_folder_contents(parent_id)['folders']:
            if folder['title'] == title:
                return folder
        return None

    def get_file(self, title, parent_id):
        """Search for files by title within a given folder"""
        for file in self.get_folder_contents(parent_id)['files']:
            if file['title'] == title:
                return file
        return None

    def get_folder_contents(self, folder_id):
        folder_contents = self.drive.ListFile({'q': "'" + folder_id + "' in parents and trashed=false"}).GetList()
        items = {
            'folders': [],
            'files': [],
            'count': len(folder_contents)
        }
        for item in folder_contents:
            if item.get('mimeType') == gDrive.FOLDER:
                items['folders'].append(item)
            else:
                items['files'].append(item)
        return items

    @property
    def upload_dir(self):
        return self.get_folder('PyCloud Drive', 'root')

    @property
    def root(self):
        return self.get_folder_contents('root')

    @property
    def root_folders(self):
        return self.root['folders']

    @property
    def root_files(self):
        return self.root['files']

    @property
    def about(self):
        return self.drive.GetAbout()

    @property
    def total_storage(self):
        if not self._total_storage:
            # Total storage should be constant, store value after retrieving
            self._total_storage = int(self.about['quotaBytesTotal'])
        return self._total_storage

    @property
    def used_storage(self):
        return int(self.about['quotaBytesUsed']) + int(self.about['quotaBytesUsedInTrash'])

    @property
    def available_storage(self):
        return self.total_storage - self.used_storage


class iCloud(CloudService):

    def __init__(self, **kwargs):
        super().__init__(name="iCloud")
        self.api = None
        self.cookie_dir = kwargs.get('cookie_dir', '~/.pyicloud')
        self.download_dir = os.path.normpath(kwargs.get('download_dir', './Photos'))
        self.folder_structure = kwargs.get('folder_structure', '{:%Y/%m}')

    def login(self, username, password):
        self.info('Authenticating...')
        try:
            self.api = authenticate(
                username=username,
                password=password,
                cookie_directory=self.cookie_dir,
                raise_error_on_2sa=False,  # For now
                client_id=os.environ.get("CLIENT_ID")
            )
            self.info(f'Logged into {self.api}')
            return self
        except TwoStepAuthRequiredError as e:
            self.error(str(e))
            sys.exit(1)

    @property
    def albums(self):
        if self.api:
            return self.api.photos.albums

    def get_album(self, album_name):
        if album := self.albums.get(album_name, None):
            return FilterAlbum(album)
        else:
            for name, album in self.albums.items():
                if name.lower() == album_name.lower():
                    self.info('Retrieved album: {}'.format(album))
                    return FilterAlbum(album)
        self.error(f'No Album found for {album_name}')
        return None

    def delete_photo(self, photo: PhotoAsset, permanent=False):
        """Adapted from @jacobpgallagher via https://github.com/picklepete/pyicloud/pull/354/"""
        record_name = photo._asset_record['recordName']
        record_type = photo._asset_record['recordType']
        record_change_tag = photo._master_record['recordChangeTag']

        json_data = {
            'operations': {
                'operationType': 'update',
                'record': {
                    'recordType': record_type,
                    'recordName': record_name,
                    'recordChangeTag': record_change_tag,  # '3t',
                    'fields': {
                        'isDeleted': {
                            'value': 1,
                        },
                        'isExpunged': {
                            'value': int(permanent),
                        },
                    },
                },
            },
            'zoneID': {
                'zoneName': 'PrimarySync',
                'zoneType': 'REGULAR_CUSTOM_ZONE'
            },
            'atomic': True,
        }
        endpoint = self.api.photos._service_endpoint
        url = f'{endpoint}/records/modify'

        response = self.api.session.post(
            url=url,
            json=json_data,
            params=self.api.params
        )
        if response.ok:
            self.info(f'Deleted {photo.filename} from iCloud')
            return True
        else:
            self.error(f'Failed to delete {photo.filename} from iCloud')
            print(f'Failed to delete {photo.filename} from iCloud')
            return False

    def clear_deleted_photos(self):
        """Permanently deletes photos from the Recently Deleted iCloud folder"""
        album = self.get_album('Recently Deleted')
        photos = album.fetch_photos()
        deleted_count = 0

        for photo in photos:
            self.delete_photo(photo, permanent=True)
            deleted_count += 1

        self.info(f"Permanently deleted {deleted_count} photos from iCloud")
        return True
