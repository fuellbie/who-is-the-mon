import pytest
import create_attack_sets

def test_powerset():
    superset = {"A", "B", "C"}
    expect = {("A"), ("B"), ("C"), ("A", "B"), ("A", "C"), ("B", "C"), ("A", "B", "C")}
    result = create_attack_sets.powerset(superset)
    assert expect == result
