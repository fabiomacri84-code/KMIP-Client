# Versioni

Il numero della versione è definito in `app_version.py` e compare in piccolo nella GUI.

## 1.0.2 — 2026-11-13

Prima distribuzione delle tre build; caricamento diretto in release provvisoria per non dipendere dalla quota degli artefatti Actions. Pubblicazione soltanto dopo verifica di tutti i pacchetti.

## 1.0.1 — 2026-11-13 (preparazione, non pubblicata)

Configurazione delle tre build. Aggiornato il runner macOS a macOS 15 ARM64; versione riportata nella GUI e negli archivi.

## 1.0.0 — 2026-11-13 (baseline, non pubblicata)

Prima release desktop per Windows x64, Linux x64 e macOS Apple Silicon (ARM64).

- Finestra dedicata con icona dell’app e interfaccia interamente in italiano.
- Connessione mTLS a CipherTrust Manager con PyKMIP e KMIP 1.4.
- Create, Activate, Locate, Get, Encrypt, Decrypt, Revoke e Destroy.
- Test completo con confronto dei dati decifrati e pulizia opzionale della chiave.
- Pulsante per copiare il solo ciphertext negli appunti.
- Upload e selezione di CA, certificato client e chiave privata; nuove installazioni prive di credenziali.
- Generazione locale della CSR senza dipendere dal comando openssl.
- Password conservata soltanto in memoria durante la sessione.
- Errori CTM di autenticazione recuperati anche dalle risposte con intestazione incompleta.
- Guida per sottodomini: CN `sottodominio|sottodominio||kmiputente`, registrazione manuale e download di certificato/chiave senza CSR.
- Nota sulla ciphersuite `TLS_RSA_WITH_AES_256_CBC_SHA` da abilitare per la procedura vSphere di riferimento, distinta dal TLS dell’app.
- Build native e pubblicazione automatica delle release dopo i controlli.
