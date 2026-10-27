# Capteurs SYNTHÉTIQUES sur 4 ans (4 machines) : lire avant utilisation

**Ces données sont inventées.** Elles servent à tester si un modèle JEPA apprend une dynamique normale assez fine pour repérer des dégradations qui ne se voient pas dans le niveau des capteurs. Elles ne démontrent rien sur les machines réelles. Ne jamais les mélanger aux données réelles sans l'étiquette « SYNTHÉTIQUE ».

Générées le 15/10/2026 par `prototype/generation_capteurs_4ans.ipynb` (graine 2026, environ 4 minutes). Rien n'est tiré des exports Teeptrak : le planning de production est lui aussi simulé, contrairement à `input/files`.

## Fichiers

| Fichier | Contenu |
|---|---|
| `capteurs_<M1..M4>_<aaaa-aaaa>.csv.gz` | Une ligne par minute, une année d'exploitation (sept. → août) par fichier. Colonnes : `timestamp, machine, running, speed, product, temp_ambiante_c, temp_moteur_c, temp_palier_c, vibration_mm_s, courant_a, pression_bar`. **Seule entrée autorisée des modèles.** |
| `verite_terrain_degradations.csv` | 167 dégradations : machine, type, issue (panne / ralentissement / préventif), début de la dégradation, instant de l'événement, intervention. **Évaluation uniquement.** |
| `verite_terrain_benins.csv` | Canicules, recalibrages de capteurs, capteurs figés, pertes de données. **Évaluation uniquement.** |
| `config_generation.json` | Paramètres et graine |
| `controle_visuel.png` | Une journée saine et la veille d'un événement, pour chaque type |

Machines (noms indicatifs, paramètres inventés) : M1 Mouleuse, M2 Démouleuse, M3 Trancheuse, M4 Conditionneuse. Période : 01/09/2022 → 31/08/2026, 2 103 840 minutes par machine, en marche environ 39 % du temps.

## Principe : pas de lien direct entre niveau des capteurs et pannes

Une dégradation change la **dynamique** ou la **relation entre capteurs**, pas le niveau moyen :

| Type | Ce qui change |
|---|---|
| `refroidissement` | la température moteur suit la charge plus lentement (constante de temps ×2,5) |
| `roulement` | la résonance vibratoire glisse vers les basses vitesses ; bruit vibratoire plus corrélé dans le temps |
| `courroie` | le courant suit la vitesse avec retard, oscille lentement ; micro-glissements simultanés courant/vibration (intermittent) |
| `pneumatique` | le compresseur cycle plus vite (8 → 3,5 min), la pression chute plus vite atelier fermé (intermittent) |
| `electrique` | pic de courant dans les 10 dernières minutes : **imprévisible** à 7 jours |

Contrôle fait à la génération : l'écart du niveau moyen des 3 jours avant un événement est du même ordre (0,05 à 0,66 écart-type) que celui d'une fenêtre saine tirée au hasard.

Les grandes variations de **niveau** viennent d'événements bénins : saisons et canicules (+4 à +8 °C), recalibrages de capteurs (tous les 1 à 3 mois et une fois sur deux après réparation : ±1 à 3 °C, gain de vibration ×0,85 à ×1,2, ±0,2 à 0,6 A), vieillissement (+10 %/an de vibration, remis à zéro en août), changements de produit, capteurs figés, pertes de données, pics isolés. Le type et la date des dégradations ne dépendent pas de la saison.

## Limites

1. **Circularité, et cas favorable par construction.** J'ai choisi des signatures « dynamiques » précisément parce qu'un JEPA peut les apprendre et qu'un seuil ne le peut pas. Un bon score JEPA ici montre que la démarche fonctionne **si** les vraies dégradations ont cette nature ; seul un essai sur de vrais capteurs le dira.
2. **Réalisme non vérifié.** Ordres de grandeur plausibles, ni mesurés ni tirés d'une fiche constructeur.
3. **Un baseline expert peut tout retrouver** : avec les bonnes caractéristiques (autocorrélations, résidus d'un modèle physique), un boosting a accès aux mêmes signatures. C'est le vrai concurrent de JEPA ici.

## Hypothèses écrites AVANT d'exécuter les modèles (pré-enregistrement)

Protocole : prédire toutes les 2 h « panne ou ralentissement dans les 7 jours » à partir des 24 dernières heures ; train sept. 2022 → août 2024, validation sept. 2024 → août 2025, test sept. 2025 → août 2026.

- **H1.** Les seuils de niveau et l'EWMA restent proches du hasard (ROC-AUC < 0,60).
- **H2.** La surprise JEPA, sans étiquettes, bat les seuils de niveau.
- **H3.** La sonde sur les représentations JEPA bat le même encodeur non pré-entraîné, pour chaque graine.
- **H4.** Le boosting sur caractéristiques expertes égale ou bat JEPA.
- **H5.** Les défauts `electrique` restent imprévisibles (ROC-AUC ≈ 0,5 pour toutes les méthodes).

Tout écart entre ces hypothèses et les résultats sera rapporté sans réécrire l'hypothèse.
