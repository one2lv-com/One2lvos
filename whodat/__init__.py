"""Who Dat: machine identity handshake and per-owner key vault for One2lvOS.

"Who Dat?"     the registry hands a system a fresh, single-use challenge.
"Whose Data?"  the system answers with its data and provenance, signed with the
               private key that only it holds. The registry checks the signature
               against the public key that the owner enrolled, logs the answer,
               and only then lets that system read that owner's keys.

Knowing the protocol, or copying a machine's hostname/metadata, is not enough:
without the enrolled private key the signature fails and nothing is released.

See WHODAT.md for the protocol, the trust anchor and what it does not protect.
"""

from .core import (  # noqa: F401
    PROTOCOL,
    Registry,
    WhoDatError,
    AuthError,
    VaultLocked,
    generate_private_key,
    public_key_b64,
    system_id_for,
    owner_id_for,
)

__version__ = "1.0.0"
