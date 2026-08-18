import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import config
from app.models.schema import MaterialInfo, VideoAspect
from app.services import generative_video, material


class TestGenerativeVideo(unittest.TestCase):
    def setUp(self):
        self.original_app_config = dict(config.app)
        self.original_proxy_config = dict(config.proxy)
        config.proxy.clear()
        config.app.update(
            {
                "generative_video_base_url": "https://video.example/",
                "generative_video_api_key": "secret",
                "generative_video_model": "seedance-compatible",
                "generative_video_create_path": "/v1/videos/generations",
                "generative_video_status_path": "/v1/videos/generations/{id}",
                "generative_video_poll_interval_seconds": 1,
                "generative_video_run_timeout_seconds": 10,
                "tls_verify": True,
            }
        )

    def tearDown(self):
        config.app.clear()
        config.app.update(self.original_app_config)
        config.proxy.clear()
        config.proxy.update(self.original_proxy_config)

    def _response(self, payload):
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: payload,
        )

    def test_generate_clip_accepts_direct_video_url(self):
        with patch(
            "app.services.generative_video.requests.request",
            return_value=self._response(
                {"id": "gen-1", "status": "completed", "video_url": "https://cdn.example/1.mp4"}
            ),
        ) as request:
            item = generative_video.generate_clip(
                "cinematic product shot",
                duration=5,
                video_aspect=VideoAspect.portrait,
            )

        self.assertEqual(item.provider, "generative")
        self.assertEqual(item.url, "https://cdn.example/1.mp4")
        self.assertEqual(item.duration, 5)
        self.assertEqual(item.source_info["asset_id"], "gen-1")
        payload = request.call_args.kwargs["json"]
        self.assertEqual(payload["model"], "seedance-compatible")
        self.assertEqual(payload["prompt"], "cinematic product shot")
        self.assertEqual(payload["duration"], 5)
        self.assertEqual(payload["aspect_ratio"], "9:16")
        self.assertEqual(
            request.call_args.kwargs["headers"]["Authorization"],
            "Bearer secret",
        )

    def test_generate_clip_polls_async_job(self):
        responses = [
            self._response({"task_id": "job-9", "status": "queued"}),
            self._response({"data": {"state": "processing"}}),
            self._response(
                {
                    "data": {
                        "state": "completed",
                        "output_url": "https://cdn.example/final.mp4",
                    }
                }
            ),
        ]

        with patch(
            "app.services.generative_video.requests.request", side_effect=responses
        ) as request, patch("app.services.generative_video.time.sleep"):
            item = generative_video.generate_clip("city aerial", duration=4)

        self.assertEqual(item.url, "https://cdn.example/final.mp4")
        self.assertEqual(request.call_count, 3)
        self.assertEqual(request.call_args_list[1].args[0], "GET")
        self.assertTrue(request.call_args_list[1].args[1].endswith("/job-9"))

    def test_material_pipeline_bypasses_stock_cache_for_generated_clips(self):
        generated = MaterialInfo(
            provider="generative",
            url="https://cdn.example/generated.mp4",
            duration=5,
            source_info={"provider": "generative", "asset_id": "g-1"},
        )

        with patch(
            "app.services.material.generative_video.search_videos",
            return_value=[generated],
        ) as search, patch(
            "app.services.material._search_videos_with_cache"
        ) as cached_search, patch(
            "app.services.material.save_video", return_value="/tmp/generated.mp4"
        ), patch("app.services.material._persist_material_sources"):
            paths = material.download_videos(
                task_id="task-1",
                search_terms=["hero product shot"],
                source="generative",
                audio_duration=4,
                max_clip_duration=5,
            )

        self.assertEqual(paths, ["/tmp/generated.mp4"])
        search.assert_called_once()
        cached_search.assert_not_called()


if __name__ == "__main__":
    unittest.main()
