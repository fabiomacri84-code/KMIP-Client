#!/usr/bin/env python3
"""Web UI minimale per il client KMIP di test (Flask)."""

import argparse
import glob
import os
import re
import secrets
import struct
import time

from flask import Flask, render_template, request, session

from templates.translations import t
from app_paths import certificates_directory, write_private_file
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID

DEFAULT_LANG = "it"

import kmip_lib
from app_version import __version__

app = Flask(__name__)
app.jinja_env.filters["filename"] = os.path.basename
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
CERTS_DIR = certificates_directory()
CERTS_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)


def cert_path(name):
    return str(CERTS_DIR / name)

@app.context_processor
def app_metadata():
    return {"app_version": __version__}


PASSWORDS = {}


def password_scope(ctx):
    return (ctx["host"], str(ctx["port"]), ctx["username"])


def saved_password(ctx):
    token = session.get("password_token")
    entry = PASSWORDS.get(token)
    if entry and entry[0] == password_scope(ctx):
        return entry[1]
    return None


DEFAULTS = {
    "host": os.environ.get("KMIP_HOST", ""),
    "port": os.environ.get("KMIP_PORT", "5696"),
    "ca": os.environ.get("KMIP_CA", cert_path("ctm-ca.pem")),
    "cert": os.environ.get("KMIP_CERT", cert_path("client.crt")),
    "key": os.environ.get("KMIP_KEY", cert_path("client.key")),
    "username": os.environ.get("KMIP_USERNAME", ""),
    "kmip_version": os.environ.get("KMIP_VERSION", "1.4"),
    "name": "",
    "uid": "",
    "data": "",
    "data_hex": "",
    "algorithm": "AES",
    "length": "256",
    "reason": "CESSATION_OF_OPERATION",
    "csr_cn": "",
    "cert_pem": "",
}

FIELDS = ["host", "port", "ca", "cert", "key", "username", "kmip_version",
          "name", "uid", "data", "data_hex", "algorithm", "length", "reason",
          "csr_cn"]

# Operazioni che producono/usano un UID: dopo di esse l'UID viene memorizzato
# in sessione e riutilizzato automaticamente se l'utente non lo inserisce a mano.
UID_PRODUCER_OPS = ("create", "demo", "locate")
UID_CONSUMER_OPS = ("activate", "get", "encrypt", "decrypt", "revoke", "destroy")


def context():
    ctx = dict(DEFAULTS)
    # Percorsi dinamici dalla sessione (dopo import certificato o generazione CSR)
    if session.get("last_cert_path"):
        ctx["cert"] = session["last_cert_path"]
    if session.get("last_key_path"):
        ctx["key"] = session["last_key_path"]
    if request.method == "POST":
        for field in FIELDS:
            if field in request.form:
                ctx[field] = request.form.get(field, "")
        # cert_pem è un textarea, non in FIELDS
        if "cert_pem" in request.form:
            ctx["cert_pem"] = request.form.get("cert_pem", "")
    ctx["insecure"] = request.form.get("insecure") == "on"
    ctx["destroy"] = request.form.get("destroy") == "on"
    ctx["certs_ready"] = session.get("certs_ready", not os.path.exists(cert_path("client.key")))
    # UID automatico: se non inserito a mano, usa l'ultimo memorizzato
    if not ctx.get("uid") and session.get("last_uid"):
        ctx["uid"] = session["last_uid"]
    if request.method == "POST":
        if request.form.get("op") in ("forget_password", "reset_certs"):
            PASSWORDS.pop(session.pop("password_token", None), None)
        elif request.form.get("password"):
            token = session.get("password_token") or secrets.token_urlsafe(32)
            session["password_token"] = token
            PASSWORDS[token] = (password_scope(ctx), request.form["password"])
    ctx["password_saved"] = saved_password(ctx) is not None
    return ctx


def require(value, label):
    if not value:
        raise ValueError("campo obbligatorio: %s" % label)


def _generate_csr(ctx, lang):
    """Genera chiave privata + CSR in locale con openssl (nessun server KMIP)."""
    if not session.get("certs_ready", not os.path.exists(cert_path("client.key"))):
        raise ValueError(t("msg.csr.prereq", lang=lang))
    cn = ctx.get("csr_cn") or "kmipclient"
    ts = int(time.time())
    key_path = cert_path(f"client_{ts}.key")
    csr_path = cert_path(f"client_{ts}.csr")
    try:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        csr = (x509.CertificateSigningRequestBuilder()
               .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)]))
               .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False)
               .sign(private_key, hashes.SHA256()))
        key_pem = private_key.private_bytes(serialization.Encoding.PEM,
                                          serialization.PrivateFormat.TraditionalOpenSSL,
                                          serialization.NoEncryption())
        csr = csr.public_bytes(serialization.Encoding.PEM).decode('ascii')
        write_private_file(key_path, key_pem)
        write_private_file(csr_path, csr.encode('ascii'))
        client_key_path = cert_path("client.key")
        write_private_file(client_key_path, key_pem)
    except Exception as exc:
        raise ValueError(t("msg.csr.error", lang=lang, exc=exc)) from exc
    session["certs_ready"] = False
    session["last_key_path"] = client_key_path
    return (
        t("msg.csr.generated", lang=lang, cn=cn, key_path=key_path,
          csr_path=csr_path, csr=csr)
    )


def _reset_certs(lang):
    """Cancella tutti i certificati/CSR/chiave in /certs."""
    removed = []
    for pattern in ("*.crt", "*.key", "*.csr", "*.pem", "*.cer", "*.cert"):
        for f in glob.glob(str(CERTS_DIR / pattern)):
            try:
                os.remove(f)
                removed.append(os.path.basename(f))
            except Exception:
                pass
    session["certs_ready"] = True
    session["last_uid"] = None
    session["last_cert_path"] = None
    session["last_key_path"] = None
    if removed:
        return t("msg.reset.done", lang=lang, files=", ".join(removed))
    return t("msg.reset.empty", lang=lang)


def _import_cert(ctx, lang):
    """Importa il certificato firmato (PEM) in /certs/client.crt."""
    pem = (ctx.get("cert_pem") or "").strip()
    if not pem:
        raise ValueError(t("msg.import.empty", lang=lang))
    if "BEGIN CERTIFICATE" not in pem:
        raise ValueError(t("msg.import.invalid", lang=lang))
    path = cert_path("client.crt")
    try:
        with open(path, "w") as f:
            f.write(pem)
        os.chmod(path, 0o644)
        session["certs_ready"] = False
        session["last_uid"] = None
        session["last_cert_path"] = path
        return t("msg.import.done", lang=lang, path=path)
    except Exception as exc:
        raise ValueError(t("msg.import.error", lang=lang, exc=exc))


def _upload_file(uploaded, dest_path, label, lang):
    """Salva un file caricato via form in dest_path."""
    if not uploaded or uploaded.filename == "":
        raise ValueError(t("msg.upload.nofile", lang=lang, label=label))
    try:
        uploaded.save(dest_path)
        os.chmod(dest_path, 0o644)
        return t("msg.upload.done", lang=lang, label=label, path=dest_path)
    except Exception as exc:
        raise ValueError(t("msg.upload.error", lang=lang, label=label, exc=exc))


def _upload_ca_cert(request, lang):
    """Carica il certificato CA del server."""
    f = request.files.get("ca_file")
    if not f or f.filename == "":
        raise ValueError(t("msg.upload.nofile", lang=lang, label="CA server"))
    content = f.read().decode("utf-8", errors="ignore")
    f.seek(0)
    if "BEGIN CERTIFICATE" not in content:
        raise ValueError(t("msg.upload.invalid", lang=lang))
    return _upload_file(f, cert_path("ctm-ca.pem"), "CA server", lang)


def _upload_client_cert(request, lang):
    """Carica il certificato client firmato."""
    f = request.files.get("client_cert_file")
    if not f or f.filename == "":
        raise ValueError(t("msg.upload.nofile", lang=lang, label="certificato client"))
    content = f.read().decode("utf-8", errors="ignore")
    f.seek(0)
    if "BEGIN CERTIFICATE" not in content:
        raise ValueError(t("msg.upload.invalid", lang=lang))
    return _upload_file(f, cert_path("client.crt"), "certificato client", lang)


def _upload_client_key(request, lang):
    """Importa una chiave privata PEM verificandola prima della scrittura."""
    uploaded = request.files.get("client_key_file")
    if not uploaded or not uploaded.filename:
        raise ValueError(t("msg.key.upload.nofile", lang=lang))
    content = uploaded.read()
    if b"PRIVATE KEY-----" not in content:
        raise ValueError(t("msg.key.upload.error", lang=lang))
    try:
        serialization.load_pem_private_key(content, password=None)
    except (ValueError, TypeError) as exc:
        raise ValueError(t("msg.key.upload.error", lang=lang)) from exc
    path = cert_path("client.key")
    write_private_file(path, content)
    session["last_key_path"] = path
    return t("msg.key.upload.done", lang=lang)


def _extract_uid(result, op):
    """Estrae l'UID dal risultato di un'operazione, se presente."""
    if op in ("create", "demo"):
        m = re.search(r"UID:\s*([0-9a-fA-F\-]+)", result)
        if m:
            return m.group(1)
    if op == "locate":
        m = re.search(r"Trovati:\s*\[([^\]]*)\]", result)
        if m:
            m2 = re.search(r"'([0-9a-fA-F\-]+)'", m.group(1))
            if m2:
                return m2.group(1)
    return None


def run_op(op, ctx):
    lang = ctx.get("lang", DEFAULT_LANG)
    if op == "forget_password":
        return "Password dimenticata. Inseriscila alla prossima connessione."
    if op == "reset_certs":
        return _reset_certs(lang)

    if op == "generate_csr":
        return _generate_csr(ctx, lang)

    if op == "import_cert":
        return _import_cert(ctx, lang)

    if op == "upload_ca_cert":
        return _upload_ca_cert(request, lang)

    if op == "upload_client_cert":
        return _upload_client_cert(request, lang)

    if op == "upload_client_key":
        return _upload_client_key(request, lang)

    password = saved_password(ctx)
    client = kmip_lib.connect(
        ctx["host"],
        ctx["port"],
        cert=ctx["cert"] or None,
        key=ctx["key"] or None,
        ca=ctx["ca"] or None,
        username=ctx["username"] or None,
        password=password,
        insecure=ctx["insecure"],
        kmip_version=ctx["kmip_version"],
    )
    try:
        if op == "ping":
            return "OK: handshake TLS completato con %s:%s" % (
                ctx["host"], ctx["port"])

        if op == "demo":
            lines = kmip_lib.demo(
                client,
                name=ctx["name"] or None,
                destroy_at_end=ctx["destroy"],
                username=ctx["username"],
            )
            result = "\n".join(lines)
            uid = _extract_uid(result, "demo")
            if uid:
                session["last_uid"] = uid
            return result

        if op == "create":
            require(ctx["name"], "name")
            uid = kmip_lib.create_key(
                client, ctx["name"], ctx["algorithm"], int(ctx["length"] or 256))
            session["last_uid"] = uid
            return t("msg.create.done", lang=lang, uid=uid)

        if op == "locate":
            uids = kmip_lib.locate(client, ctx["name"] or None)
            if uids:
                session["last_uid"] = uids[0]
                return t("msg.locate.done", lang=lang, uids=", ".join(uids))
            return t("msg.locate.none", lang=lang)

        # Operazioni che consumano UID: usa quello in sessione se non fornito
        if op in UID_CONSUMER_OPS and not ctx.get("uid") and session.get("last_uid"):
            ctx["uid"] = session["last_uid"]

        if op == "activate":
            require(ctx["uid"], "uid")
            kmip_lib.activate(client, ctx["uid"])
            return "Chiave attivata: %s" % ctx["uid"]

        if op == "get":
            require(ctx["uid"], "uid")
            info = kmip_lib.get_object(client, ctx["uid"])
            lines = [t("result.field", lang=lang, label="tipo", value=info["type"]),
                     t("result.field", lang=lang, label="uid", value=ctx["uid"])]
            if info["algorithm"]:
                lines.append(t("result.field", lang=lang, label="algoritmo", value=info["algorithm"]))
            if info["length"]:
                lines.append(t("result.field", lang=lang, label="lunghezza", value="%s bit" % info["length"]))
            if info["value_hex"]:
                lines.append(t("result.field", lang=lang, label="materiale", value=info["value_hex"]))
            return "\n".join(lines)

        if op == "encrypt":
            require(ctx["uid"], "uid")
            require(ctx["data"], "data")
            ciphertext, iv = kmip_lib.encrypt(
                client, ctx["uid"], ctx["data"].encode())
            return "ciphertext: %s\niv:         %s" % (
                ciphertext.hex(), iv.hex() if iv else "-")

        if op == "decrypt":
            require(ctx["uid"], "uid")
            require(ctx["data_hex"], "data-hex")
            plaintext = kmip_lib.decrypt(
                client, ctx["uid"], bytes.fromhex(ctx["data_hex"]))
            return "plaintext: %s" % plaintext.decode(errors="replace")

        if op == "revoke":
            require(ctx["uid"], "uid")
            kmip_lib.revoke(client, ctx["uid"], ctx["reason"])
            return "Revocata: %s (%s)" % (ctx["uid"], ctx["reason"])

        if op == "destroy":
            require(ctx["uid"], "uid")
            kmip_lib.destroy(client, ctx["uid"])
            session.pop("last_uid", None)
            return t("msg.destroy.done", lang=lang, uid=ctx["uid"])

        raise ValueError(t("msg.error.unknown_op", lang=lang, op=op))
    finally:
        client.close()


@app.route("/", methods=["GET", "POST"])
def index():
    ctx = context()
    if request.method == "POST":
        op = request.form.get("op", "")
        try:
            ctx["result"] = run_op(op, ctx)
            ctx["ok"] = True
        except Exception as exc:
            app.logger.exception(
                "Operazione %s fallita: server=%s:%s KMIP=%s utente=%s",
                op, ctx["host"], ctx["port"], ctx["kmip_version"],
                ctx["username"] or "solo certificato",
            )
            ctx["result"] = t("msg.error.generic", lang=ctx.get("lang", DEFAULT_LANG),
                              exc_type=type(exc).__name__, exc=exc)
            if isinstance(exc, struct.error):
                ctx["result"] = (
                    "Operazione «%s» fallita: risposta KMIP non decodificabile.\n"
                    "Dettaglio: %s\n"
                    "Il dettaglio tecnico è stato registrato nei log del client."
                ) % (op, exc)
            ctx["ok"] = False
    # Dopo un'operazione riuscita, l'UID prodotto è subito disponibile nel form.
    if request.method == "POST" and ctx.get("ok") and session.get("last_uid"):
        ctx["uid"] = session["last_uid"]
    # Rileggi la cartella dopo ogni operazione, inclusi upload, CSR e reset.
    files = sorted(path for path in glob.glob(str(CERTS_DIR / "*")) if os.path.isfile(path))
    certificates, keys = [], []
    for path in files:
        try:
            with open(path, "rb") as stream:
                prefix = stream.read(4096)
        except OSError:
            continue
        if b"-----BEGIN CERTIFICATE-----" in prefix:
            certificates.append(path)
        if b"PRIVATE KEY-----" in prefix:
            keys.append(path)
    ctx["cert_files"] = {"ca": certificates, "cert": certificates, "key": keys}
    ctx["certs_ready"] = session.get("certs_ready", not os.path.exists(cert_path("client.key")))
    ctx["selected_files"] = {}
    for field in ("ca", "cert", "key"):
        if request.method == "POST" and op == "reset_certs":
            ctx[field] = ""
        elif request.method == "POST" and ctx.get("ok") and op in ("generate_csr", "upload_client_key") and field == "key":
            ctx[field] = session.get("last_key_path") or ctx[field]
        elif request.method == "POST" and ctx.get("ok") and op in ("import_cert", "upload_client_cert") and field == "cert":
            ctx[field] = cert_path("client.crt")
        elif request.method == "POST" and ctx.get("ok") and op == "upload_ca_cert" and field == "ca":
            ctx[field] = cert_path("ctm-ca.pem")
        ctx["selected_files"][field] = ctx[field]
    ctx["certs_directory"] = str(CERTS_DIR)
    save_settings = app.config.get("SAVE_SETTINGS")
    if request.method == "POST" and save_settings:
        save_settings(ctx)
    return render_template("index.html", **ctx)


@app.route("/readme")
def readme():
    return render_template("readme.html")


def main():
    parser = argparse.ArgumentParser(description="Web UI per KMIP test client")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
