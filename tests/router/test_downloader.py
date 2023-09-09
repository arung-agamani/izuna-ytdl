from typing import List
from httpx import Client
from sqlmodel import delete
from unittest.mock import patch, MagicMock
from izuna_ytdl.models import DownloadTask, Item
from izuna_ytdl.models.download_task import DownloadStatusEnum
from izuna_ytdl.router.downloader import download


def test_get_task(client, login_cookie, stock_tasks):
    resp = client.get(
        "/api/downloader/tasks", headers={"access_token_cookie": login_cookie}
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["id"] == str(stock_tasks[0].id)


def test_retrieve(client: Client, login_cookie, stock_tasks):
    with patch("izuna_ytdl.router.downloader.s3") as mock_s3:
        mock_s3.generate_presigned_url.return_value = "https://downloadlink.com"

        resp = client.get(
            f"/api/downloader/retrieve?id={stock_tasks[0].id}",
            headers={"access_token_cookie": login_cookie},
        )
        assert resp.status_code == 201
        assert resp.text == "https://downloadlink.com"


class TestRouteDownload:
    def test_notask_noitem(self, client: Client, login_cookie, session):
        called_param = []

        def _side_mock_bgat(fn, id, task):
            nonlocal called_param
            called_param = [fn, id, task]

        with (
            patch("izuna_ytdl.router.downloader.download") as mock_download,
            patch("fastapi.BackgroundTasks.add_task") as mock_bgat,
        ):
            mock_bgat.side_effect = _side_mock_bgat
            resp = client.post(
                "/api/downloader/download",
                headers={"access_token_cookie": login_cookie},
                json={"url": "https://youtube.com/watch?v=86IxCGKUOzY"},
            )

            assert resp.status_code == 201
            assert resp.json() == {
                "success": True,
                "message": "Queueing download task for Youtube 86IxCGKUOzY",
            }
            mock_bgat.assert_called_once()
            [cl_fn, cl_id, cl_task] = called_param
            assert cl_fn == mock_download
            assert cl_id == "86IxCGKUOzY"
            assert cl_task.url == "https://youtube.com/watch?v=86IxCGKUOzY"
            session.exec(delete(Item))
            session.exec(delete(DownloadTask))
            session.commit()

    def test_notask_yesitem(self, client: Client, login_cookie, stock_items):
        with (
            patch("izuna_ytdl.router.downloader.download"),
            patch("fastapi.BackgroundTasks.add_task"),
        ):
            resp = client.post(
                "/api/downloader/download",
                headers={"access_token_cookie": login_cookie},
                json={"url": "https://youtube.com/watch?v=86IxCGKUOzY"},
            )

            assert resp.status_code == 201
            assert resp.json() == {
                "success": True,
                "message": "Item exists for queried item."
                "Associated user's data to the item",
            }

    def test_yestask_done(self, client: Client, login_cookie, stock_tasks, session):
        with (
            patch("izuna_ytdl.router.downloader.download"),
            patch("fastapi.BackgroundTasks.add_task"),
        ):
            stock_tasks[0].state = DownloadStatusEnum.DONE
            stock_tasks[0].save(session)

            resp = client.post(
                "/api/downloader/download",
                headers={"access_token_cookie": login_cookie},
                json={"url": "https://youtube.com/watch?v=86IxCGKUOzY"},
            )

            assert resp.status_code == 200
            assert resp.json() == {
                "success": True,
                "message": "Item have been downloaded",
            }

    def test_yestask_queued(self, client: Client, login_cookie, stock_tasks, session):
        called_param = []

        def _side_mock_bgat(fn, id, task):
            nonlocal called_param
            called_param = [fn, id, task]

        with (
            patch("izuna_ytdl.router.downloader.download") as mock_download,
            patch("fastapi.BackgroundTasks.add_task") as mock_bgat,
        ):
            stock_tasks[0].state = DownloadStatusEnum.QUEUED
            stock_tasks[0].save(session)
            mock_bgat.side_effect = _side_mock_bgat

            resp = client.post(
                "/api/downloader/download",
                headers={"access_token_cookie": login_cookie},
                json={"url": "https://youtube.com/watch?v=86IxCGKUOzY"},
            )

            assert resp.json() == {
                "success": True,
                "message": "Queueing download task for Youtube 86IxCGKUOzY",
            }
            assert resp.status_code == 201

            mock_bgat.assert_called_once()
            [cl_fn, cl_id, cl_task] = called_param
            assert cl_fn == mock_download
            assert cl_id == "86IxCGKUOzY"
            assert cl_task.url == "https://youtube.com/watch?v=86IxCGKUOzY"

    def test_yestask_error(self, client: Client, login_cookie, stock_tasks, session):
        called_param = []

        def _side_mock_bgat(fn, id, task):
            nonlocal called_param
            called_param = [fn, id, task]

        with (
            patch("izuna_ytdl.router.downloader.download") as mock_download,
            patch("fastapi.BackgroundTasks.add_task") as mock_bgat,
        ):
            stock_tasks[0].state = DownloadStatusEnum.ERROR_UNKNOWN
            stock_tasks[0].save(session)
            mock_bgat.side_effect = _side_mock_bgat

            resp = client.post(
                "/api/downloader/download",
                headers={"access_token_cookie": login_cookie},
                json={"url": "https://youtube.com/watch?v=86IxCGKUOzY"},
            )

            assert resp.json() == {
                "success": True,
                "message": "Queueing download task for Youtube 86IxCGKUOzY",
            }
            assert resp.status_code == 201

            mock_bgat.assert_called_once()
            [cl_fn, cl_id, cl_task] = called_param
            assert cl_fn == mock_download
            assert cl_id == "86IxCGKUOzY"
            assert cl_task.url == "https://youtube.com/watch?v=86IxCGKUOzY"


class TestDownloaderDownload:
    def test1(self, session, login_user, stock_tasks: List[DownloadTask]):
        with (
            patch("izuna_ytdl.router.downloader.s3"),
            patch("yt_dlp.YoutubeDL") as mock_ydl,
            patch("logging.error") as mock_log,
        ):
            ydl_i = mock_ydl.return_value.__enter__.return_value
            ydl_i.extract_info.return_value = {"duration": 700}

            task = stock_tasks[0]
            download(session, "86IxCGKUOzY", task)
            mock_log.assert_called_with("Other errors: Exception duration too long")

    def test2(self, session, login_user, stock_tasks: List[DownloadTask]):
        with (
            patch("izuna_ytdl.router.downloader.s3") as mock_s3,
            patch("yt_dlp.YoutubeDL") as mock_ydl,
            patch("logging.error") as mock_log,
            patch("os.remove") as osrem,
        ):
            ydl_i = MagicMock()
            ydl_enter = ydl_i.__enter__.return_value
            ydl_enter.extract_info.return_value = {
                "duration": 300,
                "title": "生きるよすが",
            }

            initopts = None

            def side_init(opts):
                nonlocal initopts
                initopts = opts
                return ydl_i

            mock_ydl.side_effect = side_init

            def side_download(url):
                postprocessor_hook = initopts["postprocessor_hooks"][0]
                progress_hook = initopts["progress_hooks"][0]
                d = {
                    "status": "finished",
                    "downloaded_bytes": 10,
                    "total_bytes": 10,
                    "info_dict": {
                        "filepath": "a",
                        "__files_to_move": {"a": "a.mp3"},
                    },
                }
                progress_hook(d)
                postprocessor_hook(d)

            ydl_enter.download.side_effect = side_download

            task = stock_tasks[0]
            download(session, "86IxCGKUOzY", task)

            mock_log.assert_not_called()
            osrem.assert_called_with("a.mp3")
            mock_s3.upload_file.assert_called_with(
                "a.mp3", "izuna-ytdl-files", "public/86IxCGKUOzY/a"
            )
            assert task.item.name == "a"
            assert task.title == "a"
            assert task.item.total_bytes == 10
            assert task.downloaded_bytes == 10
            assert task.item.remote_key == "public/86IxCGKUOzY/a"
            assert task.state == DownloadStatusEnum.DONE
