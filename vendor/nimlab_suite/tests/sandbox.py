"""A throwaway lab for tests that touch config, HOME and private files.

Inside `lab()` everything the v3.7 features write goes to a temp folder:
HOME, XDG_CONFIG_HOME (so ~/.config/nimlab), the data folder, a copy of
config_cluster.json / config_system_prompts.json, and ~/.nimlab_env. Secret
environment variables are cleared so a developer's real key never leaks
into a test (or a test's assertion output). Nothing outside the temp folder
is written, and no real service, network or cloudflared is used.
"""

import contextlib
import os
import shutil
import tempfile
import types
from unittest import mock

from nimlab import config, store

SECRET_ENV = ("NVIDIA_API_KEY", "NGC_API_KEY", "MCP_API_KEY", "TUNNEL_TOKEN", "NIMLAB_ORACLE_PASSWORD",
              "TELEGRAM_BOT_TOKEN", "NIMLAB_ADMIN_KEY_FILE", "NIMLAB_TELEGRAM_TOKEN_FILE",
              "NIMLAB_CLOUDFLARED_TOKEN_FILE", "NIMLAB_CLOUDFLARED", "TERMUX_VERSION", "PREFIX",
              "NIMLAB_ORACLE_USER", "NIMLAB_ORACLE_DSN", "NIMLAB_MCP_KEY_FILE", "NIMLAB_SECRETS")


@contextlib.contextmanager
def lab(termux=False):
    root = tempfile.mkdtemp(prefix="nimlab-test-")
    home = os.path.join(root, "home")
    data = os.path.join(root, "data")
    proj = os.path.join(root, "proj")
    for d in (home, data, proj):
        os.makedirs(d)
    cluster = os.path.join(proj, "config_cluster.json")
    prompts = os.path.join(proj, "config_system_prompts.json")
    for src, dst in ((config.CLUSTER_CONFIG, cluster), (config.SYSTEM_PROMPTS, prompts)):
        if os.path.exists(src):
            shutil.copy(src, dst)
    env = {k: v for k, v in os.environ.items() if k not in SECRET_ENV}
    env.update(HOME=home, XDG_CONFIG_HOME=os.path.join(home, ".config"), NIMLAB_DATA_DIR=data,
               NIMLAB_COLOR="0", NIMLAB_CONFIG_READONLY="1")
    if termux:
        prefix = os.path.join(root, "data", "data", "com.termux", "files", "usr")
        os.makedirs(os.path.join(prefix, "bin"))
        env.update(PREFIX=prefix, TERMUX_VERSION="0.118.0")
    ns = types.SimpleNamespace(root=root, home=home, data=data, proj=proj, cluster=cluster, prompts=prompts,
                               env=env, env_file=os.path.join(home, ".nimlab_env"))
    from nimlab import cli
    patches = [mock.patch.dict(os.environ, env, clear=True),
               mock.patch.object(config, "CLUSTER_CONFIG", cluster),
               mock.patch.object(config, "SYSTEM_PROMPTS", prompts),
               mock.patch.object(cli, "ENV_FILE", ns.env_file),
               mock.patch.object(cli, "BASHRC", os.path.join(home, ".bashrc"))]
    for p in patches:
        p.start()
    store.reset()
    try:
        yield ns
    finally:
        for p in reversed(patches):
            p.stop()
        store.reset()
        shutil.rmtree(root, ignore_errors=True)


def all_text(root):
    """Every readable file under root, joined: to look for leaked secrets."""
    out = []
    for d, _dirs, files in os.walk(root):
        for f in files:
            try:
                with open(os.path.join(d, f), encoding="utf-8", errors="replace") as fh:
                    out.append(fh.read())
            except OSError:
                pass
    return "\n".join(out)


class FakeIO:
    """Scripted answers for the setup wizard. `answers` is a list consumed in
    order by ask/secret/choose/yes; a callable answer gets the prompt."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.out = []
        self.prompts = []

    def _next(self, prompt):
        self.prompts.append(prompt)
        if not self.answers:
            raise KeyboardInterrupt  # ran out of script: like Ctrl-D
        a = self.answers.pop(0)
        return a(prompt) if callable(a) else a

    def say(self, text=""):
        self.out.append(str(text))

    def ask(self, prompt, default=""):
        v = self._next(prompt)
        return str(default or "") if v is None else v

    def secret(self, prompt):
        return self._next(prompt)

    def choose(self, prompt, options, default=None):
        v = self._next(prompt)
        keys = [k for k, _ in options]
        if v is None:
            return default
        assert v in keys, f"{v!r} is not one of {keys} for {prompt!r}"
        return v

    def yes(self, prompt, default=True):
        v = self._next(prompt)
        return default if v is None else bool(v)

    @property
    def text(self):
        return "\n".join(self.out)
