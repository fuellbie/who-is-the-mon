#!/usr/bin/python

import sqlite3
import logging
import copy
import itertools
import time

logging.basicConfig(level=logging.INFO)
# logging.basicConfig(level=logging.DEBUG)

GENERATIONS = [
        "1. Generation",
        "2. Generation",
        "3. Generation",
        "4. Generation",
        "5. Generation",
        "5. Generation",
        "6. Generation",
        "7. Generation",
        "8. Generation"
        ]


class CustomError(Exception):
    pass


def powerset(superset):
    result = set()
    for k in range(1, len(superset)+1):
        result = result.union(set(itertools.combinations(superset, k)))
    return result


class Graph():
    # TODO - Second round to remove empty attacksets:
    #       for pokemon with empty sets Identify evolutions, merge pokemon and rerun creation of attacksets

    def __init__(self, generation):
        self.generation = generation
        self.pokemon = self.select_pokemon()  # list
        self.edges = self.create_edges()  # dict {uuid: edge}

    def minimize_attack_sets(self):
        for pokemon in self.pokemon:
            logging.info("Compute attacksets for %s %s...", (str(pokemon.number), pokemon))
            potential_attacksets = powerset(pokemon.all_attacks)
            pot_attackset_iterator = list(copy.deepcopy(potential_attacksets))

            for attackset in pot_attackset_iterator:
                if not pokemon.is_unique(attackset):
                    potential_attacksets.remove(attackset)

            pot_attackset_iterator = list(copy.deepcopy(potential_attacksets))
            for a1 in range(len(pot_attackset_iterator)):
                for a2 in range(len(pot_attackset_iterator)):
                    if a1 == a2:
                        continue
                    if set(pot_attackset_iterator[a2]).issubset(set(pot_attackset_iterator[a1])):
                        potential_attacksets.remove(pot_attackset_iterator[a1])
                        break

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
            for p2 in self.pokemon[p1.counter:]:

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

    def select_pokemon(self, db_name="pokemon.db", tablename="pokemon_raw_n"):
        """
        Get pokemon from database and save in Graph
        """
        db = sqlite3.connect(db_name)
        cursor = db.cursor()
        cursor.execute("SELECT * FROM " + tablename + " WHERE GEN='" + self.generation + "'")
        rows = cursor.fetchall()
        db.close()
        pokemons = []
        for row in rows:
            pokemons.append(Graph.Pokemon(self.merge_attacks(row)))
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
        counter = 1
        for p1 in pokemons:
            if p1.name in pokemon_group:
                continue
            pokemon_group = p1.name
            pokemon_group_number = str(p1.number)
            for p2 in pokemons[p1.number:]:
                # TODO - gen2 does not merge pokemon, gen3 takes ages
                if p1.all_attacks.issubset(p2.all_attacks):
                    pokemon_group += "/" + p2.name
                    pokemon_group_number += "/" + str(p2.number)
                    p1.all_attacks = p1.all_attacks.union(p2.all_attacks)
                elif p2.all_attacks.issubset(p1.all_attacks):
                    pokemon_group += "/" + p2.name
                    pokemon_group_number += "/" + str(p2.number)
                    p1.all_attacks = p1.all_attacks.union(p2.all_attacks)

            p1.name = pokemon_group
            p1.number = pokemon_group_number
            p1.counter = counter
            counter += 1
            new_pokemon_list.append(p1)
        return new_pokemon_list

    class Edge():

        def __init__(self, pokemon1, pokemon2, attack, graph):
            self.v = {pokemon1, pokemon2}
            self.name = attack
            self.graph = graph
            self.common_attack = True
            self.uuid = "(" + str(self.v) + ", " + self.name + ")"

            if not (attack in pokemon1.all_attacks and attack in pokemon2.all_attacks):
                logging.debug("STOP EDGE CREATION - %s is not a common attack in %s.", attack, self)
                self.common_attack = False
                return None
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

    class Pokemon():

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
                        logging.debug("%s's attackset %s is a subset of %s's attackset.", self, attackset, pokemon.name)
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
    cursor.execute("CREATE TABLE IF NOT EXISTS " + tablename +
                   "(NUMBER text, NAME_GER text, ATTACKS_GER text, ATTACKSETS_GER text, NAME_ENG text, ATTACKS_ENG text, ATTACKSETS_ENG text, NAME_JAP text, ATTACKS_JAP text, ATTACKSETS_JAP text, GEN text)")
    db.commit()
    db.close()
    return None


def populate_db_table_with_attacksets(pokegraph, tablename="pokemon_attacksets", db_name="pokemon.db"):
    db = sqlite3.connect(db_name)
    cursor = db.cursor()
    for pokemon in pokegraph.pokemon:
        cursor.execute("INSERT INTO " + tablename + " (NUMBER, NAME_GER, ATTACKS_GER, ATTACKSETS_GER, GEN) VALUES(?,?,?,?,?)", (str(pokemon.number), pokemon.name, str(pokemon.all_attacks), str(pokemon.attacksets), pokegraph.generation))
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
createTable()

duration = dict()
for generation in GENERATIONS:

    # create graph
    pokegraph = Graph(generation)
    start = time.time()
    pokegraph.minimize_attack_sets()
    end = time.time()

    duration[generation] = end-start

    # populate table
    populate_db_table_with_attacksets(pokegraph)

for generation in GENERATIONS:
    print(generation, "took", str(duration[generation], "seconds."))
