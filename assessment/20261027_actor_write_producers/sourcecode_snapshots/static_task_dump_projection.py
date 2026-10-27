"""Bounded AST-only projection of literal task prompts in recorded programs.

No original code, imports, calls, file operations, or comprehensions are
executed. Unknown leaves remain absent. This only recovers a literal prompt's
dataflow into JSON dump arguments; actual output bytes must be checked too.
"""
import ast
import re

UNKNOWN = object()


def project(command):
    results = []
    pattern = r"(?:python(?:3)?(?:\s+-)?\s*<<|cat\s*>\s*[^\s]+\s*<<)\s*['\"]?(?P<tag>[A-Za-z0-9_]+)['\"]?\s*\r?\n(?P<body>.*?)\r?\n(?P=tag)(?:\r?\n|$)"
    for match in re.finditer(pattern, command, re.S):
        try:
            tree = ast.parse(match['body'])
        except SyntaxError:
            continue
        bindings = {}
        budget = [20000]

        def value(node, local=None):
            budget[0] -= 1
            if budget[0] < 0:
                return UNKNOWN
            local = local or {}
            if isinstance(node, ast.Constant):
                return node.value
            if isinstance(node, ast.Name):
                return local.get(node.id, bindings.get(node.id, UNKNOWN))
            if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
                items = [value(n, local) for n in node.elts]
                return [n for n in items if n is not UNKNOWN]
            if isinstance(node, ast.Dict):
                result = {}
                for k, v in zip(node.keys, node.values):
                    if k is None:
                        extra = value(v, local)
                        if isinstance(extra, dict):
                            result.update(extra)
                    else:
                        k, v = value(k, local), value(v, local)
                        if isinstance(k, (str, int)) and v is not UNKNOWN:
                            result[k] = v
                return result
            if isinstance(node, ast.Subscript):
                container, key = value(node.value, local), value(node.slice, local)
                try:
                    if isinstance(container, (dict, list, tuple, str)) and isinstance(key, (str, int)):
                        return container[key]
                except (KeyError, IndexError, TypeError):
                    pass
                return UNKNOWN
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                a, b = value(node.left, local), value(node.right, local)
                return a + b if type(a) is type(b) and isinstance(a, (str, list, int, float)) else UNKNOWN
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                a, b = value(node.left, local), value(node.comparators[0], local)
                if a is UNKNOWN or b is UNKNOWN:
                    return UNKNOWN
                op = node.ops[0]
                if isinstance(op, ast.Eq):
                    return a == b
                if isinstance(op, ast.NotEq):
                    return a != b
                if isinstance(op, ast.In) and isinstance(b, (dict, list, tuple, str)):
                    return a in b
                if isinstance(op, ast.NotIn) and isinstance(b, (dict, list, tuple, str)):
                    return a not in b
                return UNKNOWN
            if isinstance(node, (ast.ListComp, ast.DictComp)):
                scopes = [dict(local)]
                if len(node.generators) > 3:
                    return UNKNOWN
                for generator in node.generators:
                    next_scopes = []
                    for scope in scopes:
                        iterable = value(generator.iter, scope)
                        if not isinstance(iterable, (dict, list, tuple, str)) or len(iterable) > 1000 or not isinstance(generator.target, ast.Name):
                            return UNKNOWN
                        for item in iterable:
                            nested = {**scope, generator.target.id: item}
                            conditions = [value(condition, nested) for condition in generator.ifs]
                            if any(condition is UNKNOWN for condition in conditions):
                                return UNKNOWN
                            if all(conditions):
                                next_scopes.append(nested)
                    scopes = next_scopes
                if isinstance(node, ast.ListComp):
                    items = [value(node.elt, scope) for scope in scopes]
                    return [item for item in items if item is not UNKNOWN]
                result = {}
                for scope in scopes:
                    k, v = value(node.key, scope), value(node.value, scope)
                    if isinstance(k, (str, int)) and v is not UNKNOWN:
                        result[k] = v
                return result
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'dict':
                result = {}
                if len(node.args) > 1:
                    return UNKNOWN
                if node.args:
                    base = value(node.args[0], local)
                    if not isinstance(base, dict):
                        return UNKNOWN
                    result.update(base)
                for keyword in node.keywords:
                    v = value(keyword.value, local)
                    if keyword.arg is not None and v is not UNKNOWN:
                        result[keyword.arg] = v
                return result
            return UNKNOWN

        def unconditional_statements(body):
            for statement in body:
                yield statement
                if isinstance(statement, ast.With) and all(
                    isinstance(item.context_expr, ast.Call) and
                    (isinstance(item.context_expr.func, ast.Name) and item.context_expr.func.id == 'open' or
                     isinstance(item.context_expr.func, ast.Attribute) and item.context_expr.func.attr == 'open')
                    for item in statement.items):
                    yield from unconditional_statements(statement.body)

        for statement in unconditional_statements(tree.body):
            if isinstance(statement, ast.Assign):
                v = value(statement.value)
                if v is not UNKNOWN:
                    for target in statement.targets:
                        if isinstance(target, ast.Name):
                            bindings[target.id] = v
            # Only top-level statements' actual dump expressions are witnesses;
            # a dead function definition or conditional body is not sufficient.
            if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
                call = statement.value
                if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) and call.func.value.id == 'json' and call.func.attr in {'dump', 'dumps'} and call.args:
                    result = value(call.args[0])
                    if result is not UNKNOWN:
                        results.append(result)
            # Common actual program: f.write(json.dumps(tasks, ...)). A direct
            # top-level write call is required, never an arbitrary AST walk.
            if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
                outer = statement.value
                if isinstance(outer.func, ast.Attribute) and outer.func.attr == 'write' and outer.args:
                    call = outer.args[0]
                    if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) and call.func.value.id == 'json' and call.func.attr == 'dumps' and call.args:
                        result = value(call.args[0])
                        if result is not UNKNOWN:
                            results.append(result)
    return results
