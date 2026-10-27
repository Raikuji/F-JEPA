# Données capteurs SYNTHÉTIQUES : lire avant utilisation

**Ces données sont inventées.** Elles servent à valider une démarche (code, découpage, métriques, comparaison baselines / JEPA) sur une vérité terrain connue. Elles ne démontrent rien sur une machine réelle ni sur l'utilité industrielle de JEPA. Ne jamais les mélanger aux données réelles dans un tableau de résultats sans étiquette « SYNTHÉTIQUE ».

## Fichiers

| Fichier | Contenu |
|---|---|
| `synthetic_sensors.csv.gz` | 526 262 lignes (1 min) : `timestamp, running, speed, product, temperature_c, vibration_mm_s, current_a`. **Seul fichier à donner aux modèles.** |
| `synthetic_labels_GROUND_TRUTH.csv.gz` | Vérité terrain par minute (défaut, sévérité, événements bénins). **Jamais en entrée d'un modèle.** Évaluation uniquement. |
| `synthetic_fault_events.csv` | 21 défauts : début de dérive, instant de panne ou de maintenance |
| `synthetic_config.json` | Tous les paramètres, la graine, les facteurs de charge par produit |
| `generate_synthetic_sensors.py` | Générateur reproductible (graine 42) |
| `controle_visuel_synthetique.png` | Contrôle visuel de 2 défauts et de la canicule bénigne |

Reproduction : `python generate_synthetic_sensors.py <dossier_pickles> <sortie>`. Le générateur lit la timeline réelle (`perf_clean.pkl`, `events.pkl`).

## Ce qui est réel, ce qui est inventé

**Réel** (issu des exports) : états marche/arrêt/fermeture, cadence (événements par minute), produit, fenêtres d'arrêt non planifié (≥ 15 min) utilisées comme instants de panne.

**Inventé** : toutes les valeurs de capteurs, tous les défauts, l'attribution d'une cause à un arrêt réel. Les 18 pannes simulées sont posées au début d'arrêts réels, mais ces arrêts réels n'avaient aucune cause connue : l'attribution est fictive.

## Modèle de génération (hypothèses d'un technicien, non mesurées)

| Grandeur | Modèle sain |
|---|---|
| Courant | 4,5 A à vide, 12 A en charge nominale, proportionnel à la cadence et à un facteur de charge par produit (0,90 à 1,15, tiré au hasard), bruit AR(1) |
| Température | Filtre du premier ordre (τ = 40 min) vers ambiante + 30 °C × (I/I_nom)², ambiante saisonnière et journalière |
| Vibration | 1,1 mm/s RMS en marche, dépend de la vitesse et du produit, bruit log-normal ; 0,05 mm/s à l'arrêt |
| Transitoire | +15 à 20 % pendant ~10 min après un changement de produit (bénin) |

Les ordres de grandeur de vibration s'inspirent des zones de sévérité de type ISO 10816 (classe petites machines : environ 1,8 mm/s « limite », 4,5 mm/s « inacceptable »). Je les cite de mémoire : **à vérifier** avant de les mentionner dans un rapport.

## Défauts injectés

| Type | Nb pannes | Précurseur | Effet à pleine sévérité |
|---|---|---|---|
| Roulement | 6 (+2 préventifs) | 14 à 28 j, croissance accélérée | vibration ×4,2, température +9 °C, courant +4 % |
| Courroie / chaîne | 5 (+1 préventif) | 5 à 14 j, linéaire | vibration ×2,2 avec salves, courant +12 %, température +3 °C |
| Blocage mécanique | 4 | 2 à 7 j | courant +25 %, température +8 °C |
| Électrique brutal | 3 | 15 min | pic de courant : **pratiquement imprévisible** |

Les 3 « préventifs » sont des dégradations interrompues à 80 % par une maintenance : ce ne sont pas des pannes (cas censurés).

**Anomalies bénignes (ne doivent pas déclencher d'alerte de panne)** : canicule +5 °C ambiant (15 → 20 sept. 2025), dérive du capteur de température +3 °C (23 avr. → 5 mai 2026), capteur de température figé 12 h (20 mai 2026), 5 pertes de données de 2 à 6 h, transitoires de changement de produit. Un contrôle du script signale tout chevauchement avec un défaut. Les pertes de données, tirées au hasard, peuvent tomber dans une fenêtre de défaut : elles sont étiquetées dans la vérité terrain.

## Limites (à citer dans le rapport)

1. **Circularité.** J'ai défini à la fois les défauts et leur signature : une méthode qui les retrouve prouve que son code fonctionne, pas qu'elle fonctionnera sur du réel.
2. **Réalisme non vérifié.** Les paramètres ne viennent ni d'une fiche constructeur ni de mesures. Les défauts réels sont plus variés, souvent multivariés et non monotones.
3. **Capteurs sans panne inexpliquée.** Les signaux sont plus propres que des mesures industrielles réelles (pas de couplages parasites entre sous-systèmes, pas de dérives thermiques lentes inconnues).
4. **Peu de pannes pour le test.** Par date de panne, il y en a 9 de sept. à fév., 5 de mars à mai et 4 de juin à août. Un découpage chronologique laisse donc 4 pannes en test : les intervalles d'incertitude seront très larges. Prévoir une validation en fenêtre glissante, ou augmenter `n_failures` dans la configuration (en vérifiant le placement sans chevauchement).
5. **Taux de marche réel.** La machine est en marche environ 45 % du temps (cadence réelle), et plusieurs périodes d'arrêt prolongé existent : certains défauts simulés se développent donc sur des signaux souvent à l'arrêt.

## Hypothèses à écrire AVANT d'exécuter les modèles (pré-enregistrement)

- **H1.** Un EWMA ou un z-score sur la vibration détecte les défauts de roulement avant la panne. Une dérive monotone est le cas favorable aux méthodes statistiques ; si JEPA ne bat pas cette baseline ici, ce n'est pas un échec de JEPA.
- **H2.** Un seuil fixe sur la température déclenche de fausses alertes pendant la canicule et la dérive capteur.
- **H3.** Les défauts électriques brutaux ne sont pas anticipables : le rappel maximal à 15 min d'horizon est borné par 15/18 ≈ 83 % sur les pannes.
- **H4.** Si JEPA apporte un avantage, il se trouvera plutôt sur les blocages (courant anormal *pour une charge donnée*) et sur la réduction des fausses alertes bénignes, car il faut modéliser le contexte (cadence, produit). C'est une hypothèse, pas un résultat.

Tout écart entre ces hypothèses et les résultats doit être rapporté sans réécrire l'hypothèse.

## Ce que cette expérience permet de démontrer, et de réfuter

- **Démontrable :** le pipeline est correct (pas de fuite, métriques justes, lead time bien calculé) ; la sensibilité de chaque méthode à chaque type de défaut ; l'effet du bruit si on le fait varier.
- **Réfutable :** « JEPA détecte mieux que les baselines » *sur ces défauts-là*. Un résultat négatif ici est informatif.
- **Non démontrable :** toute affirmation sur une machine réelle, sur la calibration d'un risque de panne réel, ou sur la supériorité industrielle de JEPA.
