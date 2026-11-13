# User guide

[English overview](../../README.en.md) · [Italian documentation](../../README.md)

## 1. Import your certificates

In **1. Certificati e chiave del client**, select an existing file or use the upload control in each card:

| Italian label | Meaning |
|---|---|
| CA del server | CA chain used to verify the CTM KMIP server certificate |
| Certificato del client | Certificate that identifies this KMIP client |
| Chiave privata del client | Private key matching the client certificate |
| Carica… | Upload the selected file |
| File da usare | Select the imported file to use |

Use PEM files. The private key must be unencrypted. Importing a client certificate does not register the client in CTM; complete the CTM registration procedure separately.

The CA used to sign the client certificate can differ from the CA that signs the server certificate. For a CTM subdomain, importing only the subdomain CA may not provide the Root CA required to verify the KMIP server.

For the manual subdomain workflow, download the certificate and private key from CTM. Do not generate a CSR in the app. Follow the [subdomain instructions](../../README.en.md#ctm-subdomains).

## 2. Connect to CTM

Under **2. Connessione a CipherTrust Manager**:

1. Enter the CTM server address and KMIP port, normally `5696`.
2. Select KMIP `1.4` for the tested configuration.
3. If the server requires username/password authentication, enter the full certificate CN as the username. For subdomains: `subdomain|subdomain||kmipuser`.
4. Enter the password once. It remains in server memory for the same endpoint and username until the app closes or you use **Dimentica password** (Forget password).
5. Keep server-certificate verification enabled and click **Verifica connessione TLS** (Verify TLS connection).

This button checks TLS connectivity only. It does not create a key or prove that CTM accepts the KMIP user for key operations.

## 3. Run the full test

Click **Avvia test completo** in section 3. The test creates and activates an AES-256 key, locates and retrieves it, encrypts data and verifies that decryption returns the original plaintext.

Select **Revoca e distruggi la chiave alla fine del test** if the temporary key should be revoked and destroyed when the test completes. Otherwise, the key remains available in CTM for inspection. A failed test may leave a created key on CTM; check its name and UID before repeating.

## 4. Run individual operations

| Button | KMIP operation |
|---|---|
| Crea chiave | Create |
| Attiva chiave | Activate |
| Cerca chiavi | Locate |
| Leggi chiave | Get |
| Cifra dati | Encrypt |
| Decifra dati | Decrypt |
| Revoca chiave | Revoke |
| Distruggi chiave | Destroy |

Use the key UID to address an existing key. A key created using the individual **Crea chiave** button must be activated before encryption. After encryption, **Copia ciphertext** copies only the hexadecimal ciphertext into the clipboard; paste it into **Dati esadecimali da decifrare** to decrypt it.

The result panel remains visible at the bottom of the window.

## 5. Reset and stored data

**Reset client**, in the top-right corner, deletes local certificates, private keys and CSRs from the app's certificate folder. It does not delete keys stored in CTM.

| Platform | App data directory |
|---|---|
| Windows | `%LOCALAPPDATA%\KMIP Test Client` |
| Linux | `$XDG_DATA_HOME/kmip-test-client`, normally `~/.local/share/kmip-test-client` |
| macOS | `~/Library/Application Support/KMIP Test Client` |

`settings.json` stores connection settings and selected file paths. Passwords are not written to this file. `client.log` contains error diagnostics.

## Troubleshooting

- **No route to host / timeout:** check whether CTM is running, the address is correct and port 5696 is reachable.
- **Self-signed certificate in certificate chain:** import the correct server Root CA and any required intermediates. The subdomain's client CA alone may not be sufficient.
- **Certificate user must match username:** use the complete certificate CN, including all separators, and verify the registered client's user association in CTM.
- **Connection closes without a KMIP response:** inspect CTM's `nae-kmip` logs and verify the registered certificate, its domain, trusted CAs and associated user. TLS success alone does not establish successful KMIP authentication.
- **Destroyed key still appears in CTM:** this can be expected; Destroy removes key material while CTM may retain metadata.
