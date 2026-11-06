# Who Dat: machine identity and key vault for One2lvOS

**Who Dat?** The registry gives a system a fresh challenge: a random 32-byte nonce that is good once, for 60 seconds.
**Whose Data?** The system answers with what it says about itself (hostname, platform, git commit, a hash of its machine-id, who enrolled it). It signs that answer with its own private key. The registry checks the signature against the public key that the system's owner enrolled. It logs the answer and gives back a session token that lasts five minutes. Only with that token can the system read its owner's keys.

Knowing the protocol doesn't get a system in. Copying a machine's hostname or metadata doesn't either. Without the enrolled private key the signature fails and nothing is released. Lumenis saying a request is fine doesn't authorize it, and the 🧲 header doesn't either: both are accepted as markers and ignored for access.

## Two kinds of keys

| | What | Where it comes from |
|---|---|---|
| Identity keys | owner key, system key (Ed25519), vault root key (32 random bytes) | Generated on each installation by `whodat init`. Never shipped, never shared. |
| Service credentials | NVIDIA, GitHub, Supabase, Astra, Discord, sfcompute ... | Each owner gets their own from those services and stores them with `whodat secret put` / `secret import`. Nobody else's are ever included. |

## Anyone can start their own copy

```bash
pip install -r requirements.txt
python3 -m whodat init --email you@example.com      # the key generator: owner key, system key, root key, your own registry
python3 -m whodat secret put NVIDIA_API_KEY         # prompts, hidden; or: secret import my.env
./startos.sh                                        # handshake, then your keys go to the services
```

Or just run `./startos.sh`. On first boot it asks for your email at the terminal, or reads `ONE2LVOS_OWNER_EMAIL`, and generates the keys itself.

The email is a label for your keys. It isn't verified, and it isn't a password. It grants nothing by itself.

On each boot, `startos.sh` loads `.env` and then sources `whodat_boot.sh`. That script does the handshake and exports your vault keys, but only for variables that `.env` didn't already set. If anything fails (no identity, a revoked system, a missing root key, the registry unreachable), it exports nothing, prints a warning and the boot carries on with `.env` as before. `WHODAT_BOOT=0` turns the step off.

## Files (default locations)

```
~/.config/one2lvos/whodat/identity/system.key     this machine's private key (0600)
~/.config/one2lvos/whodat/identity/owner.key      owner key: enroll, revoke, write keys (0600)
~/.config/one2lvos/whodat/identity/identity.json  ids, fingerprints, registry
~/.config/one2lvos/whodat/registry.db             registry + encrypted vault (0600)
~/.config/one2lvos/whodat-root.key                vault root key: kept OUTSIDE the registry folder
```

`WHODAT_KEY_PASSPHRASE` encrypts the two private keys at rest. `WHODAT_ROOT_KEY` (base64) supplies the root key from a secret manager instead of the file.

## Commands

```
status | handshake | boot-env [--only-unset]
secret put NAME | secret import FILE [--only A,B] | secret list | secret delete NAME
keygen --out FILE                                  new system key for another machine
enroll --public-key K --label L [--scope A,B]      owner enrolls that machine (scope limits which keys it gets)
enroll --self                                      after an operator added you to a shared registry
revoke SYSTEM_ID | systems | audit [--limit N]
owner add|disable|enable|list                      registry host operator, local only
serve [--host 127.0.0.1 --port 8097]               standalone registry
dist-check PATH --env FILE                         fails if a dir/.tar.gz/.zip holds keys or credential values from FILE
```

The reactor also serves the same registry at `/whodat` (`/challenge`, `/respond`, `/secrets`, `/admin`, `/owners`). Request bodies can be JSON or `∆|key=value|key=value`.

## Security properties (all covered by tests/test_whodat.py)

- **Proof of possession:** responses are Ed25519 signatures over the registry id, challenge id, nonce, expiry, system id and a hash of Whose Data. A system's id comes from its public key, so one key can't claim another's id.
- **Replay:** a challenge is burned atomically before its signature is checked, so a used or failed nonce is dead. Signed admin requests carry a nonce and a timestamp within 120 seconds, and every nonce is recorded.
- **Domain separation:** boot, admin and registration signatures use different prefixes, so a signature made for one can't be replayed as another.
- **Enrollment and revocation:** only the owner key can enroll, revoke or write keys. A system key can't. Revoking a system also ends its live sessions immediately, and a revoked key can't be enrolled again.
- **Isolation:** each owner's keys are encrypted with AES-256-GCM, using a key derived from the root key with HKDF for that owner. The owner id, the key name and the version are bound in as associated data, so a ciphertext copied to another owner doesn't decrypt. Scopes limit which keys a system receives.
- **Fail closed:** with no root key or the wrong one, the vault stays locked. Identity can still be checked, but no key is released. Errors from outside always read `not authorized`.
- **Audit:** every action is logged, allowed or refused, with the real reason. The log is a SHA-256 hash chain and holds key names only, never values or tokens. Session tokens are stored only as hashes.
- **Network:** plain http is refused unless the registry is on loopback. Requests are rate-limited per IP, responses are marked no-store, and self-registration over the network is off unless `WHODAT_OPEN_REGISTRATION=1` (and even then it requires proof of the key).

## What it does not do: the trust anchor

- **The root key is the anchor.** Back it up somewhere other than this machine. If you lose it, the vault can't be opened, and nobody can recover it for you. If someone steals it along with `registry.db`, they can read every key in the vault.
- **A machine that holds its system key is trusted.** If that machine is compromised, revoke it. Generate a new key for a rebuilt machine with `keygen` and enroll it.
- **The registry has to be reachable at boot.** On a single machine it's a local file, so boot doesn't depend on the reactor, Lumenis, Cloudflare or the network. On a shared registry, if the host is down the handshake fails and the boot falls back to `.env`. Nothing here keeps a server online forever.
- **On a shared registry, the operator holds the root key** and can therefore read every member's vault. For full isolation, run your own registry with plain `init`.
- **Restore after a wipe is manual.** Put back the root key from its backup, restore `registry.db` and the identity folder, or start fresh with `init` and re-add your keys.
