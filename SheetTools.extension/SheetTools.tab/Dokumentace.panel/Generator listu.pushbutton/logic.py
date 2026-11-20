# -*- coding: utf-8 -*-
"""Logika generátoru listů bez závislosti na Revit API."""

import json
import os


def load_sheet_sets(json_path):
    """Načte sady výkresů z JSON souboru a vrátí jejich seznam."""
    with open(json_path, "r", encoding="utf-8") as source:
        data = json.load(source)
    if not isinstance(data, dict) or not isinstance(data.get("sets"), dict):
        raise ValueError("JSON musí obsahovat objekt 'sets' se sadami výkresů.")
    return data["sets"]


def validate_sheet_set(items):
    """Zkontroluje povinná pole a duplicitní čísla v jedné sadě."""
    errors = []
    seen = {}
    valid_items = []

    if not isinstance(items, list):
        return [], ["Sada musí být seznamem výkresů."]

    for index, item in enumerate(items):
        row = index + 1
        if not isinstance(item, dict):
            errors.append("Řádek {}: položka není objekt.".format(row))
            continue

        number = item.get("number")
        name = item.get("name")

        if not isinstance(number, str) or not number.strip():
            errors.append("Řádek {}: chybí číslo výkresu.".format(row))
            continue
        if not isinstance(name, str) or not name.strip():
            errors.append("Řádek {} ({}): chybí název výkresu.".format(row, number))
            continue

        number = number.strip()
        name = name.strip()
        if number in seen:
            errors.append(
                "Duplicitní číslo '{}' na řádcích {} a {}.".format(
                    number, seen[number], row
                )
            )
            continue

        seen[number] = row
        valid_items.append({"number": number, "name": name})

    # Při duplicitě vyřadíme všechny výskyty daného čísla, aby nevzniklo
    # nejednoznačné rozhodnutí, který název má být použit.
    duplicate_numbers = set()
    counts = {}
    for item in items:
        if isinstance(item, dict):
            value = item.get("number")
            if isinstance(value, str) and value.strip():
                counts[value.strip()] = counts.get(value.strip(), 0) + 1
    duplicate_numbers = set(k for k, v in counts.items() if v > 1)
    valid_items = [x for x in valid_items if x["number"] not in duplicate_numbers]

    return valid_items, errors


def compare_with_existing(items, existing_numbers):
    """Rozdělí platné položky na nové listy a čísla již existující v projektu."""
    existing = set(existing_numbers)
    to_create = []
    already_exists = []
    for item in items:
        if item["number"] in existing:
            already_exists.append(item)
        else:
            to_create.append(item)
    return to_create, already_exists
