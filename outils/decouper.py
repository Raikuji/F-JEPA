"""Découpe ou réassemble les fichiers trop gros pour GitHub (limite 100 Mo par fichier).

    python outils/decouper.py decouper chemin/fichier.pkl   -> fichier.pkl.part01, .part02, ...
    python outils/decouper.py reassembler chemin/fichier.pkl -> recolle les .partNN en fichier.pkl
    python outils/decouper.py reassembler                    -> recolle tous les .part01 du projet
"""
import hashlib
import sys
from pathlib import Path

TAILLE_MORCEAU = 45 * 1024 * 1024  # sous l'avertissement GitHub de 50 Mo
RACINE = Path(__file__).resolve().parent.parent


def empreinte(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def decouper(fichier):
    fichier = Path(fichier)
    with open(fichier, "rb") as f:
        i = 0
        while bloc := f.read(TAILLE_MORCEAU):
            i += 1
            Path(f"{fichier}.part{i:02d}").write_bytes(bloc)
    Path(f"{fichier}.sha256").write_text(empreinte(fichier) + "\n")
    print(f"{fichier} -> {i} morceaux")


def reassembler(fichier):
    fichier = Path(fichier)
    morceaux = sorted(fichier.parent.glob(fichier.name + ".part[0-9][0-9]"))
    if not morceaux:
        sys.exit(f"aucun morceau trouvé pour {fichier}")
    with open(fichier, "wb") as sortie:
        for m in morceaux:
            sortie.write(m.read_bytes())
    attendu = Path(f"{fichier}.sha256")
    if attendu.exists() and attendu.read_text().strip() != empreinte(fichier):
        sys.exit(f"{fichier} : empreinte SHA-256 différente, fichier corrompu")
    print(f"{fichier} reconstitué ({len(morceaux)} morceaux)")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("decouper", "reassembler"):
        sys.exit(__doc__)
    if len(sys.argv) > 2:
        for f in sys.argv[2:]:
            (decouper if sys.argv[1] == "decouper" else reassembler)(f)
    elif sys.argv[1] == "reassembler":
        for p in RACINE.rglob("*.part01"):
            if ".git" not in p.parts:
                reassembler(p.with_name(p.name[: -len(".part01")]))
    else:
        sys.exit(__doc__)
