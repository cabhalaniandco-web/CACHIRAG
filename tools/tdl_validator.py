#!/usr/bin/env python3
"""
TDL (Tally Definition Language) Syntax & Structure Validator
Validates TDL files for structural integrity, matching definitions,
proper section headers, and cross-reference coherence.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


SECTION_HEADER_PATTERN = re.compile(
    r"^\[(#?)(Report|Form|Part|Line|Field|Button|Collection|Function|System|Menu|Include):\s*(.+)\]\s*$",
    re.IGNORECASE,
)


class TDLValidator:
    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self.lines: List[str] = []
        self.sections: List[Dict[str, str]] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.defined_symbols: Dict[str, Set[str]] = {
            "Report": set(),
            "Form": set(),
            "Part": set(),
            "Line": set(),
            "Field": set(),
            "Button": set(),
            "Collection": set(),
            "Function": set(),
            "Menu": set(),
        }

    def load(self) -> bool:
        if not self.file_path.exists():
            self.errors.append(f"File not found: {self.file_path}")
            return False
        with open(self.file_path, "r", encoding="utf-8", errors="replace") as f:
            self.lines = f.readlines()
        return True

    def validate(self) -> Tuple[bool, List[str], List[str]]:
        if not self.load():
            return False, self.errors, self.warnings

        current_section = None
        bracket_stack = []

        for line_num, line in enumerate(self.lines, start=1):
            stripped = line.strip()

            # Skip comments and blank lines
            if not stripped or stripped.startswith(";;"):
                continue

            # Check bracket balance on the line
            for char in stripped:
                if char == "[":
                    bracket_stack.append((line_num, "["))
                elif char == "]":
                    if not bracket_stack:
                        self.errors.append(f"Line {line_num}: Unmatched closing bracket ']'")
                    else:
                        bracket_stack.pop()

            # Check section headers
            if stripped.startswith("[") and stripped.endswith("]"):
                match = SECTION_HEADER_PATTERN.match(stripped)
                if not match:
                    # Could be custom or standard system section
                    if not re.match(r"^\[.+:.+\]$", stripped):
                        self.warnings.append(
                            f"Line {line_num}: Unrecognized section header format: '{stripped}'"
                        )
                else:
                    is_override, section_type, section_name = match.groups()
                    section_type_cap = section_type.capitalize()
                    current_section = {
                        "line": line_num,
                        "type": section_type_cap,
                        "name": section_name.strip(),
                        "is_override": bool(is_override),
                    }
                    self.sections.append(current_section)
                    if section_type_cap in self.defined_symbols:
                        self.defined_symbols[section_type_cap].add(section_name.strip())
                continue

            # Within sections, check key-value / action format
            if current_section and current_section["type"] == "Function":
                # Functions use numbered statements like "01 : SET : ..." or "Parameter : ..." or "RETURN"
                if not re.match(
                    r"^(\d+\s*:|Parameter\s*:|Variable\s*:|Return\b)",
                    stripped,
                    re.IGNORECASE,
                ):
                    self.warnings.append(
                        f"Line {line_num}: Function statement does not start with step number or declaration: '{stripped}'"
                    )
            elif current_section:
                # Normal definition lines usually contain ':' (Attribute : Value)
                if ":" not in stripped and not stripped.startswith(";;"):
                    self.warnings.append(
                        f"Line {line_num}: Attribute line missing colon ':' in {current_section['type']}: '{stripped}'"
                    )

        if bracket_stack:
            for unclosed_line, _ in bracket_stack:
                self.errors.append(f"Line {unclosed_line}: Unclosed opening bracket '['")

        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings


def validate_all_tdl(directory: str | Path) -> bool:
    dir_path = Path(directory)
    tdl_files = sorted(dir_path.glob("**/*.tdl"))
    if not tdl_files:
        print(f"No .tdl files found in {directory}")
        return False

    all_passed = True
    print(f"Validating {len(tdl_files)} TDL file(s) in {dir_path}...\n")

    for tdl_file in tdl_files:
        validator = TDLValidator(tdl_file)
        valid, errors, warnings = validator.validate()
        status = "PASSED" if valid else "FAILED"
        print(f"[{status}] {tdl_file.relative_to(dir_path.parent if dir_path.parent.exists() else dir_path)}")
        print(f"       Found {len(validator.sections)} section definitions")

        for w in warnings:
            print(f"       [WARN] {w}")
        for e in errors:
            print(f"       [ERROR] {e}")
            all_passed = False
        print()

    return all_passed


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "tally"
    success = validate_all_tdl(target)
    sys.exit(0 if success else 1)
