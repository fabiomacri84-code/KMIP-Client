"""Operazioni KMIP condivise tra CLI e Web UI (basate su PyKMIP)."""

import ssl

from kmip.core import enums
from kmip.core.factories.attributes import AttributeFactory
from kmip.pie.client import ProxyKmipClient
from kmip.services.kmip_protocol import KMIPProtocol


class KmipServerError(RuntimeError):
    """Rifiuto CTM recuperato da una risposta con intestazione incompleta."""


def _ttlv_fields(data):
    offset = 0
    while offset < len(data):
        if offset + 8 > len(data):
            raise ValueError("Intestazione TTLV incompleta")
        tag = int.from_bytes(data[offset:offset + 3], "big")
        kind = data[offset + 3]
        length = int.from_bytes(data[offset + 4:offset + 8], "big")
        end = offset + 8 + length
        padded_end = offset + 8 + ((length + 7) // 8) * 8
        if padded_end > len(data):
            raise ValueError("Valore TTLV incompleto")
        yield tag, kind, data[offset + 8:end]
        offset = padded_end


class DiagnosticProtocol(KMIPProtocol):
    def read(self):
        data = super().read()
        # CTM può omettere BatchCount nelle risposte di errore. PyKMIP
        # fallirebbe prima di leggere ResultReason e ResultMessage.
        try:
            outer = list(_ttlv_fields(bytes(data.buffer)))
            if len(outer) != 1 or outer[0][0] != enums.Tags.RESPONSE_MESSAGE.value:
                return data
            fields = list(_ttlv_fields(outer[0][2]))
            header = next(value for tag, kind, value in fields
                          if tag == enums.Tags.RESPONSE_HEADER.value)
            if any(tag == enums.Tags.BATCH_COUNT.value
                   for tag, kind, value in _ttlv_fields(header)):
                return data
            for tag, kind, value in fields:
                if tag != enums.Tags.BATCH_ITEM.value:
                    continue
                batch = {tag: value for tag, kind, value in _ttlv_fields(value)}
                status = int.from_bytes(batch.get(enums.Tags.RESULT_STATUS.value, b""), "big")
                if status != enums.ResultStatus.OPERATION_FAILED.value:
                    continue
                reason_code = int.from_bytes(batch.get(enums.Tags.RESULT_REASON.value, b""), "big")
                try:
                    reason = enums.ResultReason(reason_code).name
                except ValueError:
                    reason = "codice %s" % reason_code
                message = batch.get(enums.Tags.RESULT_MESSAGE.value, b"").decode("utf-8", "replace")
                hint = ""
                if reason_code == enums.ResultReason.AUTHENTICATION_NOT_SUCCESSFUL.value:
                    hint = " Controlla nome utente, password e associazione del certificato client su CTM."
                raise KmipServerError("CTM ha rifiutato la richiesta: %s. %s%s" % (reason, message, hint))
        except (ValueError, StopIteration):
            # Lascia a PyKMIP la gestione delle risposte non riconosciute.
            pass
        return data

VERSIONS = {
    "1.0": enums.KMIPVersion.KMIP_1_0,
    "1.1": enums.KMIPVersion.KMIP_1_1,
    "1.2": enums.KMIPVersion.KMIP_1_2,
    "1.3": enums.KMIPVersion.KMIP_1_3,
    "1.4": enums.KMIPVersion.KMIP_1_4,
    "2.0": enums.KMIPVersion.KMIP_2_0,
}

# CipherTrust Manager richiede parametri espliciti per Encrypt/Decrypt.
CRYPTO_PARAMS = {
    "cryptographic_algorithm": enums.CryptographicAlgorithm.AES,
    "block_cipher_mode": enums.BlockCipherMode.ECB,
    "padding_method": enums.PaddingMethod.PKCS5,
}

USAGE_MASK = [
    enums.CryptographicUsageMask.ENCRYPT,
    enums.CryptographicUsageMask.DECRYPT,
    enums.CryptographicUsageMask.WRAP_KEY,
    enums.CryptographicUsageMask.UNWRAP_KEY,
]


def connect(host, port=5696, cert=None, key=None, ca=None, username=None,
            password=None, insecure=False, kmip_version="1.4"):
    """Apre una connessione KMIP (mTLS) e restituisce il client aperto."""
    kwargs = {
        "hostname": host,
        "port": int(port),
        "kmip_version": VERSIONS[kmip_version],
    }
    if cert:
        kwargs["cert"] = cert
    if key:
        kwargs["key"] = key
    if ca:
        kwargs["ca"] = ca
    if username:
        kwargs["username"] = username
        kwargs["password"] = password or ""

    client = ProxyKmipClient(**kwargs)
    if insecure:
        # ProxyKmipClient non espone cert_reqs: lo impostiamo sul proxy.
        client.proxy.cert_reqs = ssl.CERT_NONE
    client.open()
    client.proxy.protocol = DiagnosticProtocol(client.proxy.socket)
    return client


def _name_attributes(name):
    factory = AttributeFactory()
    return [factory.create_attribute(enums.AttributeType.NAME, name)]


def create_key(client, name, algorithm="AES", length=256):
    return client.create(
        getattr(enums.CryptographicAlgorithm, algorithm),
        int(length),
        name=name,
        cryptographic_usage_mask=USAGE_MASK,
    )


def locate(client, name=None):
    attributes = _name_attributes(name) if name else None
    return client.locate(attributes=attributes)


def get_object(client, uid):
    obj = client.get(uid)
    value = getattr(obj, "value", None)
    algorithm = getattr(obj, "cryptographic_algorithm", None)
    length = getattr(obj, "cryptographic_length", None)
    return {
        "type": type(obj).__name__,
        "algorithm": algorithm.name if algorithm else None,
        "length": length,
        "value_hex": value.hex() if value else None,
    }


def activate(client, uid):
    client.activate(uid)


def revoke(client, uid, reason="CESSATION_OF_OPERATION"):
    client.revoke(getattr(enums.RevocationReasonCode, reason), uid=uid)


def destroy(client, uid):
    client.destroy(uid)


def encrypt(client, uid, data):
    ciphertext, iv = client.encrypt(
        data, uid=uid, cryptographic_parameters=CRYPTO_PARAMS
    )
    return ciphertext, iv


def decrypt(client, uid, ciphertext):
    return client.decrypt(
        ciphertext, uid=uid, cryptographic_parameters=CRYPTO_PARAMS
    )


def demo(client, name=None, destroy_at_end=False, username=None):
    """Esegue un ciclo KMIP completo e restituisce le righe di log."""
    import time

    name = name or "vsphere-test-%d" % int(time.time())
    plaintext = b"CipherTrust Manager - KMIP integration test"
    lines = []

    lines.append("[1/5] Creo una chiave AES-256 con nome %r" % name)
    uid = create_key(client, name)
    lines.append("      UID: %s" % uid)

    lines.append("[2/5] Attivo la chiave")
    activate(client, uid)
    lines.append("      OK")

    lines.append("[3/5] Ricerca per nome (Locate) e lettura (Get)")
    lines.append("      trovati: %s" % (locate(client, name),))
    info = get_object(client, uid)
    lines.append(
        "      %s, algoritmo=%s, lunghezza=%s bit"
        % (info["type"], info["algorithm"], info["length"])
    )
    lines.append("      materiale: %s" % info["value_hex"])

    lines.append("[4/5] Encrypt/Decrypt AES")
    ciphertext, iv = encrypt(client, uid, plaintext)
    decrypted = decrypt(client, uid, ciphertext)
    if decrypted != plaintext:
        raise RuntimeError("roundtrip encrypt/decrypt FALLITO")
    lines.append("      cifrati %d byte, roundtrip OK" % len(ciphertext))

    if destroy_at_end:
        lines.append("[5/5] Revoca e distruzione della chiave")
        revoke(client, uid)
        destroy(client, uid)
        lines.append("      revocata e distrutta; oggetti residui: %s"
                     % (locate(client, name),))
    else:
        lines.append("[5/5] Chiave lasciata sul server (UID %s)" % uid)
        lines.append("      Verifica su CTM: Keys -> Owner = local|%s"
                     % (username or "<CN del certificato>"))

    lines.append("")
    lines.append("Integrazione KMIP OK")
    return lines
