# Dr. Brauker's Batch Image Rotator

A small Flask web app for uploading one or more image-class `.zip` files, rotating the images in batch, and downloading a new `.zip` for Teachable Machine.

## Run Locally

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-rotate-images.txt
.venv/bin/python tree_rotator_web.py
```

Open:

```text
http://127.0.0.1:5050
```

## Production Start Command

Most Python hosts can run:

```bash
gunicorn tree_rotator_web:app
```

The included `Procfile` uses that command.

## Hosting Notes

This app processes uploaded zip files on the server, so choose a host with enough upload size, memory, disk space, and request time for your class image sets.

Good first options:

- Render: easiest for a Flask app connected to GitHub, but large uploads may require a paid plan.
- Railway: also simple for Flask, with configurable resources.
- A small VPS: best for very large class zip files because you control upload limits and disk space.

For classroom-only use with large image sets, running it locally may be smoother than hosting, because your previous rotated tree output was about 884 MB.
