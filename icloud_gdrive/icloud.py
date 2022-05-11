import os
import sys
import json
import logging
import datetime

from urllib.parse import urlencode

from icloudpd import constants
from icloudpd.download import download_media
from icloudpd.authentication import authenticate, TwoStepAuthRequiredError, setup_logger
from pyicloud_ipd.services.photos import PhotoAlbum, PhotoAsset

logger = setup_logger()


class FilterAlbum(PhotoAlbum):
    """
    Wrapper class for PhotoAlbum with additional methods to filter photos by date range
    Methods adapted from @magus0219 via https://github.com/picklepete/pyicloud/pull/276
    """

    def __init__(self, album: PhotoAlbum):
        album.direction = 'DESCENDING'
        super().__init__(
            album.service,
            album.name,
            album.list_type,
            album.obj_type,
            album.direction,
            album.query_filter,
            album.page_size
        )
        self.album = album

    def _list_query_gen(self, offset, list_type, direction, query_filter=None, simple=False):
        query = {
            u"query": {
                u"filterBy": [
                    {
                        u"fieldName": u"startRank",
                        u"fieldValue": {u"type": u"INT64", u"value": offset},
                        u"comparator": u"EQUALS",
                    },
                    {
                        u"fieldName": u"direction",
                        u"fieldValue": {u"type": u"STRING", u"value": direction},
                        u"comparator": u"EQUALS",
                    },
                ],
                u"recordType": list_type,
            },
            u"resultsLimit": self.page_size * 2,
            u"zoneID": {u"zoneName": u"PrimarySync"},
        }
        if simple is False:
            query["desiredKeys"] = [
                u"resJPEGFullWidth",
                u"resJPEGFullHeight",
                u"resJPEGFullFileType",
                u"resJPEGFullFingerprint",
                u"resJPEGFullRes",
                u"resJPEGLargeWidth",
                u"resJPEGLargeHeight",
                u"resJPEGLargeFileType",
                u"resJPEGLargeFingerprint",
                u"resJPEGLargeRes",
                u"resJPEGMedWidth",
                u"resJPEGMedHeight",
                u"resJPEGMedFileType",
                u"resJPEGMedFingerprint",
                u"resJPEGMedRes",
                u"resJPEGThumbWidth",
                u"resJPEGThumbHeight",
                u"resJPEGThumbFileType",
                u"resJPEGThumbFingerprint",
                u"resJPEGThumbRes",
                u"resVidFullWidth",
                u"resVidFullHeight",
                u"resVidFullFileType",
                u"resVidFullFingerprint",
                u"resVidFullRes",
                u"resVidMedWidth",
                u"resVidMedHeight",
                u"resVidMedFileType",
                u"resVidMedFingerprint",
                u"resVidMedRes",
                u"resVidSmallWidth",
                u"resVidSmallHeight",
                u"resVidSmallFileType",
                u"resVidSmallFingerprint",
                u"resVidSmallRes",
                u"resSidecarWidth",
                u"resSidecarHeight",
                u"resSidecarFileType",
                u"resSidecarFingerprint",
                u"resSidecarRes",
                u"itemType",
                u"dataClassType",
                u"filenameEnc",
                u"originalOrientation",
                u"resOriginalWidth",
                u"resOriginalHeight",
                u"resOriginalFileType",
                u"resOriginalFingerprint",
                u"resOriginalRes",
                u"resOriginalAltWidth",
                u"resOriginalAltHeight",
                u"resOriginalAltFileType",
                u"resOriginalAltFingerprint",
                u"resOriginalAltRes",
                u"resOriginalVidComplWidth",
                u"resOriginalVidComplHeight",
                u"resOriginalVidComplFileType",
                u"resOriginalVidComplFingerprint",
                u"resOriginalVidComplRes",
                u"isDeleted",
                u"isExpunged",
                u"dateExpunged",
                u"remappedRef",
                u"recordName",
                u"recordType",
                u"recordChangeTag",
                u"masterRef",
                u"adjustmentRenderType",
                u"assetDate",
                u"addedDate",
                u"isFavorite",
                u"isHidden",
                u"orientation",
                u"duration",
                u"assetSubtype",
                u"assetSubtypeV2",
                u"assetHDRType",
                u"burstFlags",
                u"burstFlagsExt",
                u"burstId",
                u"captionEnc",
                u"locationEnc",
                u"locationV2Enc",
                u"locationLatitude",
                u"locationLongitude",
                u"adjustmentType",
                u"timeZoneOffset",
                u"vidComplDurValue",
                u"vidComplDurScale",
                u"vidComplDispValue",
                u"vidComplDispScale",
                u"vidComplVisibilityState",
                u"customRenderedValue",
                u"containerId",
                u"itemId",
                u"position",
                u"isKeyAsset",
            ]
        else:
            query["desiredKeys"] = [
                u"assetDate",
                u"recordName",
                u"recordType",
                u"recordChangeTag",
                u"masterRef",
            ]

        if query_filter:
            query["query"]["filterBy"].extend(query_filter)

        return query

    def __get_photos_by_date(self):
        """Prefetch date info of all photo to filter

        :param self:
        :return:
        """
        for photo in self.fetch_photos(simple=True):
            yield photo

    def __get_offset_and_cnt_by_date(self, album_len, date_start, date_end):
        """Get idx and cnt of date query
        Use DESCENDING as api direction so index of the first item is len-1

        :param self:
        :param album_len: (int) len of album
        :param date_start: (datetime.date) start date of query
        :param date_end: (datetime.date) end date of query(include)
        :return: (offset, cnt)
        """
        idx_first = None
        idx_last = None

        idx = 0
        for photo in self.__get_photos_by_date():
            # pylint: disable=protected-access
            asset_date = datetime.datetime.fromtimestamp(
                photo._asset_record["fields"]["assetDate"]["value"] // 1000
            ).date()
            if self.direction == "DESCENDING":
                if asset_date > date_end:
                    if idx_first is not None and idx_last is None:
                        idx_last = idx - 1
                        break

                elif asset_date >= date_start:
                    if idx_first is None:
                        idx_first = idx
                    idx += 1
                    continue

                else:
                    idx += 1
            else:
                if asset_date < date_start:
                    if idx_first is not None and idx_last is None:
                        idx_last = idx - 1
                        break

                elif asset_date <= date_end:
                    if idx_first is None:
                        idx_first = idx
                    idx += 1
                    continue

                else:
                    idx += 1

        if idx_first is None:
            return 0, 0
        if idx_last is None:
            idx_last = album_len - 1

        if self.direction == "DESCENDING":
            return album_len - 1 - idx_first, idx_last - idx_first + 1
        return idx_first, idx_last - idx_first + 1

    def calculate_offset_and_cnt(self, album_len=None, last=None, date_start=None, date_end=None):
        """A method to calculate offset and cnt from input

        Photos are sorted by date in ascending order, and the idx is reverted.
        For example:
        item    idx
        0       3
        1       2
        2       1
        3       0

        :param self:
        :param album_len: (int) len of album
        :param last: (int) cnt of recent photos
        :param date_start: (datetime.date) start date of query
        :param date_end: (datetime.date) end date of query(include)
        :return:
        """
        if not album_len:
            album_len = len(self)

        if date_start:
            if not date_end:
                date_end = datetime.date.today() + datetime.timedelta(days=1)

            offset, cnt = self.__get_offset_and_cnt_by_date(
                album_len, date_start, date_end
            )

        elif last:
            if last > album_len:
                last = album_len

            if self.direction == "DESCENDING":
                offset = last - 1
            else:
                offset = 0
            cnt = last
        else:
            if self.direction == "DESCENDING":
                offset = album_len - 1
            else:
                offset = 0
            cnt = album_len

        return offset, cnt

    def fetch_photos(self, album_len=None, last=None, date_start=None, date_end=None, simple=False):
        """Fetch photos using offset and cnt

        :param album_len: (int) len of album
        :param last: (int) start date of query
        :param date_start: (datetime.date) start date of query
        :param date_end: (datetime.date) end date of query(include)
        :param simple: (bool) flag to fetch only simple metadata of photo
        :return:
        """

        offset, cnt = self.calculate_offset_and_cnt(
            album_len=album_len, last=last, date_start=date_start, date_end=date_end
        )

        while cnt:
            # pylint: disable=protected-access
            url = ("%s/records/query?" % self.service._service_endpoint) + urlencode(
                self.service.params
            )
            request = self.service.session.post(
                url,
                data=json.dumps(
                    self._list_query_gen(
                        offset,
                        self.list_type,
                        self.direction,
                        self.query_filter,
                        simple,
                    )
                ),
                headers={"Content-type": "text/plain"},
            )
            response = request.json()

            asset_records = []
            master_records = {}
            for rec in response["records"]:
                if rec["recordType"] == "CPLAsset":
                    master_id = rec["fields"]["masterRef"]["value"]["recordName"]
                    asset_records.append({"master_id": master_id, "record": rec})
                elif rec["recordType"] == "CPLMaster":
                    master_records[rec["recordName"]] = rec

            asset_records_len = len(asset_records)
            if asset_records_len:
                if self.direction == "DESCENDING":
                    offset = offset - asset_records_len
                else:
                    offset = offset + asset_records_len

                for asset_record in asset_records:
                    if cnt:
                        yield PhotoAsset(
                            self.service,
                            master_records[asset_record["master_id"]],
                            asset_record["record"],
                        )
                        cnt -= 1
                    else:
                        break
            else:
                break  # pragma: no cove


class iCloudScraper:

    def __init__(self, **kwargs):
        self.api = None
        self.cookie_dir = kwargs.get('cookie_dir', '~/.pyicloud')
        self.download_dir = os.path.normpath(kwargs.get('download_dir', './Photos'))
        self.folder_structure = kwargs.get('folder_structure', '{:%Y/%m}')

    def login(self, username, password):
        logger.info('Authenticating...')
        try:
            self.api = authenticate(
                username=username,
                password=password,
                cookie_directory=self.cookie_dir,
                raise_error_on_2sa=False,  # For now
                client_id=os.environ.get("CLIENT_ID")
            )
            logger.info(f'Logged into {self.api}')
            return self
        except TwoStepAuthRequiredError as e:
            logger.error(str(e))
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
                    return FilterAlbum(album)
        logger.error(f'No Album found for {album_name}')
        return None

    def delete_photo(self, photo: PhotoAsset):
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
            logger.info(f'Deleted {photo.filename} from iCloud')
            return True
        else:
            logger.error(f'Failed to delete {photo.filename} from iCloud')
            print(f'Failed to delete {photo.filename} from iCloud')
            return False
