#!/usr/bin/env python3
"""A small evaluator for the subset of TDL used by the GSTR-2B add-on.

Tally is Windows-only proprietary software, so a TDL function cannot be run on
this machine. The accounting behaviour of the importer is nevertheless worth
checking: which rate-wise purchase ledger a GST slab picks, that debits and
credits of a generated voucher add up to zero, that round off lands on the
configured ledger, and that a row which reads blank is skipped instead of
posted.

This module parses the real ``.tdl`` file and executes its functions against an
in-memory stand-in for Tally's object model. It supports exactly what the
add-on uses:

  statements   SET, SET VALUE, IF / ELSE / ENDIF, RETURN, NEW OBJECT,
               INSERT COLLECTION OBJECT, SET TARGET : .., SAVE TARGET,
               WALK COLLECTION / END WALK, MSGBOX
  expressions  literals, ##variables, $methods (incl. $Method:Type:Name),
               @@formulas, if/then/else, + - * /, = <> < > <= >=,
               AND / OR / NOT, and the $$ functions the add-on calls

It deliberately mirrors one Tally quirk: ``$$Function`` arguments are split on
":", which is why a method reference cannot be passed to it inline.

This is a test harness, not a TDL implementation: anything outside the subset
raises, so a future edit using an unsupported construct fails loudly instead of
being silently mis-simulated.
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

TOKEN_RE = re.compile(
    r"""
      (?P<space>\s+)
    | (?P<var>\#\#[A-Za-z_][A-Za-z0-9_]*)
    | (?P<func>\$\$[A-Za-z_][A-Za-z0-9_]*)
    | (?P<formula>@@[A-Za-z_][A-Za-z0-9_]*)
    | (?P<method>\$[A-Za-z_][A-Za-z0-9_]*)
    | (?P<number>\d+(?:\.\d+)?)
    | (?P<string>"[^"]*")
    | (?P<op><>|>=|<=|[+\-*/=<>])
    | (?P<colon>:)
    | (?P<lparen>\()
    | (?P<rparen>\))
    | (?P<ident>[A-Za-z_][A-Za-z0-9_]*)
    """,
    re.VERBOSE,
)

KEYWORDS = {"if", "then", "else", "and", "or", "not", "yes", "no"}

# Argument counts for the $$ functions the add-on uses. "Function" is variadic:
# Tally keeps consuming ":"-separated operands, which is the quirk reproduced
# in parse_call.
FUNCTION_ARITY = {
    "isempty": 1,
    "string": 1,
    "number": 1,
    "round": 2,
    "sysname": 1,
    "numitems": 1,
    "newline": 0,
    "date": 1,
}


class TDLError(Exception):
    pass


@dataclass
class Token:
    kind: str
    text: str


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    position = 0
    while position < len(source):
        match = TOKEN_RE.match(source, position)
        if match is None:
            raise TDLError(f"cannot tokenize {source[position:]!r} in {source!r}")
        position = match.end()
        kind = match.lastgroup
        assert kind is not None
        if kind == "space":
            continue
        text = match.group()
        if kind == "ident" and text.lower() in KEYWORDS:
            kind = text.lower()
        tokens.append(Token(kind, text))
    return tokens


# ---------------------------------------------------------------------------
# Expression tree
# ---------------------------------------------------------------------------


@dataclass
class Literal:
    value: Any


@dataclass
class Variable:
    name: str


@dataclass
class Formula:
    name: str


@dataclass
class Method:
    name: str
    object_type: str | None = None
    object_name: Any = None


@dataclass
class Call:
    name: str
    args: list[Any]


@dataclass
class Unary:
    op: str
    operand: Any


@dataclass
class Binary:
    op: str
    left: Any
    right: Any


@dataclass
class Conditional:
    condition: Any
    when_true: Any
    when_false: Any


class Parser:
    def __init__(self, tokens: list[Token], source: str) -> None:
        self.tokens = tokens
        self.source = source
        self.index = 0

    def peek(self, offset: int = 0) -> Token | None:
        position = self.index + offset
        return self.tokens[position] if position < len(self.tokens) else None

    def take(self, kind: str | None = None) -> Token:
        token = self.peek()
        if token is None:
            raise TDLError(f"unexpected end of expression in {self.source!r}")
        if kind is not None and token.kind != kind:
            raise TDLError(f"expected {kind} but found {token.text!r} in {self.source!r}")
        self.index += 1
        return token

    def parse(self) -> Any:
        node = self.parse_expression()
        if self.peek() is not None:
            raise TDLError(f"trailing {self.peek().text!r} in {self.source!r}")  # type: ignore[union-attr]
        return node

    def parse_expression(self) -> Any:
        token = self.peek()
        if token is not None and token.kind == "if":
            self.take("if")
            condition = self.parse_expression()
            self.take("then")
            when_true = self.parse_or()
            self.take("else")
            when_false = self.parse_expression()
            return Conditional(condition, when_true, when_false)
        return self.parse_or()

    def parse_or(self) -> Any:
        node = self.parse_and()
        while (token := self.peek()) is not None and token.kind == "or":
            self.take("or")
            node = Binary("or", node, self.parse_and())
        return node

    def parse_and(self) -> Any:
        node = self.parse_not()
        while (token := self.peek()) is not None and token.kind == "and":
            self.take("and")
            node = Binary("and", node, self.parse_not())
        return node

    def parse_not(self) -> Any:
        token = self.peek()
        if token is not None and token.kind == "not":
            self.take("not")
            return Unary("not", self.parse_not())
        return self.parse_comparison()

    def parse_comparison(self) -> Any:
        node = self.parse_additive()
        token = self.peek()
        if token is not None and token.kind == "op" and token.text in {"=", "<>", "<", ">", "<=", ">="}:
            op = self.take("op").text
            node = Binary(op, node, self.parse_additive())
        return node

    def parse_additive(self) -> Any:
        node = self.parse_multiplicative()
        while (token := self.peek()) is not None and token.kind == "op" and token.text in {"+", "-"}:
            op = self.take("op").text
            node = Binary(op, node, self.parse_multiplicative())
        return node

    def parse_multiplicative(self) -> Any:
        node = self.parse_unary()
        while (token := self.peek()) is not None and token.kind == "op" and token.text in {"*", "/"}:
            op = self.take("op").text
            node = Binary(op, node, self.parse_unary())
        return node

    def parse_unary(self) -> Any:
        token = self.peek()
        if token is not None and token.kind == "op" and token.text == "-":
            self.take("op")
            return Unary("-", self.parse_unary())
        return self.parse_primary()

    def parse_primary(self) -> Any:
        token = self.take()
        if token.kind == "number":
            text = token.text
            return Literal(float(text) if "." in text else int(text))
        if token.kind == "string":
            return Literal(token.text[1:-1])
        if token.kind in {"yes", "no"}:
            return Literal(token.kind == "yes")
        if token.kind == "var":
            return Variable(token.text[2:])
        if token.kind == "formula":
            return Formula(token.text[2:])
        if token.kind == "lparen":
            node = self.parse_expression()
            self.take("rparen")
            return node
        if token.kind == "method":
            return self.parse_method(token.text[1:])
        if token.kind == "func":
            return self.parse_call(token.text[2:])
        if token.kind == "ident":
            return Literal(token.text)
        raise TDLError(f"unexpected {token.text!r} in {self.source!r}")

    def parse_method(self, name: str) -> Method:
        following = self.peek()
        after = self.peek(1)
        if following is not None and following.kind == "colon" and after is not None and after.kind == "ident":
            self.take("colon")
            object_type = self.take("ident").text
            object_name = None
            if (nxt := self.peek()) is not None and nxt.kind == "colon":
                self.take("colon")
                object_name = self.parse_unary()
            return Method(name, object_type, object_name)
        return Method(name)

    def parse_call(self, name: str) -> Call:
        args: list[Any] = []
        if name.lower() == "function":
            while (token := self.peek()) is not None and token.kind == "colon":
                self.take("colon")
                args.append(self.parse_unary())
            if not args:
                raise TDLError(f"$$Function without a target in {self.source!r}")
            return Call("function", args)

        arity = FUNCTION_ARITY.get(name.lower())
        if arity is None:
            raise TDLError(f"unsupported $${name} in {self.source!r}")
        for _ in range(arity):
            self.take("colon")
            args.append(self.parse_unary())
        return Call(name.lower(), args)


def parse_expression(source: str) -> Any:
    return Parser(tokenize(source), source).parse()


# ---------------------------------------------------------------------------
# Tally stand-ins
# ---------------------------------------------------------------------------


@dataclass
class TallyObject:
    """A Tally object under construction (a voucher, ledger entry or ledger)."""

    kind: str
    values: dict[str, Any] = field(default_factory=dict)
    children: dict[str, list["TallyObject"]] = field(default_factory=dict)
    parent: "TallyObject | None" = None


@dataclass
class Company:
    config: dict[str, Any] = field(default_factory=dict)
    ledgers: dict[str, dict[str, Any]] = field(default_factory=dict)
    vouchers: list[TallyObject] = field(default_factory=list)
    messages: list[tuple[str, str]] = field(default_factory=list)

    def ledger(self, name: str) -> dict[str, Any] | None:
        return self.ledgers.get(str(name).lower())

    def add_ledger(self, name: str, **attributes: Any) -> None:
        self.ledgers[str(name).lower()] = {"Name": name, **attributes}


@dataclass
class Function:
    name: str
    parameters: list[tuple[str, str]]
    variables: list[tuple[str, str]]
    returns: str | None
    steps: list[tuple[int, str]]


def is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, bool):
        return value is False
    if isinstance(value, (int, float)):
        return value == 0
    if isinstance(value, str):
        return value.strip() == ""
    return False


def to_number(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return float(str(value).replace(",", ""))


def to_string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, datetime.date):
        return value.strftime("%d-%b-%Y").lstrip("0")
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value)


def tally_round(value: float, base: float) -> float:
    if base == 0:
        return value
    quotient = abs(value) / base
    rounded = int(quotient + 0.5) * base
    return rounded if value >= 0 else -rounded


class Interpreter:
    """Executes the parsed functions of a TDL file against a mock company."""

    def __init__(self, path: Path, company: Company) -> None:
        self.company = company
        self.functions: dict[str, Function] = {}
        self.formulas: dict[str, Any] = {}
        self.collections: dict[str, list[dict[str, Any]]] = {}
        self._load(path)

    # -- loading ---------------------------------------------------------

    def _load(self, path: Path) -> None:
        from tdl_lint import parse as parse_tdl, Report

        report = Report()
        _definitions, order = parse_tdl(path, report)
        if report.errors:
            raise TDLError("\n".join(report.errors))

        for definition in order:
            kind = definition.kind.lower()
            if kind == "system" and definition.name.lower() == "formula":
                for _line_no, body in definition.body:
                    name, _sep, expression = body.partition(":")
                    self.formulas[name.strip().lower()] = parse_expression(expression.strip())
            elif kind == "function":
                self.functions[definition.name.strip().lower()] = self._build_function(definition)

    @staticmethod
    def _build_function(definition: Any) -> Function:
        parameters: list[tuple[str, str]] = []
        variables: list[tuple[str, str]] = []
        returns: str | None = None
        steps: list[tuple[int, str]] = []

        for _line_no, body in definition.body:
            head, _sep, rest = body.partition(":")
            head = head.strip().lower()
            if head in {"parameter", "variable"}:
                name, _sep2, var_type = rest.partition(":")
                entry = (name.strip(), var_type.strip())
                (parameters if head == "parameter" else variables).append(entry)
            elif head == "returns":
                returns = rest.strip()
            else:
                match = re.match(r"^(\d+)\s*:\s*(.*)$", body)
                if match is None:
                    raise TDLError(f"unparsable function line: {body!r}")
                steps.append((int(match.group(1)), match.group(2).strip()))

        return Function(definition.name.strip(), parameters, variables, returns, steps)

    # -- evaluation ------------------------------------------------------

    def evaluate(self, node: Any, scope: dict[str, Any], row: dict[str, Any] | None) -> Any:
        if isinstance(node, Literal):
            return node.value
        if isinstance(node, Variable):
            name = node.name.lower()
            if name == "svcurrentcompany":
                return "Mock Company"
            if name not in scope:
                raise TDLError(f"undeclared variable ##{node.name}")
            return scope[name]
        if isinstance(node, Formula):
            formula = self.formulas.get(node.name.lower())
            if formula is None:
                raise TDLError(f"unknown formula @@{node.name}")
            return self.evaluate(formula, scope, row)
        if isinstance(node, Method):
            return self.evaluate_method(node, scope, row)
        if isinstance(node, Call):
            return self.evaluate_call(node, scope, row)
        if isinstance(node, Unary):
            if node.op == "not":
                return not self.truth(self.evaluate(node.operand, scope, row))
            return -to_number(self.evaluate(node.operand, scope, row))
        if isinstance(node, Conditional):
            branch = node.when_true if self.truth(self.evaluate(node.condition, scope, row)) else node.when_false
            return self.evaluate(branch, scope, row)
        if isinstance(node, Binary):
            return self.evaluate_binary(node, scope, row)
        raise TDLError(f"cannot evaluate {node!r}")

    def evaluate_method(self, node: Method, scope: dict[str, Any], row: dict[str, Any] | None) -> Any:
        if node.object_type is None:
            if row is None:
                raise TDLError(f"${node.name} used without a row object")
            return row.get(node.name)

        object_type = node.object_type.lower()
        if object_type == "company":
            return self.company.config.get(node.name)
        if object_type == "ledger":
            ledger_name = self.evaluate(node.object_name, scope, row)
            ledger = self.company.ledger(ledger_name)
            if ledger is None:
                return ""
            return ledger.get(node.name, "")
        raise TDLError(f"unsupported object type {node.object_type!r}")

    def evaluate_call(self, node: Call, scope: dict[str, Any], row: dict[str, Any] | None) -> Any:
        if node.name == "function":
            target = self.evaluate(node.args[0], scope, row)
            arguments = [self.evaluate(argument, scope, row) for argument in node.args[1:]]
            return self.call(str(target), arguments, row)

        values = [self.evaluate(argument, scope, row) for argument in node.args]
        if node.name == "isempty":
            return is_empty(values[0])
        if node.name == "string":
            return to_string(values[0])
        if node.name == "number":
            return to_number(values[0])
        if node.name == "round":
            return tally_round(to_number(values[0]), to_number(values[1]))
        if node.name == "sysname":
            return str(values[0])
        if node.name == "newline":
            return "\n"
        if node.name == "numitems":
            return len(self.collections.get(str(values[0]).lower(), []))
        if node.name == "date":
            return values[0]
        raise TDLError(f"unsupported $${node.name}")

    def evaluate_binary(self, node: Binary, scope: dict[str, Any], row: dict[str, Any] | None) -> Any:
        if node.op == "and":
            return self.truth(self.evaluate(node.left, scope, row)) and self.truth(
                self.evaluate(node.right, scope, row)
            )
        if node.op == "or":
            return self.truth(self.evaluate(node.left, scope, row)) or self.truth(
                self.evaluate(node.right, scope, row)
            )

        left = self.evaluate(node.left, scope, row)
        right = self.evaluate(node.right, scope, row)

        if node.op == "+":
            if isinstance(left, str) or isinstance(right, str):
                return to_string(left) + to_string(right)
            return to_number(left) + to_number(right)
        if node.op in {"-", "*", "/"}:
            left_number, right_number = to_number(left), to_number(right)
            if node.op == "-":
                return left_number - right_number
            if node.op == "*":
                return left_number * right_number
            return left_number / right_number if right_number else 0.0

        if isinstance(left, str) or isinstance(right, str):
            if node.op == "=":
                return to_string(left).lower() == to_string(right).lower()
            if node.op == "<>":
                return to_string(left).lower() != to_string(right).lower()

        if isinstance(left, datetime.date) or isinstance(right, datetime.date):
            comparable_left, comparable_right = left, right
        else:
            comparable_left, comparable_right = to_number(left), to_number(right)

        if node.op == "=":
            return comparable_left == comparable_right
        if node.op == "<>":
            return comparable_left != comparable_right
        if node.op == "<":
            return comparable_left < comparable_right
        if node.op == ">":
            return comparable_left > comparable_right
        if node.op == "<=":
            return comparable_left <= comparable_right
        if node.op == ">=":
            return comparable_left >= comparable_right
        raise TDLError(f"unsupported operator {node.op!r}")

    @staticmethod
    def truth(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"yes", "true"}
        if value is None:
            return False
        return bool(to_number(value))

    # -- execution -------------------------------------------------------

    def call(self, name: str, arguments: list[Any], row: dict[str, Any] | None = None) -> Any:
        function = self.functions.get(name.strip().lower())
        if function is None:
            raise TDLError(f"unknown function {name!r}")
        if len(arguments) != len(function.parameters):
            raise TDLError(
                f"{function.name} expects {len(function.parameters)} argument(s), got {len(arguments)}"
            )

        scope: dict[str, Any] = {}
        for (parameter, _type), value in zip(function.parameters, arguments):
            scope[parameter.lower()] = value
        for variable, var_type in function.variables:
            scope[variable.lower()] = "" if var_type.lower() == "string" else (
                0 if var_type.lower() in {"number", "amount"} else (False if var_type.lower() == "logical" else None)
            )

        return self._run(function, scope, row)

    def _run(self, function: Function, scope: dict[str, Any], row: dict[str, Any] | None) -> Any:
        target: TallyObject | None = None
        index = 0
        # Each IF pushes (branch_taken, currently_executing).
        conditions: list[tuple[bool, bool]] = []
        walk_stack: list[tuple[int, list[dict[str, Any]], int]] = []
        current_row = row

        def executing() -> bool:
            return all(active for _taken, active in conditions)

        while index < len(function.steps):
            _number, statement = function.steps[index]
            index += 1
            verb, _sep, rest = statement.partition(":")
            verb = verb.strip().lower()
            rest = rest.strip()

            if verb == "if":
                if not executing():
                    conditions.append((True, False))
                    continue
                taken = self.truth(self.evaluate(parse_expression(rest), scope, current_row))
                conditions.append((taken, taken))
                continue
            if verb == "else":
                if not conditions:
                    raise TDLError("ELSE without IF")
                taken, _active = conditions[-1]
                outer = all(active for _t, active in conditions[:-1])
                conditions[-1] = (taken, outer and not taken)
                continue
            if verb == "endif":
                conditions.pop()
                continue

            if verb == "walk collection":
                rows = self.collections.get(rest.lower(), [])
                if not executing() or not rows:
                    depth = 0
                    while index < len(function.steps):
                        next_verb = function.steps[index][1].partition(":")[0].strip().lower()
                        index += 1
                        if next_verb == "walk collection":
                            depth += 1
                        elif next_verb == "end walk":
                            if depth == 0:
                                break
                            depth -= 1
                    continue
                walk_stack.append((index, rows, 0))
                current_row = rows[0]
                continue
            if verb == "end walk":
                start, rows, position = walk_stack.pop()
                position += 1
                if position < len(rows):
                    walk_stack.append((start, rows, position))
                    current_row = rows[position]
                    index = start
                else:
                    current_row = row
                continue

            if not executing():
                continue

            if verb == "set":
                name, _sep2, expression = rest.partition(":")
                name = name.strip().lower()
                if name not in scope:
                    raise TDLError(f"{function.name}: assignment to undeclared {name!r}")
                value = self.evaluate(parse_expression(expression.strip()), scope, current_row)
                declared = dict((variable.lower(), kind.lower()) for variable, kind in function.variables)
                kind = declared.get(name, "")
                if kind in {"number", "amount"}:
                    value = to_number(value)
                elif kind == "string":
                    value = to_string(value)
                elif kind == "logical":
                    value = self.truth(value)
                scope[name] = value
                continue

            if verb == "new object":
                target = TallyObject(kind=rest)
                continue
            if verb == "insert collection object":
                if target is None:
                    raise TDLError("INSERT COLLECTION OBJECT without a target")
                child = TallyObject(kind=rest, parent=target)
                target.children.setdefault(rest, []).append(child)
                target = child
                continue
            if verb == "set value":
                if target is None:
                    raise TDLError("SET VALUE without a target")
                name, _sep2, expression = rest.partition(":")
                target.values[name.strip()] = self.evaluate(
                    parse_expression(expression.strip()), scope, current_row
                )
                continue
            if verb == "set target":
                if rest != "..":
                    raise TDLError(f"unsupported SET TARGET : {rest}")
                if target is None or target.parent is None:
                    raise TDLError("SET TARGET : .. above the top object")
                target = target.parent
                continue
            if verb == "save target":
                if target is None:
                    raise TDLError("SAVE TARGET without a target")
                self._save(target)
                continue

            if verb == "msgbox":
                title, _sep2, body = rest.partition(":")
                self.company.messages.append(
                    (
                        to_string(self.evaluate(parse_expression(title.strip()), scope, current_row)),
                        to_string(self.evaluate(parse_expression(body.strip()), scope, current_row)),
                    )
                )
                continue

            if verb == "return":
                if not rest:
                    return None
                return self.evaluate(parse_expression(rest), scope, current_row)

            raise TDLError(f"unsupported statement {statement!r}")

        return None

    def _save(self, target: TallyObject) -> None:
        root = target
        while root.parent is not None:
            root = root.parent
        if root.kind.lower() == "voucher":
            self.company.vouchers.append(root)
        elif root.kind.lower() == "ledger":
            self.company.add_ledger(
                str(root.values.get("Name", "")),
                Parent=root.values.get("Parent", ""),
                IsBillWiseOn=root.values.get("IsBillWiseOn", False),
            )
        else:
            raise TDLError(f"cannot save a {root.kind!r} object")


def ledger_entries(voucher: TallyObject) -> list[dict[str, Any]]:
    return [entry.values | {"_children": entry.children} for entry in voucher.children.get("AllLedgerEntries", [])]


def voucher_balance(voucher: TallyObject) -> float:
    return round(sum(to_number(entry["Amount"]) for entry in ledger_entries(voucher)), 2)


def make_interpreter(path: Path, company: Company) -> Interpreter:
    return Interpreter(path, company)


Builder = Callable[[], Company]
