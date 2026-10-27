# Flotte non étiquetée SYNTHÉTIQUE (M5 à M16) : lire avant utilisation

**Ces données sont inventées**, comme celles de M1 à M4 (voir `../LISEZMOI_SYNTHETIQUE.md`). Elles servent à tester si le pré-entraînement JEPA devient utile quand on dispose de beaucoup d'historique de capteurs **sans étiquettes** et de peu de pannes qualifiées. Elles ne démontrent rien sur les machines réelles.

Générées le 15/10/2026 par `prototype/generation_capteurs_4ans.ipynb`, section 8 (graines 2026 + 1000 + 10 × j, environ 11 minutes). M1 à M4 sont inchangées : régénérées avec la flotte, elles sont identiques bit à bit aux fichiers du dossier parent.

## Ce que c'est

12 machines de plus, 3 de chacun des 4 types (M5–M7 comme M1 Mouleuse, M8–M10 comme M2 Démouleuse, M11–M13 comme M3 Trancheuse, M14–M16 comme M4 Conditionneuse) :
- **même physique et mêmes types de dégradations** que M1 à M4 (refroidissement, roulement, courroie, pneumatique, électrique), qui changent la dynamique et pas le niveau ;
- paramètres décalés au hasard de ±10 % (courant nominal et sa pente, constantes thermiques moteur et palier, vibration de base, résonance) et de ±3 % (pression), voir `config_flotte.json` ;
- même atelier (mêmes canicules que M1 à M4), mais planning, dégradations, recalibrages, capteurs figés et pertes de données propres à chaque machine ;
- 4 ans comme M1 à M4 (01/09/2022 → 31/08/2026), même format de fichiers.

487 dégradations au total, dont 245 avant le 01/09/2024 (200 pannes ou ralentissements), contre 62 pannes ou ralentissements étiquetés sur M1 à M4 sur la même période.

## Fichiers

| Fichier | Contenu |
|---|---|
| `capteurs_<M5..M16>_<aaaa-aaaa>.csv.gz` | Même format que M1 à M4. **Seuls les capteurs des deux années d'entraînement (sept. 2022 → août 2024) servent, au pré-entraînement uniquement.** |
| `verite_terrain_flotte.csv` | Dégradations de la flotte. **Jamais donnée aux modèles** : la flotte simule des machines dont la GMAO ne qualifie pas les pannes. Lue seulement pour décrire les données. |
| `verite_terrain_benins_flotte.csv` | Recalibrages, capteurs figés, pertes de données de la flotte (les canicules sont dans `../verite_terrain_benins.csv`). Description uniquement. |
| `config_flotte.json` | Paramètres de chaque machine de la flotte |

## Protocole testé (`prototype/F-JEPA_flotte.ipynb`)

Même question que dans `F-JEPA_capteurs_4ans.ipynb` : toutes les 2 h, pour M1 à M4, « panne ou ralentissement dans les 7 jours ? » à partir des 24 dernières heures ; validation sept. 2024 → août 2025, test sept. 2025 → août 2026.

- Pré-entraînement JEPA et autoencodeur masqué sur **4 machines** (poids repris du notebook précédent) ou sur **16 machines** (M1 à M16), même architecture, même nombre de pas (4 000 lots de 128), mêmes graines (0, 1, 2). À calcul égal, M1 à M4 ne font donc plus qu'un quart des lots à 16 machines : on teste « plus de machines différentes », pas « plus de calcul ».
- **Budgets d'étiquettes** : les têtes supervisées n'apprennent que sur les 2, 6, 12 ou 24 derniers mois d'entraînement de M1 à M4, soit 7, 18, 34 ou 62 pannes ou ralentissements étiquetés.
  Au budget de 2 mois (juillet-août 2024), seuls 6 événements donnent des fenêtres positives (roulement, courroie, un électrique) : **aucun refroidissement ni pneumatique étiqueté**, alors que ces deux types font près de la moitié des positifs du test. À 2 mois, ces types sont donc prédits sans en avoir vu un seul exemple. À 6 mois, les 5 types sont présents.
- Têtes : sonde logistique sur l'encodeur gelé (tous budgets) et fine-tuning complet (2, 6 et 24 mois). Contrôles : même encodeur à poids aléatoires ; boosting sur caractéristiques expertes avec les mêmes budgets.

## Hypothèses écrites AVANT d'exécuter les modèles (pré-enregistrement)

- **H6.** Pré-entraîner sur 16 machines au lieu de 4 améliore la sonde JEPA (ROC-AUC test), pour chaque graine, au budget de 24 mois.
- **H7.** Avec peu d'étiquettes (2 et 6 mois), JEPA-16 fine-tuné bat l'encodeur aléatoire fine-tuné pour chaque graine, et l'écart moyen sur 2 et 6 mois est plus grand qu'à 24 mois.
- **H8.** Avec peu d'étiquettes (2 et 6 mois), JEPA-16 fine-tuné bat le boosting expert à chacun des deux budgets : la moyenne des ROC-AUC des 3 graines (un modèle contre un modèle) dépasse celle du boosting. L'ensemble des 3 graines est rapporté en complément.
  *Modifiée à la relecture du protocole, avant toute exécution : la première version comparait l'ensemble des 3 graines au boosting, qui n'est qu'un seul modèle. Dans le notebook précédent, l'ensemble ajoutait déjà 0,02 à 0,04 d'AUC à chaque réseau, assez pour changer le verdict à lui seul.*
- **H9.** JEPA-16 contre autoencodeur-16 : pas d'hypothèse de sens ; on rapporte l'écart par graine.

Tout écart entre ces hypothèses et les résultats sera rapporté sans réécrire l'hypothèse.

## Limites

1. Les 12 machines de la flotte sortent du même simulateur que M1 à M4 : leur dynamique est plus proche de celle de M1 à M4 que ne le serait celle de vraies machines « de la même famille ». C'est un cas favorable au pré-entraînement.
2. La validation (un an étiqueté) sert à choisir les hyperparamètres et l'époque de fine-tuning pour toutes les méthodes, même aux petits budgets : c'est optimiste en valeur absolue, mais identique pour toutes les méthodes.

## Résultats (ajouté après exécution, 15/10/2026)

Voir `prototype/F-JEPA_flotte.ipynb`, section 10 : **H6, H7 et H8 ne sont pas confirmées** ; H9 est rapportée graine par graine. Les hypothèses ci-dessus n'ont pas été modifiées après exécution.

## Expérience 2 : la flotte étiquetée (16/10/2026, `prototype/F-JEPA_flotte_etiquetee.ipynb`)

À la demande d'Antoine (« plus de pannes étiquetées »), la vérité terrain de la flotte (`verite_terrain_flotte.csv`) sert maintenant **d'étiquettes**, en plus de celle de M1 à M4. Le nom du dossier est gardé pour ne rien casser. Rien n'est régénéré et aucun encodeur n'est ré-entraîné : le pré-entraînement n'utilise pas d'étiquettes, donc les encodeurs JEPA et autoencodeur restent ceux de l'expérience 1. Seules les têtes supervisées (sondes, fine-tuning, boosting) et l'évaluation changent.

| Pannes ou ralentissements | entraînement (sept. 2022 → août 2024) | validation | test (sept. 2025 → août 2026) |
|---|---|---|---|
| M1 à M4 | 62 | 35 | 36 |
| M5 à M16 | 200 | 103 | 106 |

- **Étiquettes de 4 machines** : entraînement et validation sur M1 à M4 (les fine-tunings à 24 mois de l'expérience 1 sont repris).
- **Étiquettes de 16 machines** : entraînement et validation sur M1 à M16, même procédure, même nombre de pas de fine-tuning.
- Deux tests : **M1–M4** (le même qu'avant) et **M1–M16** (4 fois plus grand).

### Hypothèses écrites AVANT d'exécuter les modèles (pré-enregistrement)

- **H10.** Avec les étiquettes des 16 machines au lieu de 4, le boosting expert et JEPA-16 fine-tuné (pour chaque graine) font mieux sur le test M1–M4.
- **H11.** Avec les étiquettes des 16 machines, JEPA-16 fine-tuné bat l'encodeur aléatoire fine-tuné pour chaque graine, sur le test M1–M16.
- **H12.** Avec les étiquettes des 16 machines, JEPA-16 fine-tuné bat le boosting expert sur le test M1–M16 : la moyenne des ROC-AUC des 3 graines dépasse celle du boosting. L'ensemble des 3 graines est rapporté en complément.
- **H13.** JEPA-16 contre autoencodeur-16 fine-tunés, étiquettes des 16 machines, test M1–M16 : pas d'hypothèse de sens ; on rapporte l'écart par graine.

Tout écart entre ces hypothèses et les résultats sera rapporté sans réécrire l'hypothèse.

### Résultats (ajouté après exécution, 16/10/2026)

Voir `prototype/F-JEPA_flotte_etiquetee.ipynb`, section 9 : **H10 et H12 sont confirmées, H11 ne l'est pas** ; pour H13, l'écart est rapporté graine par graine. Avec les étiquettes des 16 machines, les réseaux fine-tunés sont devant le boosting expert sur le test M1–M16, mais l'encodeur à poids aléatoires fait aussi bien que JEPA : le pré-entraînement n'y est pour rien. Les hypothèses ci-dessus n'ont pas été modifiées après exécution.
