#!/usr/bin/python

import pandas as pd
import sqlite3
import re
import logging

logging.basicConfig(level=logging.INFO)


class CustomError(Exception):
    pass


def createTable(tablename, db_name="pokemon.db"):
    db = sqlite3.connect(db_name)
    cursor = db.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS " + tablename +
                   "(NUMBER int, GERMAN text, ATTACKS_LV text, ATTACKS_EVOL text, GEN text)")
    db.commit()
    db.close()
    return None


def get_gen(tables):
    gen = ""
    index = 0
    while not gen:
        try:
            logging.debug(tables[index].iloc[3])
            gen = re.search(r'[0-9]+\.\s\w*', tables[index][0][0])[0]
        except (TypeError, KeyError, IndexError):
            try:
                gen = re.search(r'[0-9]+\.\s\w*', tables[index][1][0])[0]
            except (TypeError, KeyError, IndexError):
                index += 1
        if index >= len(tables):
            raise CustomError
    for i in range(index+1, len(tables)):
        try:
            logging.debug(tables[i].iloc[3])
            ng = re.search(r'[0-9]+\.\s\w*', tables[i][0][0])[0]
        except (TypeError, KeyError, IndexError):
            try:
                ng = re.search(r'[0-9]+\.\s\w*', tables[i][1][0])[0]
            except (TypeError, KeyError, IndexError):
                continue
        if ng != gen:
            break
    return gen, tables[:i]


def get_attacks(tables):
    # find attack tables with leveling and pre eveolutions
    attacks_lv_raw = []
    attacks_evolutions_raw = []
    for table in tables:
        k = 0
        for k in range(len(table)):
            if "Attacke" in list(table.iloc[k]):
                break
        if "Lv." in list(table.iloc[k]):
            attacks_lv_raw += list(table[1][4:-1])
        if "Methode" in list(table.iloc[k]):
            attacks_evolutions_raw += list(table[0][3:-1])
    attacks_lv = list(set([re.search(r'\w*', attack)[0] for attack in attacks_lv_raw]))
    attacks_evolutions = [re.search(r'\w*', attack)[0] for attack in attacks_evolutions_raw]
    # Remove "Attacke"
    attacks_lv = [item for item in attacks_lv if item != "Attacke"]
    attacks_evolutions = [item for item in attacks_evolutions if item != "Attacke"]
    return attacks_lv, attacks_evolutions


def get_info(url):
    tables = pd.read_html(url)
    gen, tables = get_gen(tables)
    attacks_lv, attacks_evolutions = get_attacks(tables)
    return (list_to_string(attacks_lv), list_to_string(attacks_evolutions), gen)


def create_pokemon_in_table(number, german, attacks_lv, attacks_evol, gen, db_name="pokemon.db", tablename="pokemon_raw_n"):
    db = sqlite3.connect(db_name)
    cursor = db.cursor()
    cursor.execute("INSERT INTO " + tablename + " (NUMBER, GERMAN, ATTACKS_LV, ATTACKS_EVOL, GEN) VALUES('" + str(number) + "','" + german + "','" + str(attacks_lv) + "','" + str(attacks_evol) + "','" + gen + "');")
    db.commit()
    db.close()
    return None


def get_pokemon(start_pokemon):
    url = "https://www.pokewiki.de/Pok%C3%A9mon-Liste"
    table = pd.read_html(url)
    p_deu = list(table[0].loc[:, "Deutsch"])
    if start_pokemon:
        return p_deu[p_deu.index(start_pokemon):]
    else:
        return p_deu


def list_to_string(input):
    output = ""
    for item in input:
        output += str(item) + ","
    return output[:-1]


def init_raw_table(start_pokemon=None):
    """
    creates a sqlite database with list of all pokemons together with their generation and their attacks. Only german names are included. It does this by querying pokewiki.de
    """
    createTable(tablename="pokemon_raw_n")
    list_pokemon = get_pokemon(start_pokemon)
    number = 1
    for pokemon in list_pokemon:
        logging.info(pokemon)
        url = "https://www.pokewiki.de/" + pokemon + "/Attacken"
        try:
            attacks_lv, attacks_evol, gen = get_info(url)
            print(attacks_lv, attacks_evol, gen)
            create_pokemon_in_table(number, pokemon, attacks_lv, attacks_evol, gen)
        except sqlite3.OperationalError as e:
            print(e)
            print("ERROR: Enter only pokemon name")
            create_pokemon_in_table(number, pokemon, "", "", "")
        except UnicodeEncodeError as e:
            print(e)
            print("ERROR: Enter only pokemon name")
            create_pokemon_in_table(number, pokemon, "", "", "")
        except CustomError:
            print("ERROR: Enter only pokemon name")
            create_pokemon_in_table(number, pokemon, "", "", "")
        number += 1
    return None


# init_raw_table()
# createTable(tablename="pokemon_raw_n")
