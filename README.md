# MoneyPrinterTurbo — AI Video Production Fork 💸

An end-to-end short-video production pipeline that turns a topic or script into finished social video using AI scripting, stock or generated visuals, voiceover, subtitles, music, FFmpeg assembly, and publishing.

This fork extends the original [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) with a **pluggable generative-video material layer**, including a first-party **Freepik API / Magnific workflow preset** and a generic provider boundary for other video-generation services.

> **Status:** the generative-video provider work currently lives on the `feature/generative-video-provider` branch / PR until merged.

## What this fork adds

- **AI-generated video materials** via `video_source = "generative"`
- **Freepik API preset** for the Magnific/Freepik workflow
  - `generative_video_provider = "freepik"`
  - `generative_video_provider = "magnific"` is accepted as an alias
  - async create → poll → download workflow
  - `x-freepik-api-key` authentication
  - portrait, landscape, and square aspect-ratio mapping
- **Generic async REST adapter** for other AI-video backends and private gateways
- **Higgsfield-ready provider boundary** without inventing an unsupported public REST contract
- AI-generated clips **bypass the stock-footage cache** so paid or temporary outputs are not accidentally reused
- Existing script, TTS, subtitle, music, rendering, and publishing stages remain unchanged

## Pipeline

```text
Topic / Brief
    ↓
LLM → script + scene/video terms
    ↓
Visual source
    ├── Freepik / Magnific AI video
    ├── Generic AI-video gateway
    ├── Pexels
    ├── Pixabay
    ├── Coverr
    └── Local assets
    ↓
Voiceover / TTS
    ↓
Subtitles
    ↓
Music
    ↓
FFmpeg assembly
    ↓
TikTok / Instagram / YouTube Shorts
```

## Supported visual sources

| Source | Type | Status |
|---|---|---|
| `pexels` | Stock footage | Supported |
| `pixabay` | Stock footage | Supported |
| `coverr` | Stock footage | Supported |
| `local` | Your own files | Supported |
| `loomloom` | Existing remote generation flow | Supported |
| `generative` + `freepik` / `magnific` | AI-generated video | Added in this fork |
| `generative` + generic REST gateway | AI-generated video | Added in this fork |
| Higgsfield | AI-generated video | Use through an authenticated gateway/provider integration when available |

## Freepik / Magnific setup

Copy the example configuration first:

```bash
cp config.example.toml config.toml
```

Then configure the generative source:

```toml
[app]
video_source = "generative"

generative_video_provider = "freepik"
generative_video_base_url = "https://api.freepik.com"
generative_video_api_key = "YOUR_FREEPIK_API_KEY"
generative_video_api_key_header = "x-freepik-api-key"
generative_video_api_key_prefix = ""

generative_video_model = "runway-4-5"
generative_video_create_path = "/v1/ai/text-to-video/runway-4-5"
generative_video_status_path = "/v1/ai/text-to-video/runway-4-5/{id}"
generative_video_aspect_field = "ratio"
```

You may also use:

```toml
generative_video_provider = "magnific"
```

as an alias for the same Freepik API preset.

See [`docs/generative-video-providers.md`](docs/generative-video-providers.md) for provider details.

## Generic AI-video gateway

For a custom or private provider, keep the provider generic and configure the REST contract:

```toml
[app]
video_source = "generative"
generative_video_provider = "generic"

generative_video_base_url = "https://your-video-gateway.example"
generative_video_api_key = "YOUR_KEY"
generative_video_api_key_header = "Authorization"
generative_video_api_key_prefix = "Bearer "

generative_video_model = "your-model"
generative_video_create_path = "/v1/videos/generations"
generative_video_status_path = "/v1/videos/generations/{id}"
```

The adapter supports either an immediate video URL or an asynchronous job ID followed by polling.

## Core capabilities inherited from MoneyPrinterTurbo

- AI Agent, WebUI, API, and CLI workflows
- AI-generated or custom scripts
- Portrait `9:16`, landscape `16:9`, and square workflows
- Batch video generation
- Multilingual scripts
- TTS through Edge TTS, Azure Speech, SiliconFlow, Gemini, Xiaomi MiMo, ElevenLabs, Chatterbox, and other configured providers
- Configurable subtitles
- Background music
- Local and stock footage
- Multiple LLM providers and gateways
- Cross-platform publishing to TikTok, Instagram, and YouTube Shorts

## Why this fork exists

The original project already has a useful orchestration and rendering engine. The goal of this fork is to turn it into a more flexible **AI creative-production backend** where the visual-material stage can use stock footage or generated scenes without rewriting the rest of the pipeline.

A practical production workflow becomes:

```text
5 hooks × 3 scripts × 2 visual styles = 30 creative variants
```

while keeping narration, captions, music, rendering, and publishing automated.

## Arabic summary — ملخص عربي

هذه النسخة توسّع MoneyPrinterTurbo ليصبح أقرب إلى **مصنع محتوى فيديو بالذكاء الاصطناعي** بدل الاعتماد فقط على فيديوهات Stock.

يمكنك الآن استخدام `video_source = "generative"` لتوليد المشاهد عبر **Freepik / Magnific** أو أي مزود Video API متوافق، ثم يكمّل النظام تلقائيًا التعليق الصوتي، الترجمة، الموسيقى، المونتاج والنشر.

بالنسبة إلى **Higgsfield**، البنية أصبحت جاهزة لربطه كمزوّد مستقل، لكننا لا نضع API غير موثّق داخل المشروع؛ يتم ربطه عندما يتوفر مسار API/Gateway رسمي أو موثوق.

## Running the project

Use the original MoneyPrinterTurbo installation flow for your platform. The upstream project supports Docker as well as local Python environments.

For the full original documentation, screenshots, deployment notes, sponsor information, and historical usage examples, see the upstream project:

- [harry0703/MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo)
- [Original English README](https://github.com/harry0703/MoneyPrinterTurbo/blob/main/README-en.md)

## Development

Tests for this extension live under:

```text
test/services/test_generative_video.py
test/services/test_generative_video_freepik.py
```

The implementation is primarily in:

```text
app/services/generative_video.py
app/services/material.py
```

## Attribution and license

This repository is a fork of **MoneyPrinterTurbo** by its original author and contributors. The project remains under the **MIT License**. Please preserve the upstream copyright and license notices when redistributing modified versions.
