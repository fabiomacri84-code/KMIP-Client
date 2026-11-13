# KMIP-Client — integrazione con CipherTrust Manager

**Italiano** · [English documentation](README.en.md)

Applicazione desktop in italiano per test KMIP verso Thales CipherTrust Manager (CTM).

[![Build desktop](https://github.com/fabiomacri84-code/KMIP-Client/actions/workflows/desktop.yml/badge.svg)](https://github.com/fabiomacri84-code/KMIP-Client/actions/workflows/desktop.yml)

[Scarica le build Windows, Linux e macOS](https://github.com/fabiomacri84-code/KMIP-Client/releases/latest) · [Guida desktop](APP-DESKTOP.md) · [Versioni](CHANGELOG.md)

## English documentation

An English overview, user guide and native build instructions are available in [README.en.md](README.en.md) and [docs/en](docs/en). The application interface remains in Italian.

## Applicazione desktop

L’avvio in una finestra dedicata e il packaging Windows, Linux e macOS sono descritti in [APP-DESKTOP.md](APP-DESKTOP.md). L’app gestisce i propri certificati nella cartella dati dell’utente.

Questo pacchetto replica il **livello KMIP** della guida
`[CTM] [KMIP] Integrazione vSphere_v1.0.docx` usando un client generico
(PyKMIP) in un container Podman, al posto di vCenter.

Serve a verificare:

- TLS mutuo con certificato client (come fa vCenter)
- registrazione del client su CTM (manuale o automatica)
- autenticazione con certificato e, se previsto, con password
- permessi dell'utente KMIP (`Key Users`)
- ciclo di vita delle chiavi: Create, Activate, Locate, Get, Revoke, Destroy
- comparsa delle chiavi in CTM con owner coerente con l’utente e il dominio KMIP

Non può testare ciò che è specifico di vSphere: trust reciproco
vCenter↔CTM, VM Storage Policy, VM Encryption, crittografia vSAN.

## Prerequisiti

- CTM raggiungibile sulla porta **5696** (VM accesa, rete corretta)
- licenza KMIP attiva (l'interfaccia è in prova per 90 giorni)
- Per l’app desktop: nessuna installazione di Python o Podman.
- Solo per l’alternativa in container: `podman`.

## 1. Configurazione lato CipherTrust Manager

La sequenza ricalca il documento vSphere. Per il primo test puoi usare il
dominio **root**. Se lavori nel sottodominio `vsphere` o in un altro
sottodominio, segui il percorso manuale dedicato qui sotto.

### Percorso nel dominio root con CSR

Per il percorso manuale nei sottodomini, usa invece la sezione seguente.

1. **CA locale** — `CA > Local > Add Local CA`, poi `Autofirma`.
2. **Interfaccia KMIP** — `Admin Settings > Interfaces > KMIP > View/Edit`.
   Verifica che la porta sia **5696**. Nella guida vSphere si abilita la suite
   `TLS_RSA_WITH_AES_256_CBC_SHA`: in `Disabled cipher suites` selezionala
   e spostala tra le suite abilitate, poi salva con `Update`. Questa
   impostazione serve all’integrazione vSphere descritta nella guida di
   riferimento; il client PyKMIP non la richiede e non la usa con la
   configurazione TLS predefinita. Mantieni abilitate anche le suite
   ECDHE/GCM compatibili con il client. Riavvia `nae-kmip` da
   `Admin Settings > Services` e attendi lo stato verde. Per altre versioni
   o profili TLS di vSphere, verifica i requisiti della relativa integrazione.
3. **Utente KMIP** — `Access Management > Users > Create New User`:
   - Username = **CN del certificato client** (es. `kmipclient`)
   - aggiungi l'utente al gruppo **Key Users**
4. **CSR e certificato** — sul PC:
   ```bash
   ./make-csr.sh kmipclient
   ```
   Poi su CTM: `CA > Local > (la CA) > Upload CSR`, incolla
   `certs/client.csr`, durata 3650 giorni, `Issue Certificate`.
   Scarica il certificato firmato come `certs/client.crt`.
5. **Registrazione del client**, scegli una delle due strade:
   - **Manuale**: `KMIP > Registered Clients > Add Client`, carica
     `client.crt` e associa l'utente creato.
   - **Automatica** (come la guida): `Access Management > Registration Tokens
     > New Registration Token` usando la CA locale; poi
     `Admin Settings > Interfaces > KMIP > Edit`, spunta
     **Auto Registration**, incolla il token, `Update` e riavvia `nae-kmip`.
6. **CA del server** — scarica la CA locale/servizio di CTM e salvala come
   `certs/ctm-ca.pem`. In alternativa, per il primissimo test puoi usare
   `--insecure`.

### Percorso nei sottodomini: registrazione manuale, senza CSR

1. Seleziona su CTM il sottodominio da usare e crea/verifica l’utente KMIP nel gruppo **Key Users**.
2. Apri **KMIP > Client profile**, crea il profilo ed espandi **Certificate detail**.
3. Nel campo **Common Name (CN)** usa esattamente:

   ```text
   sottodominio|sottodominio||kmiputente
   ```

   Una barra tra i nomi dei sottodomini e **due barre prima dell’utente**.
   Esempio verificato: `kmip|kmip||kmip6`. La sintassi generale Thales è
   `<domain>|<auth-domain>||<username>`; qui i due domini coincidono.
4. Nello stesso sottodominio, apri **KMIP > Registered Clients > Add Client** e registra **manualmente** il client usando quel profilo.
5. Scarica direttamente da CTM **certificato client e chiave privata**. Per questo percorso non usare la generazione CSR dell’app né l’auto-registrazione.
6. Nell’app carica i due file e la **CA del server KMIP**. La CA del sottodominio che firma il client può essere diversa da quella del server: il file CA deve comprendere la catena necessaria, inclusa la Root CA.
7. Se sono richieste credenziali KMIP, nel campo **Utente KMIP** inserisci il CN completo del certificato emesso, mantenendo tutti i separatori, e la password dell’utente.

Esempio CLI per le credenziali, con apici perché `|` è un operatore della shell:

```bash
--username 'kmip|kmip||kmip6' --password 'la-password'
```

### Riferimenti di configurazione

- [Thales — sintassi degli utenti KMIP e domini](https://docs-cybersec.thalesgroup.com/bundle/latest-cdsp-cm/page/reference/kmip-ref/index.html)
- [Thales — protocolli TLS e ciphersuite delle interfacce](https://www.thalesdocs.com/ctp/cm/2.7/admin/cm_admin/interfaces/index.html)
- Guida locale `[CTM] [KMIP] Integrazione vSphere_v1.0.docx`, sezione «Configurazione dell’interfaccia KMIP», per l’abilitazione di `TLS_RSA_WITH_AES_256_CBC_SHA` nel percorso vSphere descritto.

## 2. Esecuzione del client

```bash
# costruisce l'immagine (solo la prima volta) e avvia il container
./run.sh --host 192.168.6.50 \
         --ca /certs/ctm-ca.pem \
         --cert /certs/client.crt \
         --key /certs/client.key \
         demo
```

Il container usa `--network=host`, quindi raggiunge CTM sia che la VM sia in
NAT (`192.168.122.x`) sia che sia bridged. La cartella `certs/` è montata in
`/certs` in sola lettura.

Se l'interfaccia KMIP è in modalità `tls-cert-and-pw` (come quando in vCenter
si imposta "Password protection"), aggiungi:

```bash
--username kmipclient --password 'la-password'
```

### Comandi disponibili

| Comando | Effetto |
|---|---|
| `demo` | crea+attiva+legge+cifra una chiave AES-256 (la lascia su CTM) |
| `demo --destroy` | come sopra, poi revoca e distrugge |
| `create --name N` | crea una chiave AES-256 |
| `activate --uid U` | attiva una chiave creata singolarmente |
| `locate [--name N]` | cerca oggetti per nome |
| `get --uid U` | legge materiale e metadati |
| `encrypt --uid U --data "testo"` | cifra con la chiave |
| `decrypt --uid U --data-hex HEX` | decifra |
| `revoke --uid U [--reason ...]` | revoca |
| `destroy --uid U` | distrugge (richiede chiave non attiva) |

Esempio di ciclo completo:

```bash
./run.sh ... create --name chiave-test        # stampa l'UID
./run.sh ... activate --uid <UID>
./run.sh ... locate --name chiave-test
./run.sh ... get --uid <UID>
./run.sh ... revoke --uid <UID>
./run.sh ... destroy --uid <UID>
```

## 3. Web UI (browser)

In alternativa alla CLI:

```bash
./run-webui.sh
```

Apri `http://127.0.0.1:8080`. La pagina contiene:

- **Connessione**: host/IP, porta, versione KMIP, menu per selezionare CA server,
  certificato e chiave privata dai file presenti in `certs/`, utente/password
  e opzione "non verificare il certificato".
- **Reset client**: pulsante in alto a destra; elimina certificati, chiavi e CSR
  nella cartella condivisa, inclusa la CA server.
- **Risultato**: pannello sempre visibile in basso, anche scorrendo la pagina.
- **Test connessione**: esegue solo il handshake TLS e conferma che il
  container raggiunge CTM.
- **Esegui demo completa**: ciclo create → activate → locate → get →
  encrypt/decrypt, con opzione "revoca e distrugge al termine".
- **Operazioni singole**: Create, Locate, Get, Encrypt, Decrypt, Revoke,
  Destroy, con riquadro del risultato.

La Web UI usa `--network=host`: condivide la rete dell'host, quindi raggiunge
la VM CTM in QEMU sia in NAT libvirt (`192.168.122.x`), sia bridged, sia con
un port forwarding su `127.0.0.1`. La cartella `certs/` è montata in `/certs`
in lettura e scrittura nella Web UI.

Puoi precompilare i campi via variabili d'ambiente:

```bash
KMIP_HOST=192.168.122.10 KMIP_USERNAME=kmipclient ./run-webui.sh
```

Per fermare la Web UI: `Ctrl+C`.

## 4. Verifica su CipherTrust Manager

1. `Keys`: cerca `vsphere-test-*` o il nome usato.
2. Nel caso root dell’esempio, l’**Owner** è `local|kmipclient`. Per i sottodomini verifica l’utente e il dominio effettivamente associati; non applicare automaticamente la formula dell’esempio root.
3. Lo stato deve essere **Active** dopo `activate`; dopo revoca/destroy cambia
   di conseguenza.
4. Per la diagnostica: `Admin Settings > Services`, log del servizio
   `nae-kmip`.

Questo è lo stesso riscontro che la guida chiede di fare dopo la cifratura di
una VM: la chiave creata dal client compare in CTM con owner uguale all'utente
KMIP.

## 5. Differenze rispetto alla prova con vSphere

| Aspetto | vSphere | Questo client |
|---|---|---|
| Certificato client | procedura di trust di vCenter | CSR nel percorso root oppure certificato e chiave scaricati da CTM nel percorso manuale dei sottodomini |
| Registrazione | secondo la guida vSphere applicabile | manuale per il percorso nei sottodomini descritto qui; auto o manuale nel percorso root |
| Chiavi | AES-256 create da vCenter | AES-256 create dal client |
| Cifratura dati | VM Encryption / vSAN | Encrypt/Decrypt KMIP |
| Trust reciproco | handshake vCenter↔CTM | solo lato client→CTM |
| Verifica in CTM | owner coerente con utente e dominio | owner coerente con utente e dominio |

In pratica verifichi lo stesso percorso KMIP che usa vCenter; cambia solo chi
genera il certificato e chi invoca le operazioni.

## 6. Troubleshooting

- **Connection refused** — VM CTM spenta, IP errato, porta 5696 chiusa.
- **certificate verify failed** — `--ca` non è la CA che ha firmato il
  certificato server; per un test rapido usa `--insecure`.
- **hostname mismatch** — usa l'IP/FQDN presente nel certificato server,
  oppure `--insecure`.
- **AUTHENTICATION_NOT_SUCCESSFUL / Certificate user must match username** — usa il CN completo del certificato nel campo Utente KMIP; nei sottodomini, per esempio `kmip|kmip||kmip6`, non soltanto `kmip6`.
- **PERMISSION_DENIED** — utente non in `Key Users`, client non registrato,
  oppure CN del certificato diverso dall'Username.
- **Object is active and cannot be destroyed** — revoca prima di distruggere;
  `demo --destroy` lo fa automaticamente.
- **License not installed yet** — prova KMIP scaduta: serve la licenza.
- **TLS handshake failure** — se hai abilitato solo la suite RSA richiesta da
  vSphere, riabilita anche le suite ECDHE: il client Python non usa RSA key
  exchange di default.

## 7. Test offline (senza CTM)

Per verificare che container, TLS e operazioni funzionino:

```bash
./selftest.sh
```

Avvia un server PyKMIP locale su `127.0.0.1:5697`, esegue il `demo` e pulisce
il container. I certificati di test restano in `selftest-certs/`.

## 8. Alternativa senza container

Se preferisci non usare Podman:

```bash
./setup.sh
.venv/bin/python kmip_test.py --host ... demo
```

## 9. Pulizia

```bash
podman rmi localhost/kmip-test:latest
rm -rf certs selftest-certs
```

I comandi `revoke`/`destroy` revocano la chiave e ne distruggono il materiale crittografico. CTM può conservarne nome, UID e metadati con stato **Destroyed**: la voce può restare visibile in `Keys`. La cancellazione completa dei metadati è distinta.
