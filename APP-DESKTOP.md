# KMIP Test Client — applicazione desktop

La stessa interfaccia italiana e lo stesso motore PyKMIP sono eseguiti in una finestra dedicata. Il pacchetto include Python, le librerie KMIP e il motore della finestra: non occorrono Podman, Python o il comando openssl sul computer dove si usa l'app.

Le build versionate sono disponibili nella sezione [Releases di KMIP-Client](https://github.com/fabiomacri84-code/KMIP-Client/releases/latest). La versione compare in piccolo nell’intestazione della GUI e nella guida.

## Uso

1. Estrai il pacchetto per il tuo sistema. Mantieni tutta la cartella estratta, compresa `_internal`.
2. Su Windows apri `kmip-test-client.exe`; su Linux apri `kmip-test-client`; su macOS apri `KMIP Test Client.app`.
3. Al primo avvio non sono presenti certificati o chiavi private: carica tu CA del server, certificato client e chiave privata dai pulsanti della pagina. Nessuna identità del laboratorio viene precaricata. Le build bloccano la distribuzione se trovano chiavi private, certificati del laboratorio o configurazioni locali nel pacchetto.
4. Inserisci l'indirizzo di CTM e lascia KMIP 1.4 per l'ambiente verificato.
5. Per i sottodomini usa il percorso manuale: **KMIP > Client profile > Certificate detail**, CN `sottodominio|sottodominio||kmiputente`, poi **Registered Clients** con registrazione manuale e download diretto di certificato e chiave privata, senza CSR. Se richiesto, Utente KMIP deve contenere lo stesso CN completo.
6. Apri **Guida** nella finestra per la procedura completa, poi verifica la connessione ed esegui il test.
7. Chiudi la finestra per terminare l'app e il server locale. La password resta solo in memoria fino alla chiusura.

Host, porta, versione, utente e selezione dei file vengono ricordati tra gli avvii. La password non viene scritta nella configurazione.

Per l’integrazione vSphere descritta nella guida di riferimento, abilita `TLS_RSA_WITH_AES_256_CBC_SHA` in **Admin Settings > Interfaces > KMIP > View/Edit**, spostandola dalle suite disabilitate a quelle abilitate; salva e riavvia **nae-kmip** attendendo lo stato verde. Il nostro client non richiede né usa questa suite con la configurazione TLS predefinita: conserva anche le suite ECDHE/GCM. Per versioni o profili TLS diversi di vSphere, verifica i requisiti specifici.

## Dove si trovano i dati

| Sistema | Cartella |
|---|---|
| Windows | `%LOCALAPPDATA%\KMIP Test Client` |
| Linux | `$XDG_DATA_HOME/kmip-test-client`, normalmente `~/.local/share/kmip-test-client` |
| macOS | `~/Library/Application Support/KMIP Test Client` |

All'interno: `certs/` contiene certificati e chiavi private, `settings.json` le impostazioni, `client.log` gli errori. La cartella dei certificati è mostrata anche nella pagina. L'aggiornamento dell'eseguibile non cancella i dati.

Il server interno sceglie una porta libera, ascolta soltanto su `127.0.0.1` e richiede una sessione autorizzata dalla finestra. L'app non occupa necessariamente la porta 8080 e può convivere con la precedente Web UI.

Il pulsante **Reset client** elimina i certificati e le chiavi private dalla cartella dell'app; non elimina le chiavi custodite su CTM. **Distruggi chiave** invia KMIP Destroy: CTM può conservare nome, UID e metadati nello stato Destroyed dopo aver distrutto il materiale crittografico.

## Costruire i pacchetti

Le build native si eseguono su ciascun sistema, con Python 3.12:

```text
python -m pip install -r requirements-build.txt
python -m unittest discover -s tests -v
python packaging/build.py
```

Il comando produce in `dist/` una cartella eseguibile e un archivio per la distribuzione. Verifica inoltre l'eseguibile con `--self-test`, senza connettersi a CTM o usare i certificati reali.

- Windows: archivio ZIP contenente l'eseguibile e le sue librerie.
- Linux x86_64: archivio TAR.GZ contenente l'eseguibile e le sue librerie.
- macOS: archivio ZIP contenente il bundle `.app`; l'architettura corrisponde al Mac usato per costruirlo. La matrice automatica usa macOS ARM64.

La configurazione `.github/workflows/desktop.yml` prepara automaticamente i tre pacchetti quando viene eseguita in un repository GitHub con Actions abilitato. Si avvia manualmente da Actions o con un tag `v*`. I tag pubblicano la release soltanto dopo il completamento di tutte e tre le build e dei test; gli archivi includono il numero di versione. Le esecuzioni manuali eseguono test e build senza pubblicare release. Le build dei tag vengono caricate direttamente in una release provvisoria, senza usare lo spazio degli artefatti Actions; la release viene pubblicata solo se tutte riescono.

I pacchetti Windows e macOS non sono firmati con certificati di distribuzione. Per una distribuzione aziendale firmata servono le credenziali di firma del rispettivo sistema. Non sono state usate o incluse credenziali del laboratorio.

### Linux: build riproducibile in container

```bash
podman build -f packaging/Containerfile -t localhost/kmip-desktop-builder .
podman run --rm -v "$PWD:/work:rw,Z" localhost/kmip-desktop-builder python -m unittest discover -s tests -v
podman run --rm -v "$PWD:/work:rw,Z" localhost/kmip-desktop-builder python packaging/build.py
```

Il builder usa Debian 12 e Python 3.12. Il pacchetto Linux richiede un ambiente desktop x86_64 moderno con glibc >= 2.36 e le normali librerie grafiche X11/Wayland, OpenGL/EGL, NSS e ALSA. Non è un pacchetto per Alpine/musl o server senza interfaccia grafica.

### Avvio dai sorgenti

```text
python -m pip install -r requirements-desktop.txt
python desktop.py
```

Per usare una cartella dati diversa:

```text
python desktop.py --data-dir /percorso/dati
```

Anche l'eseguibile distribuito accetta `--data-dir` e `--self-test`.
