# memotion.se

The website for ME Motion.

## Everyday use (no code)
Add or change projects, photos, videos, contact details and wedding prices in the admin panel:
**https://app.pagescms.org** → sign in with GitHub → open this repository.
Every save publishes the site again automatically in about a minute.

## What is where
| Folder / file | What it holds |
|---|---|
| `content/projects/` | One file per project on the Work page (edited through the admin panel) |
| `content/settings.json` | Email, phone, Instagram, Bunny address, showreel, portrait |
| `content/wedding.json` | Wedding package prices |
| `media/` | Photos uploaded through the admin panel |
| `assets/` | Design: styles, scripts, logos |
| `build.py` | Turns the content into the finished website (in `public/`) |
| `.pages.yml` | Setup of the admin panel |

## Publishing (one.com)
Every change to this repository (including every Save in the admin panel) starts the workflow in
`.github/workflows/publish.yml`. It builds the site and uploads it to the one.com web space over SFTP.
You can follow it, or run it by hand, under the **Actions** tab.

It needs these repository secrets (Settings → Secrets and variables → Actions):
`SFTP_HOST`, `SFTP_USER`, `SFTP_PASSWORD`, `SFTP_FOLDER` (and `SFTP_PORT` if it isn't 22).
A folder called `videos` in the web space is never touched by the upload.

## Videos
Videos are hosted on Bunny Stream. In the Bunny video library, MP4 Fallback must be switched on
(Encoding tab) before uploading, so the website can play the films.
