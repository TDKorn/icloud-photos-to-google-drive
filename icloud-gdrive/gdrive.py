from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive


class gDrive:

    def __init__(self):
        self.drive = gDrive.login()

    @staticmethod
    def login():
        auth = GoogleAuth()
        auth.LocalWebserverAuth()
        drive = GoogleDrive(auth)
        return drive

    def new_folder(self, name, parent_id=None):
        folder = self.drive.CreateFile(
            {
                'title': name,
                'parents': [
                    {
                        "kind": "drive#fileLink",
                        "id": parent_id
                    }
                ],
                "mimeType": "application/vnd.google-apps.folder"
            }
        )
        if not parent_id:
            folder.pop('parents')
        folder.upload()

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

    def get_file(self, title, parent_id):
        """Search for files by title within a given folder"""
        parent_files = self.drive.ListFile({'q': "'" + parent_id + "' in parents and trashed=false"}).GetList()
        for file in parent_files:
            if file['title'] == title:
                return file
        return None

    def get_file_id(self, title, parent_id):
        if file := self.get_file(title, parent_id):
            return file['id']
        return None

    @property
    def root_files(self):
        return self.drive.ListFile({'q': "'root' in parents and trashed=false"}).GetList()

    @property
    def root_folders(self):
        return [file for file in self.root_files if file['mimeType'] == 'application/vnd.google-apps.folder']
