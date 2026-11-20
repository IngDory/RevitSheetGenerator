# -*- coding: utf-8 -*-
"""pyRevit tlačítko: generátor výkresových listů."""
import os
import sys

from pyrevit import revit, DB, forms, script

# Import čisté logiky ze stejné složky jako tento skript.
SCRIPT_DIR = os.path.dirname(__file__)
if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)

import logic

DOC = revit.doc
OUTPUT = script.get_output()


def get_titleblocks():
    """Vrátí všechna razítka (typy Title Block) načtená v projektu."""
    elements = (DB.FilteredElementCollector(DOC)
                .OfCategory(DB.BuiltInCategory.OST_TitleBlocks)
                .WhereElementIsElementType()
                .ToElements())
    return sorted(list(elements),
                  key=lambda x: (x.FamilyName or "", x.Name or ""))


def main():
    """Načte sadu, ověří ji, zobrazí náhled a vytvoří nové výkresové listy."""
    if DOC is None or DOC.IsFamilyDocument:
        forms.alert("Otevři projekt Revitu, nikoli editor rodiny.",
                    title="Generátor výkresových listů")
        return

    json_path = os.path.join(SCRIPT_DIR, "sheets.json")
    try:
        sheet_sets = logic.load_sheet_sets(json_path)
    except Exception as exc:
        forms.alert("Nepodařilo se načíst sheets.json:\n\n{}".format(exc),
                    title="Chyba vstupních dat")
        return

    if not sheet_sets:
        forms.alert("V souboru sheets.json nejsou definované žádné sady.",
                    title="Generátor výkresových listů")
        return

    set_name = forms.SelectFromList.show(
        sorted(sheet_sets.keys()),
        title="Vyber sadu výkresů",
        multiselect=False,
        button_name="Pokračovat")
    if not set_name:
        return

    valid_items, errors = logic.validate_sheet_set(sheet_sets[set_name])

    existing_numbers = [
        sheet.SheetNumber
        for sheet in DB.FilteredElementCollector(DOC).OfClass(DB.ViewSheet)
    ]
    to_create, already_exists = logic.compare_with_existing(
        valid_items, existing_numbers)

    titleblocks = get_titleblocks()
    if not titleblocks:
        forms.alert(
            "V projektu není načtené žádné výkresové razítko. "
            "Nejprve načti rodinu razítka.",
            title="Chybí razítko")
        return

    labels = ["{} : {}".format(tb.FamilyName, tb.Name)
              for tb in titleblocks]
    selected_label = forms.SelectFromList.show(
        labels,
        title="Vyber výkresové razítko",
        multiselect=False,
        button_name="Pokračovat")
    if not selected_label:
        return
    titleblock = titleblocks[labels.index(selected_label)]

    # Náhled před zápisem do projektu.
    lines = ["SADA: {}".format(set_name), "",
             "VYTVOŘÍ SE ({}):".format(len(to_create))]
    if to_create:
        lines.extend(["  + {} — {}".format(x["number"], x["name"])
                      for x in to_create])
    else:
        lines.append("  Žádné nové listy.")
    lines.extend(["", "PŘESKOČÍ SE – ČÍSLO JIŽ EXISTUJE ({}):".format(
        len(already_exists))])
    if already_exists:
        lines.extend(["  = {} — {}".format(x["number"], x["name"])
                      for x in already_exists])
    else:
        lines.append("  Žádné.")
    lines.extend(["", "CHYBNÉ POLOŽKY ({}):".format(len(errors))])
    if errors:
        lines.extend(["  ! {}".format(e) for e in errors])
    else:
        lines.append("  Žádné.")
    lines.extend(["", "Razítko: {}".format(selected_label),
                  "", "Pokračovat ve vytvoření uvedených nových listů?"])

    preview = "\n".join(lines)
    if not forms.alert(preview, title="Náhled výkresových listů",
                       yes=True, no=True):
        return

    if not to_create:
        forms.alert(
            "Nebyly nalezeny žádné nové platné listy. "
            "Zkontroluj případné chyby ve vstupních datech.",
            title="Bez změn")
        return

    created = []
    try:
        with revit.Transaction("Generátor výkresových listů"):
            for item in to_create:
                sheet = DB.ViewSheet.Create(DOC, titleblock.Id)
                sheet.SheetNumber = item["number"]
                sheet.Name = item["name"]
                created.append(item)
    except Exception as exc:
        forms.alert(
            "Vytváření selhalo. Transakce byla vrácena zpět:\n\n{}".format(exc),
            title="Chyba při vytváření")
        return

    OUTPUT.print_md("# Výsledek generátoru výkresových listů")
    OUTPUT.print_md("**Vytvořeno:** {} | **Přeskočeno:** {} | **Chyby:** {}".format(
        len(created), len(already_exists), len(errors)))
    for item in created:
        OUTPUT.print_md("- Vytvořeno: **{}** — {}".format(
            item["number"], item["name"]))
    for item in already_exists:
        OUTPUT.print_md("- Přeskočeno: **{}** — číslo již existuje".format(
            item["number"]))
    for error in errors:
        OUTPUT.print_md("- Chyba: {}".format(error))

    forms.alert(
        "Hotovo.\nVytvořeno: {}\nPřeskočeno: {}\nChybné položky: {}\n"
        "Podrobný přehled najdeš ve výstupu pyRevitu.".format(
            len(created), len(already_exists), len(errors)),
        title="Generátor výkresových listů")


if __name__ == "__main__":
    main()
