FROM docker.io/library/python:3.12-slim

ENV PYTHONUNBUFFERED=1

# Evita il warning di PyKMIP sulla configurazione assente.
RUN mkdir -p /etc/pykmip && printf '[client]\n' > /etc/pykmip/pykmip.conf

# Client KMIP (PyKMIP) + Web UI (Flask).
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /app
COPY app_version.py app_paths.py kmip_lib.py kmip_test.py webui.py /app/
COPY templates /app/templates

# I certificati vengono montati a runtime in /certs (vedi run.sh).
# Il comando predefinito è la CLI; per la Web UI vedi run-webui.sh.
ENTRYPOINT ["python", "/app/kmip_test.py"]
