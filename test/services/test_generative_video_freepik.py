import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import config
from app.models.schema import VideoAspect
from app.services import generative_video


class TestFreepikGenerativeVideoPreset(unittest.TestCase):
    def setUp(self):
        self.original_app_config = dict(config.app)
        self.original_proxy_config = dict(config.proxy)
        config.proxy.clear()
        config.app.clear()
        config.app.update(
            {
                "generative_video_provider": "magnific",
                "generative_video_api_key": "freepik-secret",
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

    @staticmethod
    def _response(payload):
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: payload)

    def test_magnific_alias_uses_official_freepik_task_contract(self):
        responses = [
            self._response(
                {
                    "data": {
                        "task_id": "task-1",
                        "status": "CREATED",
                        "generated": [],
                    }
                }
            ),
            self._response(
                {
                    "data": {
                        "task_id": "task-1",
                        "status": "COMPLETED",
                        "generated": ["https://cdn.example/final.mp4"],
                    }
                }
            ),
        ]

        with patch(
            "app.services.generative_video.requests.request", side_effect=responses
        ) as request, patch("app.services.generative_video.time.sleep"):
            item = generative_video.generate_clip(
                "cinematic coffee commercial",
                duration=5,
                video_aspect=VideoAspect.portrait,
            )

        create_call = request.call_args_list[0]
        self.assertEqual(
            create_call.args[1],
            "https://api.freepik.com/v1/ai/text-to-video/runway-4-5",
        )
        self.assertEqual(
            create_call.kwargs["headers"]["x-freepik-api-key"], "freepik-secret"
        )
        self.assertEqual(create_call.kwargs["json"]["ratio"], "720:1280")
        self.assertEqual(create_call.kwargs["json"]["duration"], 5)
        self.assertEqual(item.provider, "freepik")
        self.assertEqual(item.url, "https://cdn.example/final.mp4")


if __name__ == "__main__":
    unittest.main()
