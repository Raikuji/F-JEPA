# Prototype F-JEPA

Notebook : `F-JEPA_prototype.ipynb`. Les sorties ont été vidées pour alléger le fichier. La version déjà exécutée, avec les résultats et les figures, est jointe dans le fil du projet.

Pour le relancer :

    cd prototype
    pip install -r requirements.txt
    jupyter notebook F-JEPA_prototype.ipynb

Le notebook lit les exports Teeptrak dans `../input/`, sans les modifier, et écrit dans `results/` :
- `metrics.csv` : les scores sur le test ;
- `test_predictions.png` : les prédictions sur la période de test ;
- `jepa_seed*.pt` : les poids des modèles.

Le pré-entraînement JEPA prend environ 5 minutes sur CPU.
