#!/usr/bin/env python3
"""Structural checker for TallyPrime TDL source files.

TDL only executes inside Tally, so the mistakes that cost the most time are the
ones Tally reports as a load abort (T0008 "Could not find the default TDL
definition of ...", "Could not find description!") or as a runtime "Bad
formula". Both come from references that do not resolve: a Part listing a Line
that was never defined, a field storing into an undeclared UDF, a function
calling a name that does not exist, an unbalanced IF.

This checks those statically:

  * every referenced Part/Line/Field/Button/Form/Report/Collection/Function
    resolves to a definition in the file or to a known Tally built-in
  * every ``Storage`` target and ``$...UDF`` method is declared in [System: UDF]
    with a unique index inside the developer range 20001-59999
  * every ``@@Formula`` resolves to a [System: Formula] entry
  * inside functions: step numbers ascend, IF/ELSE/ENDIF and WALK/END WALK are
    balanced, INSERT COLLECTION OBJECT is matched by SET TARGET : ..,
    ``##variables`` are declared, and $$Function targets exist and are callable
    (``$$Function`` splits its arguments on ":", so neither the function name
    nor an argument may contain one)

Usage: tdl_lint.py <file.tdl> [...]
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Definitions TallyPrime ships with. Referencing these is expected; they are
# not defined in the add-on.
BUILTIN_FIELDS = {
    "default",
    "name field",
    "logical field",
    "number field",
    "amount field",
    "date field",
    "simple field",
    "short name field",
    "rate field",
    "qty primary field",
}
BUILTIN_TABLE_TOKENS = {"not applicable", "endoflist", "end of list"}
# Variables Tally itself maintains (##SVCurrentCompany and friends).
BUILTIN_VARIABLE_PREFIXES = ("sv", "sys")

DEF_RE = re.compile(r"^\[\s*(#?)\s*([A-Za-z ]+?)\s*:\s*(.+?)\s*\]\s*$")
STEP_RE = re.compile(r"^(\d+)\s*:\s*(.*)$")


@dataclass
class Definition:
    kind: str
    name: str
    line_no: int
    modifies: bool
    body: list[tuple[int, str]] = field(default_factory=list)


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, path: Path, line_no: int, message: str) -> None:
        self.errors.append(f"{path}:{line_no}: error: {message}")

    def warn(self, path: Path, line_no: int, message: str) -> None:
        self.warnings.append(f"{path}:{line_no}: warning: {message}")


def strip_comment(line: str) -> str:
    """Remove a ``;;`` comment, ignoring ``;;`` inside a quoted string."""
    in_quote = False
    for i, ch in enumerate(line):
        if ch == '"':
            in_quote = not in_quote
        elif ch == ";" and not in_quote and line[i : i + 2] == ";;":
            return line[:i]
    return line


def split_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def key(kind: str, name: str) -> str:
    return f"{kind.lower()}:{name.strip().lower()}"


def parse(path: Path, report: Report) -> tuple[dict[str, Definition], list[Definition]]:
    definitions: dict[str, Definition] = {}
    order: list[Definition] = []
    current: Definition | None = None

    for line_no, raw in enumerate(path.read_text().splitlines(), start=1):
        line = strip_comment(raw).rstrip()
        if not line.strip():
            continue

        match = DEF_RE.match(line.strip())
        if match:
            modifies, kind, name = match.group(1) == "#", match.group(2), match.group(3)
            current = Definition(kind=kind, name=name, line_no=line_no, modifies=modifies)
            order.append(current)
            if not modifies:
                dup = definitions.get(key(kind, name))
                # Tally merges repeated [System: ...] blocks, so only the other
                # definition types can genuinely collide.
                if dup is not None and kind.lower() != "system":
                    report.error(
                        path,
                        line_no,
                        f"duplicate definition [{kind}: {name}] (first at line {dup.line_no})",
                    )
                definitions[key(kind, name)] = current
            continue

        if current is None:
            report.error(path, line_no, f"content outside any definition: {line.strip()!r}")
            continue

        if line.count('"') % 2:
            report.error(path, line_no, "unbalanced double quote")
        if line.count("(") != line.count(")"):
            report.error(path, line_no, "unbalanced parenthesis")

        current.body.append((line_no, line.strip()))

    return definitions, order


def attribute(body_line: str) -> tuple[str, str]:
    """Split ``Name : value`` into its attribute name and the rest."""
    name, sep, value = body_line.partition(":")
    return (name.strip().lower(), value.strip() if sep else "")


def check_references(
    path: Path, definitions: dict[str, Definition], order: list[Definition], report: Report
) -> None:
    udfs: dict[str, int] = {}
    for definition in order:
        if definition.kind.lower() == "system" and definition.name.lower() == "udf":
            for line_no, body_line in definition.body:
                parts = [part.strip() for part in body_line.split(":")]
                if len(parts) != 3:
                    report.error(path, line_no, f"malformed UDF declaration: {body_line!r}")
                    continue
                name, _udf_type, index = parts
                if not index.isdigit():
                    report.error(path, line_no, f"UDF index is not a number: {index!r}")
                    continue
                number = int(index)
                if not 20001 <= number <= 59999:
                    report.error(
                        path, line_no, f"UDF index {number} is outside the developer range 20001-59999"
                    )
                if number in udfs.values():
                    report.error(path, line_no, f"UDF index {number} is used twice")
                udfs[name.lower()] = number

    formulas = {
        body_line.partition(":")[0].strip().lower()
        for definition in order
        if definition.kind.lower() == "system" and definition.name.lower() == "formula"
        for _line_no, body_line in definition.body
    }

    def require(kind: str, name: str, line_no: int, context: str) -> None:
        if key(kind, name) in definitions:
            return
        if kind == "Field" and name.strip().lower() in BUILTIN_FIELDS:
            return
        report.error(path, line_no, f"{context} references undefined [{kind}: {name}]")

    for definition in order:
        kind = definition.kind.lower()
        for line_no, body_line in definition.body:
            name, value = attribute(body_line)
            where = f"[{definition.kind}: {definition.name}]"

            if kind == "part" and name == "lines":
                for item in split_list(value):
                    require("Line", item, line_no, where)
            elif kind == "line" and name == "fields":
                for item in split_list(value):
                    require("Field", item, line_no, where)
            elif kind == "form" and name == "parts":
                for item in split_list(value):
                    require("Part", item, line_no, where)
            elif kind == "report" and name == "form":
                for item in split_list(value):
                    require("Form", item, line_no, where)
            elif name == "use":
                require("Field", value, line_no, where)
            elif name == "table":
                for item in split_list(value):
                    if item.lower() in BUILTIN_TABLE_TOKENS:
                        continue
                    require("Collection", item, line_no, where)
            elif kind == "collection" and name == "collection":
                for item in split_list(value):
                    require("Collection", item, line_no, where)
            elif name == "filter":
                for item in split_list(value):
                    if item.lower() not in formulas:
                        report.error(
                            path, line_no, f"{where} filter {item!r} has no [System: Formula] entry"
                        )
            elif name == "storage":
                if value.lower() not in udfs:
                    report.error(path, line_no, f"{where} stores into undeclared UDF {value!r}")
            elif name == "add" or name == "local":
                sub_kind, _, rest = value.partition(":")
                sub_kind = sub_kind.strip()
                target = rest.partition(":")[0].strip() if ":" in rest else rest.strip()
                if sub_kind.lower() in {"button", "field", "part", "line"} and target:
                    require(sub_kind.title(), target, line_no, where)
            elif name == "action":
                verb, _, target = value.partition(":")
                verb, target = verb.strip().lower(), target.strip()
                if verb == "call":
                    require("Function", target, line_no, where)
                elif verb in {"display", "alter", "create", "displaycollection"}:
                    require("Report", target, line_no, where)

            for formula in re.findall(r"@@([A-Za-z][A-Za-z0-9_]*)", body_line):
                if formula.lower() in formulas or formula.lower().startswith(
                    BUILTIN_VARIABLE_PREFIXES
                ):
                    continue
                report.error(path, line_no, f"{where} uses @@{formula} with no definition")

            for udf in re.findall(r"\$([A-Za-z][A-Za-z0-9_]*UDF)\b", body_line):
                if udf.lower() not in udfs:
                    report.error(path, line_no, f"{where} reads undeclared UDF ${udf}")


def check_functions(path: Path, order: list[Definition], report: Report) -> None:
    function_names = {
        definition.name.strip().lower()
        for definition in order
        if definition.kind.lower() == "function"
    }

    for definition in order:
        if definition.kind.lower() != "function":
            continue

        where = f"[Function: {definition.name}]"
        declared: set[str] = set()
        steps: list[tuple[int, int, str]] = []

        for line_no, body_line in definition.body:
            name, value = attribute(body_line)
            if name in {"variable", "parameter"}:
                declared.add(value.partition(":")[0].strip().lower())
                continue
            if name == "returns":
                continue
            step = STEP_RE.match(body_line)
            if step is None:
                report.error(path, line_no, f"{where} statement has no step number: {body_line!r}")
                continue
            steps.append((line_no, int(step.group(1)), step.group(2).strip()))

        previous = -1
        if_depth = walk_depth = object_depth = 0
        for line_no, number, statement in steps:
            if number <= previous:
                report.error(
                    path, line_no, f"{where} step {number} does not come after step {previous}"
                )
            previous = number

            verb = statement.partition(":")[0].strip().lower()
            if verb == "if":
                if_depth += 1
            elif verb == "endif":
                if_depth -= 1
                if if_depth < 0:
                    report.error(path, line_no, f"{where} ENDIF without a matching IF")
                    if_depth = 0
            elif verb in {"else", "else if", "elseif"}:
                if if_depth == 0:
                    report.error(path, line_no, f"{where} ELSE outside an IF")
                if verb != "else" or statement.partition(":")[2].strip():
                    report.error(
                        path,
                        line_no,
                        f"{where} ELSE takes no condition (ELSE IF is not valid in a function)",
                    )
            elif verb == "walk collection":
                walk_depth += 1
            elif verb == "end walk":
                walk_depth -= 1
                if walk_depth < 0:
                    report.error(path, line_no, f"{where} END WALK without a matching WALK")
                    walk_depth = 0
            elif verb == "insert collection object":
                object_depth += 1
            elif verb == "set target" and statement.partition(":")[2].strip() == "..":
                object_depth -= 1
                if object_depth < 0:
                    report.error(
                        path,
                        line_no,
                        f"{where} SET TARGET : .. leaves more objects than were inserted",
                    )
                    object_depth = 0
            elif verb == "set":
                target = statement.split(":")[1].strip().lower() if ":" in statement else ""
                if target and target not in declared:
                    report.error(path, line_no, f"{where} assigns to undeclared variable {target!r}")

            for variable in re.findall(r"##([A-Za-z][A-Za-z0-9_]*)", statement):
                if variable.lower() in declared or variable.lower().startswith(
                    BUILTIN_VARIABLE_PREFIXES
                ):
                    continue
                report.error(path, line_no, f"{where} uses undeclared variable ##{variable}")

            for call in re.findall(r"\$\$Function\s*:\s*([^:\s]+)", statement):
                if call.strip().lower() not in function_names:
                    report.error(path, line_no, f"{where} calls undefined function {call!r}")

            # $$Function splits on ":", so an argument of the form
            # $Method:Object:Name is read as three separate arguments.
            for arguments in re.findall(
                r"\$\$Function\s*:\s*[A-Za-z0-9_]+"
                r"((?:\s*:\s*(?:##[A-Za-z0-9_]+|\$[A-Za-z0-9_]+(?::[A-Za-z0-9_]+)*"
                r'|"[^"]*"|[0-9.]+))*)',
                statement,
            ):
                if re.search(r"\$[A-Za-z0-9_]+\s*:", arguments):
                    report.error(
                        path,
                        line_no,
                        f"{where} passes a method reference inline to $$Function; "
                        "fetch it into a variable first",
                    )

            if re.search(r"\$\$Function\s*:\s*[A-Za-z0-9_]+\s+[A-Za-z]", statement):
                report.error(
                    path,
                    line_no,
                    f"{where} calls a function whose name contains a space; "
                    "$$Function cannot parse it",
                )

        if if_depth:
            report.error(path, definition.line_no, f"{where} has {if_depth} unclosed IF block(s)")
        if walk_depth:
            report.error(path, definition.line_no, f"{where} has an unclosed WALK COLLECTION")
        if object_depth:
            report.error(
                path,
                definition.line_no,
                f"{where} inserts {object_depth} collection object(s) without SET TARGET : ..",
            )

    for definition in order:
        if definition.kind.lower() == "function" and " " in definition.name.strip():
            report.warn(
                path,
                definition.line_no,
                f"[Function: {definition.name}] has a space in its name: it can be used with "
                "Action : Call but not with $$Function",
            )


def lint(path: Path) -> Report:
    report = Report()
    definitions, order = parse(path, report)
    check_references(path, definitions, order, report)
    check_functions(path, order, report)
    return report


def main(argv: list[str]) -> int:
    paths = [Path(arg) for arg in argv[1:]]
    if not paths:
        print(__doc__)
        return 2

    failed = False
    for path in paths:
        if not path.is_file():
            print(f"{path}: error: file not found")
            failed = True
            continue
        report = lint(path)
        for message in report.warnings:
            print(message)
        for message in report.errors:
            print(message)
        if report.errors:
            failed = True
            print(f"{path}: FAILED with {len(report.errors)} error(s)")
        else:
            print(f"{path}: OK ({len(report.warnings)} warning(s))")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
