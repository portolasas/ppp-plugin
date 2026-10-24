"""Control versions for "paste code" (source code schema).

Confirmed state: Studio September/October 2026, classic controls, same tenant for all projects (probe from a Studio
export of 2026-09-29 used in ReiRue and Orga-Otto; Timer from the serialization of an existing app). On PA2105 (outdated version) or PA2108 (unknown property) take a new probe:
"copy code" per control type in Studio, or `Src/*.pa.yaml` of a current solution export of the same environment.
Never guess. A project that needs other versions keeps its own `versionen.py` next to its generator; `ppp run`
finds it first.
"""
VERSIONEN = {
    "Label": "Label@2.5.1",
    "Button": "Classic/Button@2.2.0",
    "Rectangle": "Rectangle@2.3.0",
    "Image": "Image@2.2.3",
    "Container": "GroupContainer@1.5.0",
    "Gallery": "Gallery@2.15.0",
    "TextInput": "Classic/TextInput@2.3.2",
    "DropDown": "Classic/DropDown@2.3.1",
    "ComboBox": "Classic/ComboBox@2.4.0",
    "DatePicker": "Classic/DatePicker@2.6.0",
    "CheckBox": "Classic/CheckBox@2.1.0",
    "Timer": "Timer@2.1.0",
}
QUELLE = "confirmed: Studio export 2026-09-29 (probe of ReiRue and Orga-Otto), Timer from an existing app"
