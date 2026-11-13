#!/usr/bin/env python3
"""
Client KMIP di test per CipherTrust Manager (CLI, basato su PyKMIP).

Esempi:
    ./kmip_test.py --host 192.168.6.50 --ca /certs/ctm-ca.pem \
        --cert /certs/client.crt --key /certs/client.key demo

    ./kmip_test.py ... create --name chiave1
    ./kmip_test.py ... locate --name chiave1
    ./kmip_test.py ... get --uid <UID>
    ./kmip_test.py ... revoke --uid <UID>
    ./kmip_test.py ... destroy --uid <UID>
"""

import argparse
import logging
import sys

from kmip.core import enums
import kmip_lib

# PyKMIP è verboso quando non trova un file di configurazione.
logging.getLogger("kmip").setLevel(logging.ERROR)


def cmd_demo(client, args):
    for line in kmip_lib.demo(
        client,
        name=args.name,
        destroy_at_end=args.destroy,
        username=args.username,
    ):
        print(line)


def cmd_create(client, args):
    print(kmip_lib.create_key(client, args.name, args.algorithm, args.length))


def cmd_locate(client, args):
    for uid in kmip_lib.locate(client, args.name):
        print(uid)


def cmd_get(client, args):
    info = kmip_lib.get_object(client, args.uid)
    print("tipo:      %s" % info["type"])
    print("uid:       %s" % args.uid)
    if info["algorithm"]:
        print("algoritmo: %s" % info["algorithm"])
    if info["length"]:
        print("lunghezza: %s bit" % info["length"])
    if info["value_hex"]:
        print("materiale: %s" % info["value_hex"])


def cmd_activate(client, args):
    kmip_lib.activate(client, args.uid)
    print("attivata: %s" % args.uid)


def cmd_revoke(client, args):
    kmip_lib.revoke(client, args.uid, args.reason)
    print("revocata: %s (%s)" % (args.uid, args.reason))


def cmd_destroy(client, args):
    kmip_lib.destroy(client, args.uid)
    print("distrutta: %s" % args.uid)


def cmd_encrypt(client, args):
    ciphertext, iv = kmip_lib.encrypt(client, args.uid, args.data.encode())
    print("ciphertext: %s" % ciphertext.hex())
    if iv:
        print("iv:         %s" % iv.hex())


def cmd_decrypt(client, args):
    plaintext = kmip_lib.decrypt(
        client, args.uid, bytes.fromhex(args.data_hex)
    )
    print("plaintext: %s" % plaintext.decode(errors="replace"))


COMMANDS = {
    "demo": cmd_demo,
    "create": cmd_create,
    "activate": cmd_activate,
    "locate": cmd_locate,
    "get": cmd_get,
    "revoke": cmd_revoke,
    "destroy": cmd_destroy,
    "encrypt": cmd_encrypt,
    "decrypt": cmd_decrypt,
}


def build_parser():
    parser = argparse.ArgumentParser(
        description="Client KMIP di test per CipherTrust Manager",
        epilog="Esempio: kmip_test.py --host 192.168.6.50 --ca /certs/ctm-ca.pem "
               "--cert /certs/client.crt --key /certs/client.key demo",
    )
    parser.add_argument("command", choices=COMMANDS,
                        help="operazione da eseguire")
    parser.add_argument("--host", default="127.0.0.1",
                        help="host/IP del CipherTrust Manager")
    parser.add_argument("--port", type=int, default=5696,
                        help="porta KMIP (default 5696)")
    parser.add_argument("--cert", help="certificato client (PEM)")
    parser.add_argument("--key", help="chiave privata client (PEM)")
    parser.add_argument("--ca", help="CA che ha firmato il certificato server")
    parser.add_argument("--username",
                        help="utente KMIP (CN del certificato) se l'interfaccia "
                             "richiede l'autenticazione con password")
    parser.add_argument("--password", help="password dell'utente KMIP")
    parser.add_argument("--insecure", action="store_true",
                        help="non verificare il certificato server (solo test)")
    parser.add_argument("--kmip-version", default="1.4",
                        choices=kmip_lib.VERSIONS,
                        help="versione KMIP (default 1.4)")
    parser.add_argument("--name", help="nome dell'oggetto")
    parser.add_argument("--uid", help="unique identifier dell'oggetto")
    parser.add_argument("--algorithm", default="AES",
                        choices=["AES", "TDES", "HMAC_SHA256", "HMAC_SHA384",
                                 "HMAC_SHA512"])
    parser.add_argument("--length", type=int, default=256,
                        help="lunghezza chiave in bit (default 256)")
    parser.add_argument("--data", help="stringa da cifrare")
    parser.add_argument("--data-hex", help="dati esadecimali da decifrare")
    parser.add_argument("--destroy", action="store_true",
                        help="con 'demo', distrugge la chiave al termine")
    parser.add_argument("--reason", default="CESSATION_OF_OPERATION",
                        choices=["CESSATION_OF_OPERATION", "KEY_COMPROMISE",
                                 "CA_COMPROMISE", "AFFILIATION_CHANGED",
                                 "SUPERSEDED", "PRIVILEGE_WITHDRAWN"],
                        help="motivo per il comando revoke")
    return parser


def main():
    args = build_parser().parse_args()

    if args.command in ("activate", "get", "revoke", "destroy", "encrypt", "decrypt") \
            and not args.uid:
        print("ERRORE: --uid è obbligatorio per il comando %s" % args.command,
              file=sys.stderr)
        return 2
    if args.command == "create" and not args.name:
        print("ERRORE: --name è obbligatorio per il comando create",
              file=sys.stderr)
        return 2
    if args.command == "encrypt" and args.data is None:
        print("ERRORE: --data è obbligatorio per il comando encrypt",
              file=sys.stderr)
        return 2
    if args.command == "decrypt" and args.data_hex is None:
        print("ERRORE: --data-hex è obbligatorio per il comando decrypt",
              file=sys.stderr)
        return 2

    try:
        client = kmip_lib.connect(
            args.host,
            args.port,
            cert=args.cert,
            key=args.key,
            ca=args.ca,
            username=args.username,
            password=args.password,
            insecure=args.insecure,
            kmip_version=args.kmip_version,
        )
    except Exception as exc:
        print("ERRORE di connessione: %s: %s"
              % (type(exc).__name__, exc), file=sys.stderr)
        return 1

    try:
        COMMANDS[args.command](client, args)
    except Exception as exc:
        print("ERRORE: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 1
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
