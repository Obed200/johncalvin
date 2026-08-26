# The Ledger — Django edition

A news site with photo galleries, in-story links and embedded video, built
in Django. An administrator can create author accounts (with a photo), and
authors can publish stories with as many photos as the story needs.

## What's included

- **Two roles**: Administrator and Author, backed by Django's built-in
  `User` model plus a `Profile` model (role, bio, photo).
- **Eight sections**: News, Economy, Technology, Environment, Education,
  Blogs, Sports and Updates — used by the masthead nav, the sidebar and the
  `?category=` filter on the front page.
- **Admin dashboard** (`/accounts/dashboard/`): create author accounts
  (name, username, password, photo, bio), remove accounts, feature, edit or
  delete any story.
- **Author dashboard** (`/dashboard/`): publish stories with a headline,
  section, one-line summary, body text and photos; edit or delete your own
  stories afterwards.
- **Photo galleries**: a story carries as many photos as it needs. One is the
  **spotlight image** — it leads the story on the front page and at the top
  of the story; the rest appear in a gallery underneath, each with an
  optional caption. The spotlight is chosen from thumbnails while writing,
  and can be changed at any time from the edit page.
- **Links inside the story**: paste a web address anywhere and it becomes a
  link, or write `[words to link](https://example.com)` to link a phrase.
- **Embedded YouTube video**: a YouTube address on a line of its own plays
  on the page; `[Caption](https://youtu.be/…)` captions the player.
- **Per-story switches** to turn clickable links and video players off, so
  an author can show plain addresses instead.
- **Clickable story cards**: the photo, the headline and the summary all
  open the story — not just the headline.
- Django's own `/admin/` is also available and fully wired up (useful for
  bulk edits or promoting a user to administrator).

## Writing a story

Everything an author needs is on the author dashboard.

| To do this | Write this in the story box |
| --- | --- |
| Link an address | `https://example.com/report` |
| Link a phrase | `[the full report](https://example.com/report)` |
| Play a video | a YouTube address on a line of its own |
| Caption a video | `[Site tour](https://youtu.be/VIDEO_ID)` |

Story text is escaped before anything is linked, and only `http`, `https`
and `mailto` addresses ever become links — pasting markup or a
`javascript:` address is safe.

Photos are picked with a single file chooser (select several at once).
Thumbnails appear underneath with a radio button on each: the one you pick
is the spotlight image. Adding more photos, captioning them, changing the
spotlight or removing one is all done from **Edit** on the dashboard.

## Setup

```bash
python -m venv venv
source venv/bin/activate          # venv\Scripts\activate on Windows
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser  # creates your first administrator
python manage.py runserver
```

Visit `http://127.0.0.1:8000/`.

### Optional: load demo content

To see the site populated right away (a demo admin, a demo author, and a
few sample stories), run:

```bash
python manage.py seed_demo
```

This creates:
- Administrator — username `admin`, password `admin12345`
- Author — username `jkim`, password `author12345`

**Change or remove these before deploying anywhere public.**

## How account creation works

1. Sign in as an administrator at `/accounts/login/`.
2. Go to the **Admin dashboard** and fill in the "Create an author account"
   form — name, username, password, an optional photo, and a short bio.
3. Give those credentials to the author. They sign in at the same
   `/accounts/login/` page and land on their own **Author dashboard**,
   where they can publish stories under their byline.

Administrators can remove any author account from the same dashboard
(their published stories stay live, just kept under their original byline).

## Upgrading an existing copy

`python manage.py migrate` does the whole move:

- the five old business sections are folded into the new eight (Business,
  Markets and Money become **Economy**; Leadership becomes **Blogs**);
- each story's single cover photo becomes its spotlight photo in the new
  gallery, so no image is lost.

## Tests

```bash
python manage.py test news
```

Covers link and video rendering (including the escaping rules and the two
per-story switches), spotlight-photo selection, publishing with several
photos at once, and the edit page.

## Notes for going to production

The app is now configured to run in production via environment variables
(see `.env.example`): `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` and
`DATABASE_URL` are all read from the environment, static files are served
by WhiteNoise, and `Procfile` runs migrations, `collectstatic`, then
`gunicorn`.

One thing that's *not* solved: uploaded images (`media/`) are still stored
on local disk. That's fine for a single always-on container, but most
PaaS hosts (including Railway, unless a Volume is attached — see below)
don't persist local disk writes across redeploys. Move to cloud storage
(e.g. S3 via `django-storages`) if that becomes a problem.

## Deploying to Railway (johncalvin.site)

1. **Create the project.** In Railway, "New Project" → "Deploy from GitHub
   repo" → select `Obed200/johncalvin`.
2. **Set the root directory.** This Django project lives in
   `ledger_project/`, not the repo root — in the service's Settings →
   "Root Directory", set it to `ledger_project`. Railway will then pick up
   `requirements.txt`, `Procfile` and `.python-version` from there via
   Nixpacks automatically.
3. **Add a Postgres database.** "New" → "Database" → "Add PostgreSQL" in
   the same project. Railway injects `DATABASE_URL` into your web
   service automatically (via a shared variable reference) — no manual
   copy-pasting needed once the two services are in the same project.
4. **Set environment variables** on the web service (Settings →
   Variables):
   - `SECRET_KEY` — a long random string (don't reuse the dev default in
     `settings.py`; generate one with
     `python -c "import secrets; print(secrets.token_urlsafe(50))"`).
   - `DEBUG` = `False`
   - `ALLOWED_HOSTS` — optional; `johncalvin.site`, `www.johncalvin.site`
     and the Railway-assigned `*.up.railway.app` domain are already
     allowed by default in `settings.py`. Only set this if you need
     another host.
5. **Deploy.** Railway builds and runs the `Procfile`'s `web` command,
   which applies migrations, collects static files, then starts gunicorn.
6. **Attach the custom domain.** In the web service → Settings →
   Networking → "Custom Domain", add `johncalvin.site` (and
   `www.johncalvin.site` if you want both). Railway gives you a CNAME (or
   an A/ALIAS target for the apex domain) — add that record at your DNS
   registrar. DNS propagation can take a few minutes to a few hours;
   Railway auto-provisions the TLS certificate once it verifies.
7. **Persist uploaded photos (optional but recommended).** Without this,
   anything authors upload to `media/` is lost on the next deploy. In the
   web service → Settings → Volumes, add a volume mounted at
   `/app/media` (the `media/` folder is created relative to the app's
   working directory).
8. **Create your first administrator** once it's live: use Railway's
   "Deploy" → service → the built-in shell (or `railway run` locally with
   the CLI) to run `python manage.py createsuperuser`.
