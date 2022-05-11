import os
import calendar

from datetime import datetime
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive


class gDrive:
    FOLDER = 'application/vnd.google-apps.folder'

    def __init__(self, drive=None):
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
            self.folders['upload'] = self.upload_dir['id']
            self.map_folders(self.upload_dir)
        else:
            upload_dir = self.new_folder('PyCloud Drive', parent_id='root', key='upload')
            if not upload_dir.uploaded:
                raise RuntimeError('Unable to initialize PyCloud Drive upload folder')

    def map_folders(self, root):
        """From a root directory, recursively map the ids of its subdirectories"""
        folders = self.get_folder_contents(root['id'])['folders']
        if not folders:     # No subdirectories to map
            return
        for folder in folders:
            # Recursively map the subdirectories to their folder ids
            name, id = folder['title'], folder['id']
            try:
                # If it's a month folder, convert month name to integer value
                month = str(datetime.strptime(name, "%B").month).zfill(2)
            except ValueError:
                month = None

            if month:
                # Month folder dict key format is "YYYY/mm", need the name of parent(year) folder
                year_dir = self.drive.CreateFile({'id': folder['parents'][0]['id']})
                year_dir.FetchMetadata()
                year = year_dir['title']
                key = f'{year}/{month}'
            else:
                # If it's not a month folder, the dict key is just the folder name
                key = name
            self.folders[key] = id
            self.map_folders(folder)

    def get_date_folder(self, date):
        """Get ID of the folder corresponding to a date in "YYYY/mm" format. Creates the folder if needed."""
        if self.folders.get(date):
            return self.folders[date]

        year, month = date.split('/')
        if year not in self.folders:  # Both year and month folders need to be made
            year_dir = self.new_folder(
                name=year,
                parent_id=self.upload_dir['id']
            )
            if not year_dir.uploaded:
                raise RuntimeError('Unable to create folder %s' % year)

        # Year folder must exist at this point. Still need to make month folder though
        month_name = calendar.month_name[int(month.lstrip('0'))]
        month_dir = self.new_folder(
            name=month_name,
            parent_id=self.folders[year],
            key=f'{year}/{month}'
        )
        if month_dir.uploaded:
            return self.get_date_folder(date)
        else:
            raise RuntimeError('Unable to create folder %s' % month)

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
            return folder
        else:
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
        return int(self.about['quotaBytesTotal'])

    @property
    def used_storage(self):
        return int(self.about['quotaBytesUsed']) + int(self.about['quotaBytesUsedInTrash'])

    @property
    def available_storage(self):
        return self.total_storage - self.used_storage
