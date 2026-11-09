# RSA Key Management

The authentication flow uses a persistent RSA private key so that every
backend worker can decrypt passwords encrypted by the frontend.

## Local Development

Generate a development key from the backend project root:

```powershell
New-Item -ItemType Directory -Force secrets
openssl genpkey `
  -algorithm RSA `
  -pkeyopt rsa_keygen_bits:3072 `
  -out secrets/auth_rsa_private_key.pem
```

The default configuration points to:

```text
secrets/auth_rsa_private_key.pem
```

The `secrets/` directory and PEM files are ignored by Git and Docker. Do not
commit or copy the private key into the application image.

## Production

Mount the key as a read-only Docker secret or volume:

```yaml
services:
  backend:
    secrets:
      - auth_rsa_private_key

secrets:
  auth_rsa_private_key:
    file: ./secrets/auth_rsa_private_key.pem
```

The Docker image expects the secret at:

```text
/run/secrets/auth_rsa_private_key.pem
```

Override `RSA_PRIVATE_KEY_PATH` if the secret is mounted elsewhere.

If the PEM file is password-protected, set `RSA_PRIVATE_KEY_PASSWORD`.
Otherwise leave it unset.

## Key Rotation

Because the public key endpoint returns the active public key, the simplest
rotation strategy is:

1. Deploy the new private key to every backend instance.
2. Restart all workers together.
3. Clear any frontend public-key cache.

For zero-downtime rotation with mixed key versions, add a `key_id` to the
public-key response, store multiple private keys, and select the matching key
when decrypting.

## Verification

Run the RSA tests:

```powershell
python -m pytest tests/test_rsa_persistence.py
```
