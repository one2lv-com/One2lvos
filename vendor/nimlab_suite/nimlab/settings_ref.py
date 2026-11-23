"""Every setting Nim Lab reads, with its default (v3.7.1). The README's
"Settings reference" lists each one; tests/test_v371_settings_docs.py checks
that nothing is missing there."""

from . import bugs, config, ltm, server, service, telegram


def leaves(d, p=""):
    for k, v in d.items():
        path = f"{p}.{k}" if p else k
        if isinstance(v, dict) and v and k not in ("host_delays_sec", "candidate_overrides"):
            yield from leaves(v, path)
        else:
            yield path, v


def all_settings():
    c = {k: v for k, v in config.DEFAULT_CLUSTER.items() if k != "roles"}
    out = list(leaves(c))
    out += list(leaves(ltm.DEFAULTS, "memory_settings.long_term"))
    out += list(leaves(telegram.settings({}), "telegram_settings"))
    out += list(leaves(service.settings({}), "service_settings"))
    from . import heartbeat, scheduler            # 3.8.0
    out += list(leaves(dict(scheduler.DEFAULTS), "scheduler_settings"))
    out += list(leaves(dict(heartbeat.DEFAULTS), "heartbeat_settings"))
    ss = {k: v for k, v in server.default_settings().items() if k not in ("schema", "api_key", "key_created_at")}
    out += [("server." + p, v) for p, v in leaves(ss)]
    out += list(leaves(bugs.DEFAULTS, "server.bugs"))
    seen, uniq = set(), []
    for p, v in out:
        if p not in seen:
            seen.add(p)
            uniq.append((p, v))
    return uniq
