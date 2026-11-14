"""The card before a change of the tenant (VERBUNDEN VB-6, VB-14; review 14.11.): a CONFIRM FIRST line names a code, a
hash over what the card shows and what it rests on (the lines of a drift, say). ppp import --confirmed <code> goes on
only with the code of the card that the state now gives; a state that changed since the card (another drift, another
version, another value) gives another code, and the command shows the new card instead. So an answer is bound to what
the user saw, and no change of the tenant happens without one run that showed its card."""
from __future__ import annotations

import hashlib

ASK = "the same command with --confirmed"


def code(text: str, bound: tuple | list = ()) -> str:
    """Eight hex digits over the card and what it rests on."""
    data = "\n".join([text, *map(str, bound)]).encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:8]


def confirm(text: str, confirmed: bool | str | None, bound: tuple | list = ()) -> bool:
    """True when the change may go on: confirmed is True (a call from Python, the tests), or the code of this card. Else
    the card is printed with its code (the line names it after --confirmed) and False comes back. A code given that is
    not this card's says so first: the state changed since the card was shown."""
    mine = code(text, bound)
    if confirmed is True or (isinstance(confirmed, str) and confirmed.strip().lower() == mine):
        return True
    if isinstance(confirmed, str) and confirmed.strip():
        print(f"CHANGED: the card with code {confirmed.strip()} no longer fits the state now; show this card instead.")
    elif confirmed == "":
        print("--confirmed needs the code of the card: show this card, then the command it names.")
    print(text.replace(ASK, f"{ASK} {mine}"))
    return False
