"""The list-choice prompt used by every model-specific menu.

    Which model list?  1. Verified 200 OK (38)  2. All discovered (243)

Default is the verified 200 OK list. When nothing is verified yet the
default becomes the full list, and the prompt says why.
"""

VERIFIED = "verified"
ALL = "all"


def prompt_text(n_verified, n_all):
    return f"1. Verified 200 OK ({n_verified})  2. All discovered ({n_all})"


def choose_list(verified, discovered, input_fn=None, out=None, title="Which model list?"):
    """Ask once which list to use. Returns (models, scope) where scope is
    'verified' or 'all'. Enter takes the default."""
    input_fn = input_fn or input
    out = out or print
    verified, discovered = list(verified), list(discovered)
    default = "1" if verified else "2"
    out(f"\n{title}  {prompt_text(len(verified), len(discovered))}")
    if not verified:
        out("  (no model has passed the 200 test yet, so the default is the full list)")
    try:
        ans = (input_fn(f"List [{default}]: ") or "").strip().lower()
    except EOFError:
        ans = ""
    if ans in ("2", "a", "all", "d", "discovered", "full"):
        choice = "2"
    elif ans in ("1", "v", "verified", "200"):
        choice = "1"
    else:
        choice = default
    return (verified, VERIFIED) if choice == "1" else (discovered, ALL)


def unverified_note(model, verified):
    """The short note shown before testing a model that is not verified,
    or '' when it is."""
    if model in set(verified):
        return ""
    return (f"Note: {model} hasn't passed the 200 OK test. It may not answer; "
            "run the sweep (option 2) to verify it.")
