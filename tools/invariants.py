"""Evaluates behaviour-contract invariants declared in probes.json.

A response diff can only say that a value CHANGED, and a changed value is
often intended: a pricing PR is supposed to change prices. What makes a change
provably wrong is a broken business rule -- "the total must equal taxable
amount + GST + shipping", "a coupon never raises the price". Those rules live
in probes.json as data, and this module checks them against captured
responses.

The rules are small expressions, evaluated by walking the AST against an
allowlist rather than with eval(): no imports, no attribute access on Python
objects (dotted names only read JSON fields), no dunder access, and bounded
iteration. The contract is repository data and is treated as untrusted input.

Python 3.8 compatible: requirements.txt is pinned to 3.8 and ci.yml matches.
"""
from __future__ import annotations

import ast
import operator

MAX_ITER = 1000
MONEY_TOLERANCE = 0.01


class InvariantError(Exception):
    """The rule could not be evaluated (missing field, bad status, bad syntax)."""


def approx(a, b, tol=MONEY_TOLERANCE):
    try:
        return abs(float(a) - float(b)) <= float(tol)
    except (TypeError, ValueError):
        raise InvariantError("approx() needs numbers, got {0!r} and {1!r}".format(a, b))


def _safe_round(value, ndigits=0):
    return round(value, int(ndigits))


_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}
_CMP_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}


class _Evaluator(object):
    def __init__(self, env, funcs):
        self.env = env
        self.funcs = funcs

    def eval(self, node):
        handler = getattr(self, "_" + type(node).__name__, None)
        if handler is None:
            raise InvariantError("unsupported syntax in rule: " + type(node).__name__)
        return handler(node)

    # -- literals and names ------------------------------------------------
    def _Expression(self, n):
        return self.eval(n.body)

    def _Constant(self, n):
        return n.value

    def _Num(self, n):  # pragma: no cover - pre-3.8 AST
        return n.n

    def _Str(self, n):  # pragma: no cover - pre-3.8 AST
        return n.s

    def _NameConstant(self, n):  # pragma: no cover - pre-3.8 AST
        return n.value

    def _Name(self, n):
        if n.id in self.env:
            return self.env[n.id]
        if n.id in self.funcs:
            return self.funcs[n.id]
        raise InvariantError("unknown name in rule: " + n.id)

    def _List(self, n):
        return [self.eval(e) for e in n.elts]

    def _Tuple(self, n):
        return tuple(self.eval(e) for e in n.elts)

    # -- field access: dotted names read JSON keys, never Python attributes --
    def _Attribute(self, n):
        base = self.eval(n.value)
        if isinstance(base, dict):
            if n.attr not in base:
                raise InvariantError("response has no field '{0}'".format(n.attr))
            return base[n.attr]
        raise InvariantError("cannot read .{0} from a {1}".format(n.attr, type(base).__name__))

    def _Subscript(self, n):
        base = self.eval(n.value)
        key_node = n.slice
        if isinstance(key_node, ast.Index):  # Python 3.8 wraps subscripts in Index
            key_node = key_node.value
        key = self.eval(key_node)
        if not isinstance(base, (dict, list, tuple)):
            raise InvariantError("cannot index a " + type(base).__name__)
        try:
            return base[key]
        except (KeyError, IndexError, TypeError):
            raise InvariantError("no element {0!r}".format(key))

    # -- operators ---------------------------------------------------------
    def _BinOp(self, n):
        op = _BIN_OPS.get(type(n.op))
        if op is None:
            raise InvariantError("operator not allowed: " + type(n.op).__name__)
        try:
            return op(self.eval(n.left), self.eval(n.right))
        except ZeroDivisionError:
            raise InvariantError("division by zero")
        except TypeError as exc:
            raise InvariantError("type error: {0}".format(exc))

    def _UnaryOp(self, n):
        value = self.eval(n.operand)
        if isinstance(n.op, ast.USub):
            return -value
        if isinstance(n.op, ast.UAdd):
            return +value
        if isinstance(n.op, ast.Not):
            return not value
        raise InvariantError("operator not allowed: " + type(n.op).__name__)

    def _BoolOp(self, n):
        if isinstance(n.op, ast.And):
            result = True
            for v in n.values:
                result = self.eval(v)
                if not result:
                    return result
            return result
        result = False
        for v in n.values:
            result = self.eval(v)
            if result:
                return result
        return result

    def _Compare(self, n):
        left = self.eval(n.left)
        for op_node, comp in zip(n.ops, n.comparators):
            op = _CMP_OPS.get(type(op_node))
            if op is None:
                raise InvariantError("comparison not allowed: " + type(op_node).__name__)
            right = self.eval(comp)
            try:
                if not op(left, right):
                    return False
            except TypeError as exc:
                raise InvariantError("type error: {0}".format(exc))
            left = right
        return True

    def _IfExp(self, n):
        return self.eval(n.body) if self.eval(n.test) else self.eval(n.orelse)

    def _Call(self, n):
        if not isinstance(n.func, ast.Name) or n.func.id not in self.funcs:
            raise InvariantError("only these functions may be called: " + ", ".join(sorted(self.funcs)))
        func = self.funcs[n.func.id]
        args = [self.eval(a) for a in n.args]
        kwargs = {}
        for kw in n.keywords:
            if kw.arg is None:
                raise InvariantError("**kwargs not allowed")
            kwargs[kw.arg] = self.eval(kw.value)
        return func(*args, **kwargs)

    # -- comprehensions: single generator, bounded ---------------------------
    def _comprehend(self, n):
        if len(n.generators) != 1:
            raise InvariantError("only one 'for' per comprehension")
        gen = n.generators[0]
        if not isinstance(gen.target, ast.Name):
            raise InvariantError("comprehension target must be a simple name")
        iterable = self.eval(gen.iter)
        if not isinstance(iterable, (list, tuple)):
            raise InvariantError("can only iterate over a list")
        if len(iterable) > MAX_ITER:
            raise InvariantError("list too long to evaluate")
        out = []
        for item in iterable:
            child = _Evaluator(dict(self.env), self.funcs)
            child.env[gen.target.id] = item
            if all(child.eval(cond) for cond in gen.ifs):
                out.append(child.eval(n.elt))
        return out

    def _GeneratorExp(self, n):
        return self._comprehend(n)

    def _ListComp(self, n):
        return self._comprehend(n)


def _parse(rule):
    try:
        return ast.parse(rule, mode="eval")
    except SyntaxError as exc:
        raise InvariantError("rule does not parse: {0}".format(exc.msg))


def _observed(tree, evaluator):
    """Best-effort 'what the two sides actually were', for the report."""
    body = tree.body
    try:
        if isinstance(body, ast.Call) and isinstance(body.func, ast.Name) and body.func.id == "approx" and len(body.args) >= 2:
            return "left = {0}, right = {1}".format(_fmt(evaluator.eval(body.args[0])), _fmt(evaluator.eval(body.args[1])))
        if isinstance(body, ast.Compare) and len(body.ops) == 1:
            return "left = {0}, right = {1}".format(_fmt(evaluator.eval(body.left)), _fmt(evaluator.eval(body.comparators[0])))
    except InvariantError:
        return None
    return None


def _fmt(value):
    if isinstance(value, float):
        return "{0:.2f}".format(value)
    return repr(value)


def evaluate_contract(contract, captured):
    """Evaluate every invariant in `contract` against `captured` probe records.

    Returns one result per (invariant, probe) pair:
      {"key", "id", "probe", "description", "status": holds|violated|error,
       "observed", "error"}
    """
    by_id = {p["id"]: p for p in captured}

    def probe(probe_id):
        record = by_id.get(probe_id)
        if record is None:
            raise InvariantError("rule references unknown probe '{0}'".format(probe_id))
        status = record.get("status")
        if not isinstance(status, int) or not 200 <= status < 300:
            raise InvariantError("probe '{0}' returned status {1}".format(probe_id, status))
        return record.get("body") or {}

    funcs = {
        "approx": approx,
        "abs": abs,
        "round": _safe_round,
        "min": min,
        "max": max,
        "sum": sum,
        "len": len,
        "probe": probe,
    }

    results = []
    for inv in contract.get("invariants", []):
        targets = inv.get("applies_to") or [inv.get("probe")]
        for probe_id in targets:
            key = "{0}@{1}".format(inv.get("id"), probe_id)
            result = {
                "key": key,
                "id": inv.get("id"),
                "probe": probe_id,
                "description": inv.get("description", ""),
                "rule": inv.get("rule", ""),
                "status": None,
                "observed": None,
                "error": None,
            }
            try:
                record = by_id.get(probe_id)
                if record is None:
                    raise InvariantError("probe '{0}' was not captured".format(probe_id))
                status = record.get("status")
                if not isinstance(status, int) or not 200 <= status < 300:
                    raise InvariantError("endpoint returned status {0}".format(status))
                env = {
                    "body": record.get("body") or {},
                    "request": record.get("request") or {},
                    "status": status,
                }
                tree = _parse(inv.get("rule", ""))
                evaluator = _Evaluator(env, funcs)
                holds = bool(evaluator.eval(tree))
                result["status"] = "holds" if holds else "violated"
                if not holds:
                    result["observed"] = _observed(tree, evaluator)
            except InvariantError as exc:
                result["status"] = "error"
                result["error"] = str(exc)
            results.append(result)
    return results
