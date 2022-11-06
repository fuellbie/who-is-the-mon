# Preperations

This section contains the scripts and information to prepare the data needed for the application

## init_db.py

This script fetches the pages from `www.pokewiki.de` to collect to attack information for the pokemon and writes them into a sqlite database.

## create_attack_sets.py

This script takes the information from the sqlite database created by the script `init_db.py` to create the attack sets used by the quiz. It writes them into the sqlite database into the table "pokemon_attacksets".
