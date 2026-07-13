# StegoForge

A minimal white/blue desktop GUI for LSB (Least Significant Bit) image steganography — hide and extract text messages inside PNG images.

Part of the **devforge** toolkit.

## Features

- **Hide (Steganography)** — embed a text message inside a cover image
- **Reveal (Desteganography)** — extract a hidden message from a stego image
- Live capacity estimation based on image size
- Optional password protection (XOR obfuscation layer)
- Drag-and-drop or click-to-browse image loading
- Threaded processing — UI never freezes on large images
- Clean minimal white/blue interface, no clutter

## How It Works

Each pixel channel (R, G, B) of a PNG can have its least significant bit changed without any visible difference to the human eye. StegoForge packs your message into a bitstream:

```
[4-byte magic header] + [4-byte message length] + [UTF-8 message bytes]
```

...and writes one bit of that stream into the LSB of each color channel value, in order. Extraction reverses the process: read the LSBs back, reassemble the header to find the message length, then decode the payload.

## Requirements

```bash
pip install PySide6 pillow numpy
```

## Usage

```bash
python3 stegoforge.py
```

1. **To hide a message:** select the "Hide" tab, choose a cover image, type your message, (optionally) set a password, then click "Hide Message in Image" and choose where to save the output PNG.
2. **To reveal a message:** select the "Reveal" tab, choose the stego image, enter the password if one was used, then click "Extract Hidden Message".

## Important Notes

- **Always use PNG for output.** JPEG uses lossy compression that destroys LSB data. If you load a JPG as a cover image, the tool still works, but you must save the *output* as PNG — which it always does.
- **The password feature is XOR obfuscation, not encryption.** It will stop a casual viewer from reading the message, but it is not cryptographically secure and provides no integrity check — a wrong password can occasionally still produce output that looks like valid (garbled) text instead of failing cleanly. For real confidentiality, encrypt the message yourself first (e.g. with your `CryptForge` AES-256-GCM tool) and hide the resulting ciphertext instead of relying on the built-in password.
- **Capacity** is roughly `(width × height × 3) / 8 − 9` characters, since 1 bit is used per color channel.
- Resizing, re-compressing, or converting a stego PNG to JPEG will destroy the hidden data.

## File Structure

```
stegoforge.py   — single-file application (engine + GUI)
README.md       — this file
```
