#!/usr/bin/python

import sqlite3
import logging
import copy
import itertools
import time
import sys

logging.basicConfig(level=logging.INFO)
# logging.basicConfig(level=logging.DEBUG, filename="debug.log")

GENERATIONS = [
    # "1. Generation",  # Done
    # "2. Generation",  # Done
    # "3. Generation",  # Done
    "4. Generation",
    "5. Generation",
    "5. Generation",
    "6. Generation",
    "7. Generation",
    "8. Generation",
]


class CustomError(Exception):
    pass


def powerset(superset):
    result = set()
    print("Create all attacksets... 0%", end="\r")
    for k in range(1, len(superset) + 1):
        if k / len(superset) * 100 % 1 == 0:
            print(
                "Create all attacksets... " + str(int(k / len(superset) * 100)) + "%",
                end="\r",
            )
        result = result.union(set(itertools.combinations(superset, k)))
    return result


def in_list(name, pokemon_list):
    for pokemon in pokemon_list:
        for pokemon_name in list(pokemon.name.split("/")):
            if name == pokemon_name:
                return True
    return False


class Graph:
    def __init__(self, generation, db_name):
        self.db_name = db_name
        self.generation = generation
        self.pokemon = self.select_pokemon()  # list
        self.edges = self.create_edges()  # dict {uuid: edge}

    def minimize_attack_sets(self):

        for pokemon in self.pokemon:

            # EXCEPTION - Ignore Attacksets
            if pokemon.name in ("Riolu/Lucario"):
                continue

            logging.info(
                "Compute attacksets for %s %s...", str(pokemon.number), pokemon
            )
            potential_attacksets = powerset(pokemon.all_attacks)
            # pot_attackset_iterator = powerset(pokemon.all_attacks)

            # Copy attackset
            print("Copy attackset ... ", end="\r")
            pot_attackset_iterator = list(copy.deepcopy(potential_attacksets))
            sys.stdout.flush()
            print("Copy attackset ... Done", end="\r")
            sys.stdout.flush()

            # Find unique attackets
            counter = 0
            print("Find unique attacksets... 0%", end="\r")
            sys.stdout.flush()
            for attackset in pot_attackset_iterator:
                counter += 1
                if counter / len(pot_attackset_iterator) * 100 % 1 == 0:
                    print(
                        "Find unique attacksets... "
                        + str(int(counter / len(pot_attackset_iterator) * 100))
                        + "%",
                        end="\r",
                    )
                if not pokemon.is_unique(attackset):
                    potential_attacksets.remove(attackset)

            sys.stdout.flush()

            # Copy attackset
            print("Copy attackset ... ", end="\r")
            pot_attackset_iterator = list(copy.deepcopy(potential_attacksets))
            sys.stdout.flush()
            print("Copy attackset ... Done", end="\r")
            sys.stdout.flush()

            # Reduce attacksets
            counter = 0
            length = int((len(pot_attackset_iterator) ** 2) / 2)
            print("Reduce attacksets... 0% - " + str(length) + "            ", end="\r")
            print("Reduce attacksets... 0% -                  ", end="\r")
            sys.stdout.flush()
            removed = set()  # Collect index of removed attackset
            for a1 in range(len(pot_attackset_iterator)):
                if a1 in removed:
                    counter += len(pot_attackset_iterator) - a1
                    continue
                for a2 in range(a1, len(pot_attackset_iterator)):
                    counter += 1
                    if counter / length * 100 % 1 == 0:
                        print(
                            "Reduce attacksets... "
                            + str(int((counter / length) * 100))
                            + "% - "
                            + str(length-counter)
                            + "        ",
                            end="\r",
                        )
                    if a2 in removed or a1 == a2:
                        continue
                    if set(pot_attackset_iterator[a2]).issubset(
                        set(pot_attackset_iterator[a1])
                    ):
                        potential_attacksets.remove(pot_attackset_iterator[a1])
                        removed.add(a1)
                        counter += len(pot_attackset_iterator) - a2
                        print(
                            "Reduce attacksets... "
                            + str(int((counter / length) * 100))
                            + "% - "
                            + str(length-counter)
                            + "        ",
                            end="\r",
                        )
                        break
                    elif set(pot_attackset_iterator[a1]).issubset(
                        set(pot_attackset_iterator[a2])
                    ):
                        potential_attacksets.remove(pot_attackset_iterator[a2])
                        removed.add(a2)
                        counter += len(pot_attackset_iterator) - a2
                        print(
                            "Reduce attacksets... "
                            + str(int((counter / length) * 100))
                            + "% - "
                            + str(length - counter)
                            + "        ",
                            end="\r",
                        )
                        break
            sys.stdout.flush()

            pokemon.attacksets = potential_attacksets
        return None

    def create_edges(self):
        """
        create edges between pokemon. For each attack which exists on both pokemon's attack sets, an edge with the name of the attack is created. A reference to the edge is saved into the "edges" of each pokemon and to self.edges of the graph
        """
        logging.info("Start creating graph ...")
        edges = dict()

        logging.debug(self.pokemon)

        for p1 in self.pokemon:
            logging.debug("Create edges for %s with counter %s", p1, str(p1.counter))
            for p2 in self.pokemon[p1.counter :]:

                logging.debug("Create edges for %s and %s", p1, p2)
                for attack in p1.all_attacks:
                    logging.debug("Create edge for %s", attack)
                    edge = self.Edge(p1, p2, attack, self)
                    if edge.common_attack:
                        edges[edge.uuid] = edge
        logging.info("Graph created.")
        return edges

    def remove_edge(self, edge):
        del self.edges[edge]

    def remove_all_edges(self):
        logging.info("Delete edges ... ")
        for uuid in list(self.edges.keys()):
            self.edges[uuid].delete()
        logging.info("Done")

    def select_pokemon(self, tablename="pokemon_raw_n"):
        """
        Get pokemon from database and save in Graph
        """
        db = sqlite3.connect(self.db_name)
        cursor = db.cursor()
        cursor.execute(
            "SELECT * FROM " + tablename + " WHERE GEN='" + self.generation + "'"
        )
        rows = cursor.fetchall()
        db.close()
        pokemons = []
        for row in rows:
            if row[1] in ("Papinella", "Pudox"):
                pokemons.append(Graph.Pokemon((row[0], row[1], set(row[2].split(",")))))
            else:
                pokemons.append(
                    Graph.Pokemon(self.merge_attacks(row))
                )  # TODO - consider removing merge_attacks
        return self.merge_pokemon(pokemons)

    def merge_attacks(self, row):
        """
        Merge attacks from lvl up and pre evolution to a set
        """
        attacks = []
        for attack in row[2].split(",") + row[3].split(","):
            if attack:
                attacks.append(attack)
        return (row[0], row[1], set(attacks))

    def merge_pokemon(self, pokemons):
        """
        Merge pokemons with the same attack sets, such as Amonitas and Amoroso.
        Return List of Pokemon Objects with name "Amonitas/Amoroso"
        """
        new_pokemon_list = []

        pokemon_group = ""
        pokemon_group_number = ""
        start_number = pokemons[0].number

        counter = 0
        for p1 in pokemons:

            counter += 1
            if in_list(p1.name, new_pokemon_list):
                counter -= 1
                continue
            p1.counter = counter
            pokemon_group = p1.name
            pokemon_group_number = str(p1.number)

            original_counter = int(p1.number) - start_number + 1

            # EXCEPTIONS
            # Ignore specific pokemon overall to keep them single
            if p1.name in (
                "Rabauz",
                "Ditto",
                "Deoxys - Initiativform",
                "Deoxys - Normalform",
                "Deoxys - Verteidigungsform",
                "Deoxys - Angriffsform",
            ):
                pass
            else:

                for p2 in pokemons[original_counter:]:

                    # EXCEPTIONS
                    # Ignore specific pokemon for merging
                    if p2.name in ("Rabauz", "Tanhel") or (
                        p1.name == "Raupy" and p2.name == "Kokuna"
                    ):
                        continue

                    # Manually merge
                    if (
                        (p1.name == "Raupy" and p2.name in ("Safcon", "Smettbo"))
                        or (p1.name == "Hornliu" and p2.name in ("Kokuna", "Bibor"))
                        or (p1.name == "Quiekel" and p2.name in ("Keifel"))
                        or (
                            p1.name == "Bummelz" and p2.name in ("Muntier", "Letarking")
                        )
                        or (p1.name == "Waumpel" and p2.name in ("Panekon", "Schaloko"))
                        or (
                            p1.name == "Loturzel"
                            and p2.name in ("Lombrero", "Kappalores")
                        )
                        or (
                            p1.name == "Geckarbor"
                            and p2.name in ("Reptain", "Gewaldro")
                        )
                        or (p1.name == "Flemmli" and p2.name in ("Jungglut", "Lohgock"))
                        or (p1.name == "Hydropi" and p2.name in ("Moorabbel", "Sumpex"))
                        or (p1.name == "Wingull" and p2.name in ("Pelipper"))
                        or (p1.name == "Camaub" and p2.name in ("Camerupt"))
                        or (
                            p1.name == "Knacklion"
                            and p2.name in ("Vibrava", "Lielldra")
                        )
                        or (p1.name == "Knilz" and p2.name in ("Kapilz"))
                        or p1.all_attacks.issubset(p2.all_attacks)
                        or p2.all_attacks.issubset(p1.all_attacks)
                    ):
                        # Merge
                        pokemon_group += "/" + p2.name
                        pokemon_group_number += "/" + str(p2.number)
                        p1.all_attacks = p1.all_attacks.union(p2.all_attacks)

            p1.name = pokemon_group
            p1.number = pokemon_group_number
            new_pokemon_list.append(p1)
        return new_pokemon_list

    class Edge:
        def __init__(self, pokemon1, pokemon2, attack, graph):
            self.v = {pokemon1, pokemon2}
            self.name = attack
            self.graph = graph
            self.common_attack = True
            self.uuid = "(" + str(self.v) + ", " + self.name + ")"

            if not (attack in pokemon1.all_attacks and attack in pokemon2.all_attacks):
                logging.debug(
                    "STOP EDGE CREATION - %s is not a common attack in %s.",
                    attack,
                    self,
                )
                self.common_attack = False
                return None
            else:
                pokemon1.add_edge(self)
                pokemon2.add_edge(self)

        def __str__(self):
            return "(" + str(self.v) + ", " + self.name + ")"

        def __repr__(self):
            return "(" + str(self.v) + ", " + self.name + ")"

        def get_other(self, pokemon):
            other_list = list(self.v.difference({pokemon}))
            if len(other_list) == 1:
                return other_list[0]
            else:
                logging.error("%s is not in edge %s.", pokemon, self)
                raise CustomError

        def delete(self):
            logging.debug("Remove edge %s.", self)

            pokemon = list(self.v)[0]
            other = list(self.v)[1]

            # remove from pokemon
            pokemon.remove_edge(self)
            other.remove_edge(self)

            # remove from graph
            self.graph.remove_edge(self.uuid)
            return None

    class Pokemon:
        def __init__(self, entry):
            self.number = entry[0]
            self.counter = entry[0]
            self.name = entry[1]
            self.attacksets = {}
            self.all_attacks = entry[2]
            self.edges = dict()  # {pokemon: {attack: Edge}}

        def is_unique(self, attackset):
            for pokemon in self.edges.keys():
                if len(attackset) <= len(self.edges[pokemon]):
                    # compare attacks
                    subset = True
                    for attack in attackset:
                        if attack not in self.edges[pokemon]:
                            subset = False
                            break
                    if subset:
                        logging.debug(
                            "%s's attackset %s is a subset of %s's attackset.",
                            self,
                            attackset,
                            pokemon.name,
                        )
                        return False
            return True

        def __str__(self):
            return self.name

        def __repr__(self):
            return self.name

        def get_edges(self):
            print(self.edges)

        def add_edge(self, edge):
            # Check if common attack
            if self not in edge.v:
                logging.error("Pokemon %s not part of edge %s.", self.name, edge)
                raise CustomError
            attack = edge.name
            other = edge.get_other(self)

            #  Check if Edge already exists
            if other not in self.edges.keys():
                self.edges[other] = dict()
            if other in self.edges[other].keys():
                logging.info("Edge already exists")
                return None
            self.edges[other][attack] = edge

        def remove_edge(self, edge):
            logging.debug("Delete %s from %s", edge, self)
            attack = edge.name
            other = edge.get_other(self)

            del self.edges[other][attack]
            if not self.edges[other]:
                del self.edges[other]

        def return_attacksets(self):
            attacksets_string = ""
            for attackset in list(self.attacksets):
                attacksets_string += str(set(attackset)) + ","
            return attacksets_string[:-1]

        def print_attacksets(self):
            print(self.name + ": " + self.return_attacksets())

        def return_attacks(self):
            attacks_string = ""
            for attack in list(self.all_attacks):
                attacks_string += attack + ","
            return attacks_string[:-1]

        def print_attacks(self):
            print(self.name + ": " + self.return_attacks())


def createTable(tablename="pokemon_attacksets", db_name="pokemon.db"):
    db = sqlite3.connect(db_name)
    cursor = db.cursor()
    cursor.execute("DROP table  IF EXISTS " + tablename)
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS "
        + tablename
        + "(NUMBER text, NAME_GER text, ATTACKS_GER text, ATTACKSETS_GER text, NAME_ENG text, ATTACKS_ENG text, ATTACKSETS_ENG text, NAME_JAP text, ATTACKS_JAP text, ATTACKSETS_JAP text, GEN text)"
    )
    db.commit()
    db.close()
    return None


def populate_db_table_with_attacksets(
    pokegraph, tablename="pokemon_attacksets", db_name="pokemon.db"
):
    db = sqlite3.connect(db_name)
    cursor = db.cursor()
    for pokemon in pokegraph.pokemon:
        cursor.execute(
            "INSERT INTO "
            + tablename
            + " (NUMBER, NAME_GER, ATTACKS_GER, ATTACKSETS_GER, GEN) VALUES(?,?,?,?,?)",
            (
                str(pokemon.number),
                pokemon.name,
                str(pokemon.all_attacks),
                str(pokemon.attacksets),
                pokegraph.generation,
            ),
        )
    db.commit()
    db.close()


# Testing and Debugging

# pokegraph = Graph("1. Generation")
# pokegraph.minimize_attack_sets()

# Create table
# createTable()

# Print for debugging
# for pokemon in pokegraph.pokemon:
#     pokemon.print_attacks()
#     pokemon.print_attacksets()

# Populate table
# populate_db_table_with_attacksets(pokegraph)

# Productive run

# Create table

duration = dict()
db_name = "pokemon.db"
for generation in GENERATIONS:

    tablename = "Gen" + generation[0] + "_pokemon_attacksets"
    # create graph
    pokegraph = Graph(generation, db_name)
    start = time.time()
    pokegraph.minimize_attack_sets()
    end = time.time()

    duration[generation] = end - start

    # Print for debugging
    # print()
    # for pokemon in pokegraph.pokemon:
    #     # pokemon.print_attacks()
    #     # pokemon.print_attacksets()
    #     if pokemon.name in ("Lapras", "Arktos"):
    #         pokemon.print_attacks()
    #         pokemon.print_attacksets()
    #         print("Edges:", str(pokemon.edges))
    #         print()

    # populate table
    createTable(tablename=tablename, db_name=db_name)
    populate_db_table_with_attacksets(pokegraph, tablename=tablename, db_name=db_name)

for generation in GENERATIONS:
    print(generation, "took", str(duration[generation]), "seconds.")
