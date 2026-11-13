# Verifica integrazione CTM / KMIP — 13 novembre 2026

Server: `192.168.122.221:5696`. Protocollo: KMIP 1.4.
Autenticazione della prova positiva: mTLS con certificato client e verifica CA server, senza username/password.

| Operazione | Esito |
|---|---|
| Connessione mTLS | OK |
| Create AES-256 | OK |
| Activate | OK |
| Locate per nome, con verifica UID | OK |
| Get: AES, 256 bit, 32 byte di materiale | OK |
| Encrypt AES ECB / PKCS5 | OK |
| Decrypt e confronto con il testo originale | OK |
| Revoke | OK |
| Destroy | OK |
| Locate dopo distruzione: UID assente | OK |

Chiave creata solo per la verifica: `vsphere-verifica-20261113-140747-2d9a69`.
UID: `0d82d4900a8241688c215f19bc450c16d2433ddce621498e802bcef19a5283af`.
La chiave della prova è stata revocata e distrutta. Le chiavi preesistenti non sono state modificate.

## Diagnostica verificata

Con un utente inesistente, una richiesta Locate di sola lettura restituisce:
`AUTHENTICATION_NOT_SUCCESSFUL: Certificate user must match username in Authentication request`.
Con KMIP 2.0, una richiesta Locate restituisce:
`INVALID_MESSAGE: Protocol major version mismatch`.

Queste risposte CTM omettono BatchCount nell’intestazione. PyKMIP 0.11.0 tenta di leggerlo prima di ResultReason/ResultMessage e genera `unpack requires a buffer of 4 bytes`, nascondendo il motivo reale. Il client ora recupera e mostra il motivo del rifiuto da queste risposte, senza registrare il contenuto dei pacchetti o le password.

## Modifiche

- Recupero del messaggio CTM dalle risposte di errore con intestazione incompleta.
- Log di errore con operazione, server, versione KMIP e utente, senza password o materiale delle chiavi.
- Operazione Attiva chiave disponibile anche singolarmente nella GUI e come comando `activate --uid ...` nella CLI.

Il ciclo positivo non verifica l’autenticazione con username/password né le funzioni specifiche di vSphere.

## Verifica della demo completa

Anche la funzione `demo` condivisa da GUI e CLI è stata eseguita contro CTM con KMIP 1.4 e autenticazione mTLS. Esito finale: `Integrazione KMIP OK`; confronto cifratura/decifratura riuscito, chiave revocata e distrutta, Locate finale vuoto.

Nome: `vsphere-demo-verificata-1794578933`.
UID: `f3591408ac904f1698313655d271e73d4e0d012f6f27438db4887739403175c9`.
