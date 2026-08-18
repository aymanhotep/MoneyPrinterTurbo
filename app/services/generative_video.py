import time
from typing import Any, Iterable
from urllib.parse import urljoin

import requests
from loguru import logger

from app.config import config
from app.models.schema import MaterialInfo, VideoAspect


class GenerativeVideoError(RuntimeError):
    """Raised when a configured generative-video backend cannot complete a clip."""


_SUCCESS_STATES = {"completed", "complete", "succeeded", "success", "ready", "done"}
_FAILURE_STATES = {"failed", "failure", "error", "cancelled", "canceled", "rejected"}
_MAGNIFIC_DEFAULT_BASE_URL = "https://api.magnific.com"
_MAGNIFIC_DEFAULT_MODEL = "runway-4-5"


def _cfg(name: str, default: Any = None) -> Any:
    return config.app.get(name, default)


def _provider() -> str:
    configured = str(_cfg("generative_video_provider", "")).strip().lower()
    if configured:
        return configured

    base_url = str(_cfg("generative_video_base_url", "")).strip().lower()
    if "api.magnific.com" in base_url:
        return "magnific"
    return "generic"


def _base_url() -> str:
    configured = str(_cfg("generative_video_base_url", "")).strip()
    if configured:
        return configured
    if _provider() == "magnific":
        return _MAGNIFIC_DEFAULT_BASE_URL
    return ""


def is_enabled() -> bool:
    return bool(_base_url())


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    api_key = str(_cfg("generative_video_api_key", "")).strip()
    if api_key:
        if _provider() == "magnific":
            default_header = "x-magnific-api-key"
            default_prefix = ""
        else:
            default_header = "Authorization"
            default_prefix = "Bearer "

        header_name = str(
            _cfg("generative_video_api_key_header", default_header)
        ).strip() or default_header
        prefix = str(_cfg("generative_video_api_key_prefix", default_prefix))
        headers[header_name] = f"{prefix}{api_key}"

    extra_headers = _cfg("generative_video_extra_headers", {})
    if isinstance(extra_headers, dict):
        for key, value in extra_headers.items():
            if key and value is not None:
                headers[str(key)] = str(value)
    return headers


def _request_timeout() -> tuple[int, int]:
    connect_timeout = int(_cfg("generative_video_connect_timeout_seconds", 30) or 30)
    read_timeout = int(_cfg("generative_video_request_timeout_seconds", 120) or 120)
    return connect_timeout, read_timeout


def _endpoint(path: str) -> str:
    base_url = _base_url()
    if not base_url:
        raise GenerativeVideoError("generative_video_base_url is not configured")
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def _dig(payload: Any, path: str) -> Any:
    current = payload
    for token in path.split("."):
        if isinstance(current, dict):
            if token not in current:
                return None
            current = current[token]
            continue
        if isinstance(current, list):
            try:
                current = current[int(token)]
            except (ValueError, IndexError):
                return None
            continue
        return None
    return current


def _first(payload: Any, paths: Iterable[str]) -> Any:
    for path in paths:
        value = _dig(payload, path)
        if value not in (None, "", [], {}):
            return value
    return None


def _task_id(payload: Any) -> str:
    value = _first(
        payload,
        (
            "id",
            "task_id",
            "request_id",
            "generation_id",
            "data.id",
            "data.task_id",
            "data.request_id",
            "data.generation_id",
        ),
    )
    return str(value or "").strip()


def _status(payload: Any) -> str:
    value = _first(
        payload,
        ("status", "state", "data.status", "data.state", "result.status"),
    )
    return str(value or "").strip().lower()


def _video_url(payload: Any) -> str:
    value = _first(
        payload,
        (
            "video_url",
            "output_url",
            "url",
            "data.video_url",
            "data.output_url",
            "data.url",
            "data.0.url",
            "data.generated.0",
            "generated.0",
            "output.video_url",
            "output.url",
            "output.0.url",
            "result.video_url",
            "result.url",
            "result.0.url",
        ),
    )
    return str(value or "").strip()


def _error_message(payload: Any) -> str:
    value = _first(
        payload,
        (
            "error.message",
            "error",
            "message",
            "data.error.message",
            "data.error",
            "data.message",
        ),
    )
    return str(value or "generative video request failed")


def _aspect_ratio(video_aspect: VideoAspect) -> str:
    return VideoAspect(video_aspect).value


def _magnific_ratio(video_aspect: VideoAspect) -> str:
    aspect = VideoAspect(video_aspect)
    mapping = {
        VideoAspect.landscape: "1280:720",
        VideoAspect.portrait: "720:1280",
        VideoAspect.square: "960:960",
    }
    return mapping[aspect]


def _model() -> str:
    configured = str(_cfg("generative_video_model", "")).strip()
    if configured:
        return configured
    if _provider() == "magnific":
        return _MAGNIFIC_DEFAULT_MODEL
    return ""


def _default_create_path() -> str:
    if _provider() == "magnific":
        return f"/v1/ai/text-to-video/{_model()}"
    return "/v1/videos/generations"


def _default_status_path() -> str:
    if _provider() == "magnific":
        return f"/v1/ai/text-to-video/{_model()}/{{id}}"
    return "/v1/videos/generations/{id}"


def _create_payload(
    prompt: str, duration: int, video_aspect: VideoAspect
) -> dict[str, Any]:
    if _provider() == "magnific":
        aspect_field = str(
            _cfg("generative_video_aspect_field", "ratio")
        ).strip() or "ratio"
        aspect_value = (
            _magnific_ratio(video_aspect)
            if aspect_field == "ratio"
            else _aspect_ratio(video_aspect)
        )
        payload: dict[str, Any] = {
            "prompt": prompt,
            "duration": int(duration),
            aspect_field: aspect_value,
        }
    else:
        payload = {
            "prompt": prompt,
            "duration": int(duration),
            "aspect_ratio": _aspect_ratio(video_aspect),
        }
        model = _model()
        if model:
            payload["model"] = model

    extras = _cfg("generative_video_request_defaults", {})
    if isinstance(extras, dict):
        payload = {**extras, **payload}
    return payload


def _request_json(method: str, url: str, **kwargs) -> Any:
    try:
        response = requests.request(
            method,
            url,
            headers=_headers(),
            proxies=config.proxy,
            verify=bool(_cfg("tls_verify", True)),
            timeout=_request_timeout(),
            **kwargs,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise GenerativeVideoError(
            f"generative video API request failed: {type(exc).__name__}: {exc}"
        ) from exc
    except ValueError as exc:
        raise GenerativeVideoError("generative video API returned invalid JSON") from exc


def generate_clip(
    prompt: str,
    duration: int,
    video_aspect: VideoAspect = VideoAspect.portrait,
) -> MaterialInfo:
    """Generate one clip using a configurable REST video-generation backend."""
    if not is_enabled():
        raise GenerativeVideoError("generative video backend is not configured")

    create_path = str(
        _cfg("generative_video_create_path", _default_create_path())
    ).strip()
    status_path_template = str(
        _cfg("generative_video_status_path", _default_status_path())
    ).strip()
    poll_interval = max(
        1.0, float(_cfg("generative_video_poll_interval_seconds", 3) or 3)
    )
    run_timeout = max(
        1.0, float(_cfg("generative_video_run_timeout_seconds", 900) or 900)
    )

    logger.info(
        "generating AI video material: "
        f"provider={_provider()}, model={_model() or 'configured-by-endpoint'}, "
        f"prompt={prompt!r}"
    )
    created = _request_json(
        "POST",
        _endpoint(create_path),
        json=_create_payload(prompt, duration, video_aspect),
    )

    direct_url = _video_url(created)
    generation_id = _task_id(created)
    state = _status(created)

    if direct_url and state not in _FAILURE_STATES:
        return MaterialInfo(
            provider=_provider(),
            url=direct_url,
            duration=int(duration),
            source_info={
                "provider": _provider(),
                "search_term": prompt,
                "asset_id": generation_id or None,
            },
        )

    if state in _FAILURE_STATES:
        raise GenerativeVideoError(_error_message(created))
    if not generation_id:
        raise GenerativeVideoError(
            "generative video API returned neither a video URL nor a generation id"
        )

    deadline = time.monotonic() + run_timeout
    while time.monotonic() < deadline:
        status_path = status_path_template.format(id=generation_id)
        result = _request_json("GET", _endpoint(status_path))
        state = _status(result)
        video_url = _video_url(result)

        if video_url and (not state or state in _SUCCESS_STATES):
            return MaterialInfo(
                provider=_provider(),
                url=video_url,
                duration=int(duration),
                source_info={
                    "provider": _provider(),
                    "search_term": prompt,
                    "asset_id": generation_id,
                },
            )
        if state in _FAILURE_STATES:
            raise GenerativeVideoError(_error_message(result))
        time.sleep(poll_interval)

    raise GenerativeVideoError(
        f"generative video generation timed out after {int(run_timeout)} seconds"
    )


def search_videos(
    search_term: str,
    minimum_duration: int,
    video_aspect: VideoAspect = VideoAspect.portrait,
) -> list[MaterialInfo]:
    """Material-provider compatible wrapper used by MoneyPrinterTurbo."""
    return [
        generate_clip(
            prompt=search_term,
            duration=minimum_duration,
            video_aspect=video_aspect,
        )
    ]
