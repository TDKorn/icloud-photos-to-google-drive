from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive


class gDrive:
    FOLDER = 'application/vnd.google-apps.folder'

    def __init__(self, drive=None):
        self.drive = drive
        self.folders = {}

        if not self.drive:
            self.drive = self.get_drive()

    @staticmethod
    def get_drive():
        auth = GoogleAuth()
        auth.LocalWebserverAuth()
        drive = GoogleDrive(auth)
        return drive

    def initialize_folders(self):
        if not (pycloud := self.pycloud_root):
            pycloud = self.new_folder('PyCloud')
            if not pycloud.uploaded:
                raise Exception('Could not create root folder')

        self.folders['PyCloud'] = pycloud['id']

    def new_folder(self, name, parent_id='root'):
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
            return folder
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
        if title:
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

    def get_file_id(self, title, parent_id):
        if file := self.get_file(title, parent_id):
            return file['id']
        return None

    def get_folder_contents(self, folder_id):
        folder_contents = self.drive.ListFile({'q': "'" + folder_id + "' in parents and trashed=false"}).GetList()
        items = {
            'folders': [],
            'files': []
        }
        for item in folder_contents:
            if item.get('mimeType') == gDrive.FOLDER:
                items['folders'].append(item)
            else:
                items['files'].append(item)
        return items

    @property
    def pycloud_root(self):
        return self.get_folder('PyCloud', 'root')

    @property
    def root(self):
        return self.get_folder_contents('root')

    @property
    def root_folders(self):
        return self.root['folders']

    @property
    def root_files(self):
        return self.root['files']
