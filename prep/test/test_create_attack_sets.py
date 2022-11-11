import pytest
import create_attack_sets


def test_powerset():
    superset = {"A", "B"}
    expect1 = {("A",), ("B",), ("A", "B"), ("A", "B")}
    expect2 = {("A",), ("B",), ("A", "B"), ("B", "A")}
    result = create_attack_sets.powerset(superset)
    assert expect1 == result or expect2 == result


# def test_is_unique():
#     entry = 
#     create_attack_sets.Pokemon()
