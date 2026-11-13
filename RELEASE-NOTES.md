Prima release di **KMIP-Client**, applicazione desktop per i test di integrazione tra Thales CipherTrust Manager e client KMIP.

Scarica l’archivio del tuo sistema, estrailo e avvia l’app. Python e il motore della finestra sono inclusi; non servono Podman né il comando openssl. Mantieni tutta la cartella estratta, compresa `_internal`.

- **Windows x64:** `kmip-test-client.exe`.
- **Linux x64:** `kmip-test-client`.
- **macOS Apple Silicon (ARM64):** `KMIP Test Client.app`.

La versione compare in piccolo nella GUI. Le nuove installazioni non includono certificati, chiavi private o impostazioni del laboratorio. Gli aggiornamenti mantengono i dati già importati dall’utente nella propria cartella dati.

La guida inclusa descrive il percorso manuale nei sottodomini, il CN `sottodominio|sottodominio||kmiputente` e la ciphersuite `TLS_RSA_WITH_AES_256_CBC_SHA` prevista dalla guida vSphere di riferimento. L’app PyKMIP non richiede quella suite con la configurazione TLS predefinita.

Le build Windows e macOS non sono firmate con certificati di distribuzione. La build Linux richiede un desktop x86_64 con glibc >= 2.36 e le normali librerie grafiche di sistema. Per tutti i dettagli consulta `APP-DESKTOP.md` e `CHANGELOG.md` nel repository.
