# Versioning e pubblicazione

Si usa il formato `MAJOR.MINOR.PATCH` (Semantic Versioning):

- `PATCH`: correzioni compatibili, per esempio `1.0.1`.
- `MINOR`: funzionalità nuove compatibili, per esempio `1.1.0`.
- `MAJOR`: modifiche incompatibili, per esempio `2.0.0`.

Per una release:

1. Aggiorna `__version__` in `app_version.py`.
2. Aggiorna `CHANGELOG.md` e `RELEASE-NOTES.md`.
3. Esegui i test e registra le modifiche su `main`.
4. Crea e invia un tag che corrisponda alla versione, per esempio `v1.0.0`.
5. GitHub Actions verifica la corrispondenza tra tag e versione, costruisce su Windows, Linux e macOS, esegue i test e il controllo dell’eseguibile, poi pubblica i tre archivi e `SHA256SUMS.txt` nella release.

Non pubblicare certificati, chiavi private, password, token o configurazioni del laboratorio. I pacchetti vengono controllati automaticamente per escludere identità e impostazioni locali.

Una build fallita impedisce la pubblicazione della release. Le esecuzioni manuali del workflow consentono di verificare i pacchetti prima di creare il tag.
