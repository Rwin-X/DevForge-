# FaceCensor

> Local, in-browser face redaction. Blur, pixelate, or black-box every face in an image — zero uploads, zero servers, zero trust required.

![status](https://img.shields.io/badge/status-stable-3ddc97?style=flat-square)
![type](https://img.shields.io/badge/type-single--file%20HTML-111113?style=flat-square)
![license](https://img.shields.io/badge/license-MIT-8a8a8e?style=flat-square)

```
┌─────────────────────────────────────────┐
│  FACECENSOR // local face redaction      │
│  ● READY — runs entirely in your browser │
└─────────────────────────────────────────┘
```

## What it does

Drop in a screenshot, an OSINT export, or a batch of photos — FaceCensor finds every face and redacts it before you share anything further. All detection and processing happens **client-side**, in-memory, in your own browser tab. Nothing is ever sent over the network. Close the tab and it's gone.

| Mode | Result |
|---|---|
| **Blur** | Gaussian blur, double-pass at high intensity |
| **Pixelate** | Classic mosaic redaction |
| **Black Box** | Solid fill — zero residual information |

## Why

Built as an OPSEC utility — sanitize images before they leave your machine, without trusting a third-party redaction tool with the original.

## Features

- 🧠 **TensorFlow.js face detection** (`@vladmandic/face-api`, TinyFaceDetector) — loaded once from CDN, then fully offline for the session
- 🪞 **Mirror-scan mode** for catching missed side-profiles
- 🎛️ Live tuning: sensitivity, confidence threshold, box padding
- 📂 Drag & drop, file browser, or clipboard paste
- ⚡ Batch processing with sequential auto-download
- 🖼️ PNG or JPEG output
- 🖤 Minimal dark UI, zero dependencies beyond the detection model

## Usage

1. Open `index.html` in any modern browser.
2. Drop images into the queue (or paste from clipboard).
3. Pick a redaction mode and intensity, tune detection if needed.
4. **Save This Image** for one file, or **Process & Download All** for the whole queue.

No install. No build step. No backend.

## Detection notes

Face detection is not infallible — extreme angles, heavy occlusion, or poor lighting can cause misses. **Always check the live preview before trusting a batch run on sensitive material.** If a face is missed, raise sensitivity, lower the confidence threshold, or enable mirror-scan.

## Stack

`HTML` · `CSS` · `Vanilla JS` · [`face-api.js`](https://github.com/vladmandic/face-api) (TensorFlow.js)

---

<sub>Part of <a href="https://github.com/Rwin/devforge">devforge</a> — a vibe-coding practice repo.</sub>
