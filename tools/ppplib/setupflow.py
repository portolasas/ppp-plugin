"""Setup flow from components/sharepoint/schema.json (ANFORDERUNGEN T3, PLUGIN PL-15, ASUM pattern).

The logic is written into the scaffold that the user created in the designer and exported: a manual trigger with the
text input "Phase", one "Send an HTTP request to SharePoint" (its connection and site address are the template for
every request) and one "Respond to a PowerApp or flow" with the output "ergebnis". Origin: ASUM
komponenten/powerautomate/ASUM_Setup/build.py (imported and run twice in the tenant, 2026-10-08), generalized.

Behaviour: phase Schema creates missing lists, sets the Title index, adds missing fields and missing choice values;
phase Daten inserts start values only for missing keys and, optionally, the caller as first admin; Alles = both.
Never changes or deletes fields, lists or items (exception: the optional schema version setting).
"""
from __future__ import annotations

import copy
import json
import re

from .flows import walk

# ------------------------------------------------------------------ building blocks for workflow definitions


def expr(s: str) -> str:
    return "@" + s


def after(name=None, states=None) -> dict:
    return {name: states or ["SUCCEEDED"]} if name else {}


def compose(value, prev=None) -> dict:
    return {"type": "Compose", "inputs": value, "runAfter": after(prev)}


def cond(test, yes, no=None, prev=None) -> dict:
    return {"type": "If", "expression": test, "actions": yes, "else": {"actions": no or {}}, "runAfter": after(prev)}


def eq(left, right) -> dict:
    return {"equals": [left, right]}


def gt(left, right) -> dict:
    return {"greater": [left, right]}


def loop(items, actions, prev=None, parallel=None) -> dict:
    a = {"type": "Foreach", "foreach": items, "actions": actions, "runAfter": after(prev)}
    if parallel:
        a["runtimeConfiguration"] = {"concurrency": {"repetitions": parallel}}
    return a


def scope(actions, prev=None, states=None) -> dict:
    return {"type": "Scope", "actions": actions, "runAfter": after(prev, states)}


def filt(items, predicate, prev=None) -> dict:
    return {"type": "Query", "inputs": {"from": items, "where": predicate}, "runAfter": after(prev)}


def select(items, mapping, prev=None) -> dict:
    return {"type": "Select", "inputs": {"from": items, "select": mapping}, "runAfter": after(prev)}


def var(name, kind, value, prev=None) -> dict:
    return {"type": "InitializeVariable", "inputs": {"variables": [{"name": name, "type": kind, "value": value}]},
            "runAfter": after(prev)}


def setvar(name, value, prev=None) -> dict:
    return {"type": "SetVariable", "inputs": {"name": name, "value": value}, "runAfter": after(prev)}


def append(name, value, prev=None, states=None) -> dict:
    return {"type": "AppendToArrayVariable", "inputs": {"name": name, "value": value}, "runAfter": after(prev, states)}


def inc(name, prev=None) -> dict:
    return {"type": "IncrementVariable", "inputs": {"name": name, "value": 1}, "runAfter": after(prev)}


def obj(*pairs, base="json('{}')") -> str:
    """addProperty chain; pairs = (key, expression)."""
    o = base
    for k, v in pairs:
        o = f"addProperty({o},'{k}',{v})"
    return o


def meta(type_expression) -> str:
    return "addProperty(json('{}'),'type'," + type_expression + ")"


def cut(x, length) -> str:
    """Text cut to at most `length` characters. substring() needs a start index below the text length, also for empty
    text (ASUM run 2026-10-08), so a blank is appended and only the real length is read."""
    s = f"string(coalesce({x},''))"
    return f"substring(concat({s},' '),0,min(length({s}),{length}))"


class Http:
    """SharePoint HTTP actions from the template action of the scaffold (host, connection, site address stay)."""

    def __init__(self, template: dict):
        self.template = template
        self.writing: list[str] = []

    def __call__(self, name, method, uri, prev=None, body=None, merge=False, states=None) -> dict:
        assert not uri.startswith("@"), f"{name}: the URI must start with fixed text (PA-20260929-MAC-01)"
        a = copy.deepcopy(self.template)
        p = a["inputs"]["parameters"]
        write = method == "POST"
        p["parameters/method"] = method
        p["parameters/uri"] = uri
        p["parameters/headers"] = {
            "Accept": "application/json;odata=verbose",
            **({"Content-Type": "application/json;odata=verbose"} if write else {}),
            **({"IF-MATCH": "*", "X-HTTP-Method": "MERGE"} if merge else {}),
        }
        p.pop("parameters/body", None)
        if body is not None:
            p["parameters/body"] = body
        a["runAfter"] = after(prev, states)
        a.pop("metadata", None)
        if write:
            a["inputs"]["retryPolicy"] = {"type": "none"}
            self.writing.append(name)
        return a


def lift_bodies(actions: dict) -> dict:
    """HTTP bodies built with json() go into their own Compose (ppp verify C7 warns on json( in a body)."""
    out = {}
    for name, action in actions.items():
        if isinstance(action.get("actions"), dict):
            action["actions"] = lift_bodies(action["actions"])
        if isinstance(action.get("else"), dict):
            action["else"]["actions"] = lift_bodies(action["else"]["actions"])
        if action["type"] == "OpenApiConnection":
            body = action["inputs"]["parameters"].get("parameters/body")
            if isinstance(body, str) and "json(" in body:
                bn = "Body_" + name
                assert bn not in out and bn not in actions
                out[bn] = compose(body)
                out[bn]["runAfter"] = action["runAfter"]
                action["inputs"]["parameters"]["parameters/body"] = expr("outputs('" + bn + "')")
                action["runAfter"] = after(bn)
        out[name] = action
    return out


# ------------------------------------------------------------------ templates from the scaffold
class ScaffoldError(Exception):
    pass


def templates(workflow: dict) -> tuple[dict, dict, str, str | None]:
    """(HTTP template, response template, internal key of the trigger input Phase, note on the site address)."""
    d = workflow["properties"]["definition"]
    http = [a for _, a, *_ in walk(d.get("actions") or {})
            if a.get("type") == "OpenApiConnection" and (a.get("inputs") or {}).get("host", {}).get("operationId") == "HttpRequest"
            and str(a["inputs"]["host"].get("apiId", "")).endswith("shared_sharepointonline")]
    if not http:
        raise ScaffoldError("no 'Send an HTTP request to SharePoint' in the flow; add one in the designer and export again")
    kinds = {json.dumps(a["inputs"].get("host"), sort_keys=True) + str(a["inputs"]["parameters"].get("dataset")) for a in http}
    if len(kinds) > 1:
        raise ScaffoldError("SharePoint HTTP actions with different connections or sites; the template is not unique")
    site = str(http[0]["inputs"]["parameters"].get("dataset", ""))
    note = None
    if not site.startswith("@"):
        note = ("site address is fixed text, not an environment variable; the flow cannot move between environments "
                "without editing (T8)")
    else:
        params = {k for k, v in (d.get("parameters") or {}).items() if (v.get("metadata") or {}).get("schemaName")}
        if not any(p in site for p in params):
            note = "site address is an expression without an environment variable (T8)"
    responses = [a for _, a, *_ in walk(d.get("actions") or {}) if a.get("type") == "Response"]
    if len(responses) != 1:
        raise ScaffoldError(f"exactly one 'Respond to a PowerApp or flow' expected, found {len(responses)}")
    keys = list(((responses[0].get("inputs") or {}).get("body") or {}).keys())
    if keys != ["ergebnis"]:
        raise ScaffoldError(f"the response needs exactly one text output 'ergebnis', found {keys}")
    trigger = next(iter((d.get("triggers") or {}).values()), {})
    props = (((trigger.get("inputs") or {}).get("schema") or {}).get("properties") or {})
    phase = next((k for k, v in props.items() if v.get("title") == "Phase"), None)
    if not phase:
        raise ScaffoldError(f"the trigger needs a text input 'Phase', found {[v.get('title') for v in props.values()]}")
    return copy.deepcopy(http[0]), copy.deepcopy(responses[0]), phase, note


def list_uri(item_expression, rest="") -> str:
    return "_api/web/lists/getbytitle('@{" + item_expression + "}')" + rest


def fixed_list_uri(title: str, rest="") -> str:
    return f"_api/web/lists/getbytitle('{title}')" + rest


# ------------------------------------------------------------------ the flow
def build(definition: dict, prefix: str, http_template: dict, response_template: dict, phase_key: str) -> tuple[dict, list[str]]:
    """Actions of the setup flow and the names of the writing HTTP actions (retryPolicy none)."""
    setup = definition.get("setup") or {}
    run_list = setup.get("laufListe")
    version_part = setup.get("versionEinstellung")
    admin_part = setup.get("ersterAdmin")
    http = Http(http_template)
    phase = f"triggerBody()?['{phase_key}']"
    run_name = "workflow()?['run']?['name']"
    status = "if(empty(variables('setupFehler')),'OK','Fehler')"
    error_text = "join(variables('setupFehler'),'; ')"
    result_text = "join(variables('setupErgebnis'),'; ')"

    a = {}
    a["Definition"] = compose(definition)
    a["setupFehler"] = var("setupFehler", "array", [], "Definition")
    a["setupErgebnis"] = var("setupErgebnis", "array", [], "setupFehler")
    a["setupLaufItemId"] = var("setupLaufItemId", "integer", 0, "setupErgebnis")
    a["setupLaufTyp"] = var("setupLaufTyp", "string", "", "setupLaufItemId")
    a["setupNeu"] = var("setupNeu", "integer", 0, "setupLaufTyp")

    def catch(name, try_name, label, length=800):
        return scope({f"{name}_merken": append("setupFehler", expr(
            f"concat('{label}: ',{cut(f'result({chr(39)}{try_name}{chr(39)})', length)})"))}, try_name, ["FAILED", "TIMEDOUT"])

    # ---- phase Schema
    lst = "items('Schema_Liste')?['titel']"
    field_uri = list_uri(lst, "/fields/getbyinternalnameortitle('@{items('Schema_Feld')?['name']}')")
    values = "coalesce(items('Schema_Feld')?['werte'],json('[]'))"
    existing = "coalesce(body('Auswahl_lesen')?['d']?['Choices']?['results'],json('[]'))"
    # beside Feld_anlegen_wenn_fehlt, not in its else branch: otherwise level 9 > 8 (ASUM package 1.0.0.22)
    add_choices = {"Auswahl_pruefen": cond(
        {"and": [gt(expr("length(body('Feld_finden'))"), 0), eq(expr(f"empty({values})"), False)]},
        {"Auswahl_lesen": http("Auswahl_lesen", "GET", field_uri + "?$select=Choices"),
         "Auswahl_fehlt": filt(expr(values), expr(f"not(contains({existing},item()))"), "Auswahl_lesen"),
         "Auswahl_wenn_noetig": cond(
             gt(expr("length(body('Auswahl_fehlt'))"), 0),
             {"Auswahl_ergaenzen": http("Auswahl_ergaenzen", "POST", field_uri, merge=True, body=expr("string(" + obj(
                 ("Choices", f"addProperty(json('{{\"__metadata\":{{\"type\":\"Collection(Edm.String)\"}}}}'),'results',"
                             f"union({existing},body('Auswahl_fehlt')))"),
                 base="json('{\"__metadata\":{\"type\":\"SP.FieldChoice\"}}')") + ")")),
              "Auswahl_zaehlen": inc("setupNeu", "Auswahl_ergaenzen")},
             prev="Auswahl_fehlt")}, prev="Feld_anlegen_wenn_fehlt")}
    field_try = {
        "Feld_finden": filt(expr("body('Felder_lesen')?['d']?['results']"),
                            expr("equals(item()?['InternalName'],items('Schema_Feld')?['name'])")),
        "Feld_anlegen_wenn_fehlt": cond(
            eq(expr("length(body('Feld_finden'))"), 0),
            {"Feld_anlegen": http("Feld_anlegen", "POST", list_uri(lst, "/fields/createfieldasxml"), body=expr(
                "string(addProperty(json('{}'),'parameters',addProperty(addProperty(json('{\"__metadata\":{\"type\":"
                "\"SP.XmlSchemaFieldCreationInformation\"}}'),'SchemaXml',items('Schema_Feld')?['schemaXml']),"
                "'Options',coalesce(outputs('Definition')?['optionen'],25))))")),
             "Neues_Feld_zaehlen": inc("setupNeu", "Feld_anlegen")},
            prev="Feld_finden"),
        **add_choices,
    }
    want_index = "items('Schema_Liste')?['titelFeld']?['Indexed']"
    want_unique = "items('Schema_Liste')?['titelFeld']?['EnforceUniqueValues']"
    title_field = "first(body('Title_Feld_finden'))"
    schema_try = {
        "Liste_finden": filt(expr("body('Alle_Listen')?['d']?['results']"), expr("equals(item()?['Title']," + lst + ")")),
        "Liste_anlegen_wenn_fehlt": cond(
            eq(expr("length(body('Liste_finden'))"), 0),
            {"Liste_anlegen": http("Liste_anlegen", "POST", "_api/web/lists", body=expr("string(" + obj(
                ("BaseTemplate", "coalesce(items('Schema_Liste')?['basis'],100)"), ("Title", lst),
                ("Description", "coalesce(items('Schema_Liste')?['beschreibung'],'')"),
                base="json('{\"__metadata\":{\"type\":\"SP.List\"}}')") + ")")),
             "Neue_Liste_zaehlen": inc("setupNeu", "Liste_anlegen")},
            prev="Liste_finden"),
        "Felder_lesen": http("Felder_lesen", "GET",
                             list_uri(lst, "/fields?$select=InternalName,Indexed,EnforceUniqueValues&$top=5000"),
                             "Liste_anlegen_wenn_fehlt"),
        "Title_Feld_finden": filt(expr("body('Felder_lesen')?['d']?['results']"),
                                  expr("equals(item()?['InternalName'],'Title')"), "Felder_lesen"),
        # only ever raised: index on, uniqueness on when wanted; never switched off
        "Title_indizieren": cond(
            {"and": [eq(expr(f"coalesce({want_index},false)"), True),
                     {"or": [eq(expr(f"{title_field}?['Indexed']"), False),
                             {"and": [eq(expr(f"coalesce({want_unique},false)"), True),
                                      eq(expr(f"{title_field}?['EnforceUniqueValues']"), False)]}]}]},
            {"Title_Index_setzen": http(
                "Title_Index_setzen", "POST", list_uri(lst, "/fields/getbyinternalnameortitle('Title')"),
                body=expr("string(" + obj(
                    ("Indexed", "true"),
                    ("EnforceUniqueValues", f"or(coalesce({want_unique},false),coalesce({title_field}?['EnforceUniqueValues'],false))"),
                    base="json('{\"__metadata\":{\"type\":\"SP.Field\"}}')") + ")"), merge=True)},
            prev="Title_Feld_finden"),
        "Schema_Feld": loop(expr("coalesce(items('Schema_Liste')?['felder'],json('[]'))"), field_try, "Title_indizieren"),
    }
    schema_list = {
        "Neu_zuruecksetzen": setvar("setupNeu", 0),
        "Try_Schema_Liste": scope(schema_try, "Neu_zuruecksetzen"),
        "Schema_merken": append("setupErgebnis", expr("concat(" + lst + ",': neu=',string(variables('setupNeu')))"),
                                "Try_Schema_Liste"),
        "Catch_Schema_Liste": scope({"Schema_Fehler_merken": append("setupFehler", expr(
            "concat('Schema '," + lst + ",': '," + cut("result('Try_Schema_Liste')", 800) + ")"))},
            "Try_Schema_Liste", ["FAILED", "TIMEDOUT"]),
    }
    schema_actions = {"Schema_Liste": loop(expr("outputs('Definition')?['listen']"), schema_list)}
    if version_part:
        vlist, vtitle = version_part["liste"], version_part["titel"]
        version = "coalesce(outputs('Definition')?['schemaVersion'],outputs('Definition')?['version'])"
        vtype = "body('Einst_Typ')?['d']?['ListItemEntityTypeFullName']"
        version_try = {
            "Einst_Typ": http("Einst_Typ", "GET", fixed_list_uri(vlist, "?$select=ListItemEntityTypeFullName")),
            "Einst_lesen": http("Einst_lesen", "GET", fixed_list_uri(vlist, "/items?$select=Id,Title&$top=5000"), "Einst_Typ"),
            "Version_finden": filt(expr("body('Einst_lesen')?['d']?['results']"),
                                   expr(f"equals(item()?['Title'],'{vtitle}')"), "Einst_lesen"),
            "Version_setzen": cond(
                eq(expr("length(body('Version_finden'))"), 0),
                {"Version_anlegen": http("Version_anlegen", "POST", fixed_list_uri(vlist, "/items"), body=expr(
                    "string(" + obj(("__metadata", meta(vtype)), ("Title", f"'{vtitle}'"), ("Wert", version),
                                    ("Beschreibung", "'set by the setup flow'")) + ")"))},
                {"Version_aktualisieren": http(
                    "Version_aktualisieren", "POST", fixed_list_uri(vlist, "/items(@{first(body('Version_finden'))?['Id']})"),
                    body=expr("string(" + obj(("__metadata", meta(vtype)), ("Wert", version)) + ")"), merge=True)},
                prev="Version_finden"),
            "Version_merken": append("setupErgebnis", expr(f"concat('{vtitle}=',{version})"), "Version_setzen"),
        }
        schema_actions["Version_Try"] = scope(version_try, "Schema_Liste")
        schema_actions["Version_Catch"] = scope({"Version_Fehler_merken": append("setupFehler", expr(
            f"concat('{vtitle}: '," + cut("result('Version_Try')", 800) + ")"))}, "Version_Try", ["FAILED", "TIMEDOUT"])

    # ---- phase Daten
    dlist = "items('Daten_Liste')?['liste']"
    key = "items('Daten_Liste')?['schluessel']"
    data_try = {
        "Daten_Typ": http("Daten_Typ", "GET", list_uri(dlist, "?$select=ListItemEntityTypeFullName")),
        "Daten_vorhanden": http("Daten_vorhanden", "GET", list_uri(dlist, "/items?$select=@{" + key + "}&$top=5000"), "Daten_Typ"),
        "Daten_Schluessel": select(expr("body('Daten_vorhanden')?['d']?['results']"), expr("item()?[" + key + "]"), "Daten_vorhanden"),
        "Daten_fehlend": filt(expr("items('Daten_Liste')?['items']"),
                              expr("not(contains(body('Daten_Schluessel'),item()?[" + key + "]))"), "Daten_Schluessel"),
        "Daten_Eintrag": loop(expr("body('Daten_fehlend')"), {
            "Daten_einfuegen": http("Daten_einfuegen", "POST", list_uri(dlist, "/items"), body=expr(
                "string(setProperty(items('Daten_Eintrag'),'__metadata',"
                + meta("body('Daten_Typ')?['d']?['ListItemEntityTypeFullName']") + "))"))},
            "Daten_fehlend", parallel=5),
    }
    data_list = {
        "Try_Daten_Liste": scope(data_try),
        "Daten_merken": append("setupErgebnis", expr(
            "concat(" + dlist + ",': vorhanden=',string(sub(length(items('Daten_Liste')?['items']),"
            "length(body('Daten_fehlend')))),', neu=',string(length(body('Daten_fehlend'))))"), "Try_Daten_Liste"),
        "Catch_Daten_Liste": scope({"Daten_Fehler_merken": append("setupFehler", expr(
            "concat('Daten '," + dlist + ",': '," + cut("result('Try_Daten_Liste')", 800) + ")"))},
            "Try_Daten_Liste", ["FAILED", "TIMEDOUT"]),
    }
    data_actions = {"Daten_Liste": loop(expr("coalesce(outputs('Definition')?['daten'],json('[]'))"), data_list)}
    if admin_part:
        alist, role = admin_part["liste"], admin_part["rolle"]
        caller = "triggerOutputs()?['headers']?['x-ms-user-email']"
        rtype = "body('Rollen_Typ')?['d']?['ListItemEntityTypeFullName']"
        admin_try = {
            "Rollen_Typ": http("Rollen_Typ", "GET", fixed_list_uri(alist, "?$select=ListItemEntityTypeFullName")),
            "Rollen_lesen": http("Rollen_lesen", "GET", fixed_list_uri(alist, "/items?$select=Id,Rolle,Aktiv&$top=5000"), "Rollen_Typ"),
            "Admins_finden": filt(expr("body('Rollen_lesen')?['d']?['results']"),
                                  expr(f"and(equals(item()?['Rolle'],'{role}'),equals(item()?['Aktiv'],true))"), "Rollen_lesen"),
            "Admin_eintragen_wenn_keiner": cond(
                {"and": [eq(expr("length(body('Admins_finden'))"), 0), eq(expr("empty(coalesce(" + caller + ",''))"), False)]},
                {"Admin_eintragen": http("Admin_eintragen", "POST", fixed_list_uri(alist, "/items"), body=expr(
                    "string(" + obj(("__metadata", meta(rtype)), ("Title", "toLower(" + caller + ")"),
                                    ("Rolle", f"'{role}'"), ("Aktiv", "true")) + ")")),
                 "Admin_merken": append("setupErgebnis", f"{alist}: first {role} added", "Admin_eintragen")},
                {"Admin_vorhanden_merken": append("setupErgebnis", expr(
                    f"concat('{alist}: {role}=',string(length(body('Admins_finden'))))"))},
                prev="Admins_finden"),
        }
        data_actions["Admin_Try"] = scope(admin_try, "Daten_Liste")
        data_actions["Admin_Catch"] = scope({"Admin_Fehler_merken": append("setupFehler", expr(
            f"concat('First {role}: '," + cut("result('Admin_Try')", 800) + ")"))}, "Admin_Try", ["FAILED", "TIMEDOUT"])

    is_phase = lambda *values: {"or": [eq(expr(phase), v) for v in values]}  # noqa: E731
    main = {
        "Alle_Listen": http("Alle_Listen", "GET", "_api/web/lists?$select=Title&$top=5000"),
        "Wenn_Schema": cond(is_phase("Schema", "Alles"), schema_actions, prev="Alle_Listen"),
        "Wenn_Daten": cond(is_phase("Daten", "Alles"), data_actions, prev="Wenn_Schema"),
    }
    catch_setup = {"Abbruch_merken": append("setupFehler", expr("concat('Abbruch: '," + cut("result('Try_Setup')", 1500) + ")"))}

    if run_list:
        run_uri = fixed_list_uri(run_list, "/items(@{variables('setupLaufItemId')})")
        start_body = expr("string(" + obj(
            ("__metadata", meta("variables('setupLaufTyp')")), ("Title", run_name), ("Art", "'Setup'"),
            ("Status", "'Laeuft'"), ("Modus", f"string({phase})"), ("Start", "utcNow()")) + ")")
        end_fields = (("Status", status), ("Ende", "utcNow()"), ("Ergebnis", result_text), ("Meldung", error_text))
        end_new = expr("string(" + obj(
            ("__metadata", meta("variables('setupLaufTyp')")), ("Title", run_name), ("Art", "'Setup'"),
            ("Modus", f"string({phase})"), ("Start", "utcNow()"), *end_fields) + ")")
        end_merge = expr("string(" + obj(("__metadata", meta("variables('setupLaufTyp')")), *end_fields) + ")")
        # the run entry at the start only if the run list exists already (first schema run: created at the end)
        start_run = {
            "Laeufe_Typ": http("Laeufe_Typ", "GET", fixed_list_uri(run_list, "?$select=ListItemEntityTypeFullName")),
            "Laeufe_Typ_merken": setvar("setupLaufTyp", expr("body('Laeufe_Typ')?['d']?['ListItemEntityTypeFullName']"), "Laeufe_Typ"),
            "Lauf_anlegen": http("Lauf_anlegen", "POST", fixed_list_uri(run_list, "/items"), "Laeufe_Typ_merken", start_body),
            "Lauf_Id_merken": setvar("setupLaufItemId", expr("int(body('Lauf_anlegen')?['d']?['Id'])"), "Lauf_anlegen"),
        }
        main = {
            "Alle_Listen": main["Alle_Listen"],
            "Laeufe_finden": filt(expr("body('Alle_Listen')?['d']?['results']"),
                                  expr(f"equals(item()?['Title'],'{run_list}')"), "Alle_Listen"),
            "Lauf_starten": cond(gt(expr("length(body('Laeufe_finden'))"), 0), start_run, prev="Laeufe_finden"),
            "Wenn_Schema": {**main["Wenn_Schema"], "runAfter": after("Lauf_starten")},
            "Wenn_Daten": main["Wenn_Daten"],
            "Laeufe_Typ_nachladen": cond(eq(expr("variables('setupLaufTyp')"), ""), {
                "Laeufe_Typ_neu": http("Laeufe_Typ_neu", "GET", fixed_list_uri(run_list, "?$select=ListItemEntityTypeFullName")),
                "Laeufe_Typ_neu_merken": setvar("setupLaufTyp", expr("body('Laeufe_Typ_neu')?['d']?['ListItemEntityTypeFullName']"),
                                                "Laeufe_Typ_neu")}, prev="Wenn_Daten"),
            "Lauf_abschliessen": cond(
                eq(expr("variables('setupLaufItemId')"), 0),
                {"Lauf_neu_abschliessen": http("Lauf_neu_abschliessen", "POST", fixed_list_uri(run_list, "/items"), body=end_new)},
                {"Lauf_aktualisieren": http("Lauf_aktualisieren", "POST", run_uri, body=end_merge, merge=True)},
                prev="Laeufe_Typ_nachladen"),
        }
        catch_setup["Abbruch_vermerken"] = cond(gt(expr("variables('setupLaufItemId')"), 0), {
            "Lauf_Abbruch": http("Lauf_Abbruch", "POST", run_uri, body=end_merge, merge=True)}, prev="Abbruch_merken")

    a["Phase_pruefen"] = cond(
        is_phase("Schema", "Daten", "Alles"),
        {"Try_Setup": scope(main), "Catch_Setup": scope(catch_setup, "Try_Setup", ["FAILED", "TIMEDOUT"])},
        {"Phase_ungueltig": append("setupFehler", "Phase must be Schema, Daten or Alles")},
        prev="setupNeu")

    response = copy.deepcopy(response_template)
    response.pop("metadata", None)
    response["inputs"]["body"] = {"ergebnis": expr(
        "concat(" + status + ",': ',if(empty(variables('setupFehler'))," + result_text + "," + error_text + "))")}
    response["runAfter"] = after("Phase_pruefen", ["SUCCEEDED", "FAILED", "TIMEDOUT", "SKIPPED"])
    a["Antwort"] = response
    a["Abbruch_bei_Fehler"] = cond(gt(expr("length(variables('setupFehler'))"), 0), {"Fehler_beenden": {
        "type": "Terminate", "runAfter": {},
        "inputs": {"runStatus": "Failed", "runError": {"code": f"{prefix.upper()}_SETUP", "message": expr(error_text)}}}},
        prev="Antwort")
    return lift_bodies(a), http.writing


def replace_value(text: str, key: str, new, after_marker: str | None = None) -> str:
    """Replace the JSON value after `"<key>": ` (first one after the marker), indented like the export (CRLF);
    every other byte of the file stays as it is (origin: ASUM paket.py)."""
    marker = f'"{key}": '
    start = text.index(marker, text.index(after_marker) if after_marker else 0) + len(marker)
    _, length = json.JSONDecoder().raw_decode(text[start:])
    line = text.rfind("\n", 0, start) + 1
    indent = re.match(r"[ \t]*", text[line:]).group(0)
    newline = "\r\n" if "\r\n" in text else "\n"
    payload = json.dumps(new, ensure_ascii=False, indent=2).replace("\n", newline + indent)
    return text[:start] + payload + text[start + length:]
