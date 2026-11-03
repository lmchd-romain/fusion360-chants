"""Point d'entrée de l'add-in Edge Banding (Chants plaqués). run/stop protégés ; panne de démarrage → demarrage.log."""
import sys
import traceback
from pathlib import Path

_ICI = Path(__file__).resolve().parent
_JOURNAL = _ICI / "demarrage.log"


def _noter(texte: str) -> None:
    try:
        with open(_JOURNAL, "a", encoding="utf-8") as f:
            f.write(texte + "\n")
    except OSError:
        pass


if str(_ICI) not in sys.path:
    sys.path.insert(0, str(_ICI))
for _nom in [n for n in sys.modules if n == "edgebanding" or n.startswith("edgebanding.")]:
    del sys.modules[_nom]  # Arrêter / Exécuter ne recharge pas les sous-modules

try:
    from edgebanding import interface
except Exception:  # noqa: BLE001
    _noter("Import impossible :\n" + traceback.format_exc())
    raise


def run(context):
    try:
        interface.demarrer()
    except Exception:  # noqa: BLE001
        _noter("run() en échec :\n" + traceback.format_exc())


def stop(context):
    try:
        interface.arreter()
    except Exception:  # noqa: BLE001
        _noter("stop() en échec :\n" + traceback.format_exc())
