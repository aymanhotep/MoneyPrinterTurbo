# Generative video providers

MoneyPrinterTurbo can use `video_source = "generative"` to turn its generated video terms into prompts for an external video-generation backend.

## Freepik / Magnific workflow

The built-in adapter understands the official Freepik async text-to-video task shape. `generative_video_provider = "freepik"` and `generative_video_provider = "magnific"` are aliases for this preset.

For the default Runway Gen-4.5 text-to-video endpoint:

```toml
[app]
video_source = "generative"
generative_video_provider = "freepik"
generative_video_api_key = "YOUR_FREEPIK_API_KEY"
```

The preset uses `https://api.freepik.com`, sends the key in `x-freepik-api-key`, posts to `/v1/ai/text-to-video/runway-4-5`, and polls `/v1/ai/text-to-video/runway-4-5/{id}`. Portrait, landscape, and square jobs map to the documented `720:1280`, `1280:720`, and `960:960` ratios.

You can override `generative_video_model`, `generative_video_base_url`, `generative_video_create_path`, `generative_video_status_path`, `generative_video_aspect_field`, and `generative_video_request_defaults` for another Freepik video model when its request fields are compatible with this adapter.

## Higgsfield

Higgsfield is intentionally not hard-coded as an API-key REST preset. Use the generic provider only when you have a supported authenticated gateway that exposes a create endpoint plus a pollable status endpoint:

```toml
[app]
video_source = "generative"
generative_video_provider = "generic"
generative_video_base_url = "https://your-gateway.example"
generative_video_api_key = "YOUR_KEY"
generative_video_model = "YOUR_MODEL"
generative_video_create_path = "/v1/videos/generations"
generative_video_status_path = "/v1/videos/generations/{id}"
```

This keeps the MoneyPrinterTurbo orchestration layer independent from vendor-specific authentication while still allowing Higgsfield-backed infrastructure to plug into the same material stage.
