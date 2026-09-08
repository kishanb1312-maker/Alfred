# Alfred · always-on worker
#
# Serves the Telegram email conversation while the user's laptop is off: approve → email
# preview card, edit → re-preview, send → the email actually goes out, with the ✅/❌
# confirmation. Email channel only — the portal channel needs the signed-in browser on the
# user's own machine and deliberately does not run here.
#
# The Alfred home is a VOLUME, not baked in: it holds the user's config, staged drafts and
# tailored PDFs, and it changes every time they run Alfred on their laptop.
#
#   docker build -t alfred-worker -f deploy/Dockerfile .
#   docker run -d --name alfred-worker --restart unless-stopped \
#       -v "$HOME/.alfred:/data" --env-file "$HOME/.alfred/.env" alfred-worker
#
# Secrets arrive through --env-file at RUN time. Never COPY a .env into the image: it would
# be baked into a layer and travel with every copy of it.

FROM python:3.12-slim

# No LibreOffice and no browser: tailoring and portal applications happen on the user's
# machine, and this container only talks to Telegram and SMTP. The worker's actual import
# closure is just requests + PyYAML, but the full requirements file is installed anyway so
# a later import can never fail at runtime out here, where nobody is watching. Re-check the
# closure with:  python -c "import ast,os,sys; ..."  (see deploy/README.md)
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/ ./scripts/

# Where the user's data is mounted. paths.py reads this and resolves config/, data/ and
# output/ beneath it, so the container never assumes a home directory layout.
ENV ALFRED_HOME=/data \
    PYTHONUNBUFFERED=1
VOLUME ["/data"]

# Not root: this process reads the user's resume, cover letters and Gmail app password.
RUN useradd --create-home --uid 10001 alfred
USER alfred

# --once is the smoke test:  docker run --rm ... alfred-worker --once
ENTRYPOINT ["python", "scripts/alfred_worker.py"]
