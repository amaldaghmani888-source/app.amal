# Carnet de santé de la femme — application Flask

## Démarrage
- Python 3.10+
- `pip install -r requirements.txt`
- `python app.py`
- Ouvrir http://127.0.0.1:5000

## Logique fonctionnelle
L'interface principale est un carnet de santé (et non un tableau de bord administratif). Chaque femme dispose d'un dossier contenant son profil, son historique médical, ses vaccinations, son suivi du dépistage du cancer du sein et ses rendez-vous.
Les indicateurs sont calculés à partir des actes saisis dans les carnets, via la page « Indicateurs de santé ».

## À valider avant usage réel
Les profils et actes préchargés sont fictifs. Le calcul « dossiers avec au moins une vaccination / dossiers créés » et « dossiers avec au moins un dépistage / dossiers créés » est descriptif et ne constitue pas une couverture populationnelle officielle. Pour des indicateurs officiels, ajouter les dénominateurs cibles validés (par âge, période et territoire) et les définitions nationales.
Ce prototype n'intègre pas encore l'authentification, les rôles, le chiffrement, la traçabilité ni les exigences d'hébergement des données de santé. Ne pas y saisir de données personnelles ou médicales réelles avant mise en conformité et sécurisation.
