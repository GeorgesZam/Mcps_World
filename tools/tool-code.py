# tool/tool-add.py

# Schéma pour spécifier la structure attendue des appels
function_schema = {
    "type": "object",
    "properties": {
        "code": {
            "type": "string",
            "description": "Code à exécuter"
        }
    },
    "required": ["code"]
}
def function_call(code: str) -> str:
    from io import StringIO
    import sys
    import ast

    try:
        old_stdout = sys.stdout
        redirected_output = sys.stdout = StringIO()

        safe_builtins = {
            'print': print,
            'len': len,
            'range': range,
            'enumerate': enumerate,
            'abs': abs,
            'min': min,
            'max': max,
            'sum': sum,
            'sorted': sorted,
            'list': list,
            'tuple': tuple,
            'dict': dict,
            'set': set,
        }

        # Dictionnaire global partagé
        globals_dict = {"__builtins__": safe_builtins}

        code_ast = ast.parse(code, mode='exec')
        last_expr = None
        if code_ast.body and isinstance(code_ast.body[-1], ast.Expr):
            last_expr = code_ast.body.pop().value
            code_body = compile(ast.Module(body=code_ast.body, type_ignores=[]), '<string>', 'exec')
            exec(code_body, globals_dict, globals_dict)
            # Eval de la dernière expression
            result = eval(compile(ast.Expression(last_expr), '<string>', 'eval'), globals_dict, globals_dict)
            if result is not None:
                print(result)
        else:
            exec(code, globals_dict, globals_dict)

        sys.stdout = old_stdout
        output = redirected_output.getvalue().strip()
        if not output:
            output = "Aucune sortie."
        return output

    except Exception as e:
        sys.stdout = old_stdout
        return f"Erreur lors de l'exécution du code : {str(e)}"
