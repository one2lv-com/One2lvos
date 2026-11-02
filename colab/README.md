# One2lvOS on Google Colab

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/one2lv-com/One2lvos/blob/main/One2lvOS_Colab.ipynb)

`One2lvOS_Colab.ipynb` (repo root) uses the files in this folder:

| File | What it does |
|---|---|
| `ubuntu26-root.sh` | Downloads the official Ubuntu 26 base image (checksum-verified), points apt at the Ubuntu 26 mirrors (`resolute` for 26.04, `stonking` for 26.10), runs `apt update` and `apt full-upgrade`, installs sudo and base tools, creates the `one2lv` user with sudo and sets the root password for `su -`. |
| `enter-ubuntu26.sh` | The login shell ttyd starts for each browser terminal (chroot, or proot if chroot isn't allowed). |
| `gateway.py` | The one public port: password login, `/terminal/` to ttyd, everything else to the Lumenis reactor. Injects `o2-colab.js` into `/desktop`. |
| `o2-colab.js` | Adds the Ubuntu 26 Terminal and Lumenis Console apps to `one2lvos-desktop.html`, next to its built-in Lumenis Chat. |

Why a chroot and not an in-place upgrade: Colab's image is an older Ubuntu, and dist-upgrading it replaces the libraries the notebook kernel runs on. Ubuntu 26 runs as a full root filesystem instead; apt, sudo and su in it are real. The kernel is Colab's.

Secrets come from Colab's Secrets panel (`O2_DESKTOP_PASSWORD`, `NVIDIA_API_KEY`) or a prompt. Nothing is stored in the notebook, and its outputs are private.

The reactor honours `LUMENIS_EXEC_CHROOT`: when set, its `/api/terminal` and `/ws/terminal` commands run inside that root.
