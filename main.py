import argparse
import ast
import logging
import os
import sys
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_argparse():
    """
    Sets up the argument parser for the command-line interface.

    Returns:
        argparse.ArgumentParser: The configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description="Removes unused import statements from Python code to reduce code clutter and improve readability."
    )
    parser.add_argument("filepath", help="Path to the Python file to be processed.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without modifying the file.",
    )
    parser.add_argument(
        "--aggressive",
        action="store_true",
        help="Aggressively remove imports, even if they might be used indirectly (use with caution).",
    )
    return parser

def find_unused_imports(filepath, aggressive=False):
    """
    Finds unused import statements in a Python file.

    Args:
        filepath (str): The path to the Python file.
        aggressive (bool):  Aggressively remove imports, even if they might be used indirectly.

    Returns:
        tuple: A tuple containing:
            - A list of tuples, where each tuple represents an unused import statement
              in the form (line_number, import_statement_string).
            - The parsed AST of the Python file.
    """
    try:
        with open(filepath, "r") as f:
            content = f.read()
    except FileNotFoundError:
        logging.error(f"File not found: {filepath}")
        return None, None
    except IOError as e:
        logging.error(f"Error reading file: {filepath} - {e}")
        return None, None

    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        logging.error(f"Syntax error in file: {filepath} - {e}")
        return None, None

    # Used roots: every Name id in the file. An attribute chain such as
    # os.path.join still bottoms out in a Name (os), so collecting Name
    # ids is enough; there is no need to rebuild dotted strings.
    used_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used_names.add(node.id)

    if not aggressive:
        # Safety net for indirect use: a binding mentioned inside a
        # string (a lazy import path, a __all__ style export list, a
        # getattr target) is kept. --aggressive is the opt-in to drop
        # that net, which is what the flag now actually changes.
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                for word in node.value.replace(".", " ").replace("'", " ").split():
                    used_names.add(word)

    lines = content.splitlines()
    unused_imports = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        bindings = []
        for alias in node.names:
            if alias.name == "*":
                continue  # a star import binds names this pass cannot list
            # "import os.path" binds os; "from m import x as y" binds y.
            bindings.append(alias.asname or alias.name.split(".")[0])
        if not bindings:
            continue
        # Invariant for the remover below: a line is only ever dropped
        # whole. If one alias on a shared line is still used, the line
        # stays, because deleting it would delete the used import too
        # (the old per-alias loop did exactly that and broke the file).
        if any(name in used_names for name in bindings):
            continue
        statement = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ""
        unused_imports.append((node.lineno, statement, getattr(node, "end_lineno", node.lineno) or node.lineno))
    return unused_imports, tree

def remove_unused_imports(filepath, unused_imports, dry_run=False):
    """
    Removes the specified unused import statements from the Python file.

    Args:
        filepath (str): The path to the Python file.
        unused_imports (list): A list of tuples, where each tuple represents an unused
            import statement in the form (line_number, import_statement_string).
        dry_run (bool): If True, perform a dry run without modifying the file.
    """
    if not unused_imports:
        logging.info("No unused imports found.")
        return

    try:
        with open(filepath, "r") as f:
            lines = f.readlines()
    except IOError as e:
        logging.error(f"Error reading file: {filepath} - {e}")
        return

    lines_to_remove = set()
    for line_number, _statement, end_line in unused_imports:
        # Parenthesized from-imports span several lines; the whole
        # span has to go or the file is left with a dangling bracket.
        lines_to_remove.update(range(line_number, end_line + 1))

    new_lines = [
        line for i, line in enumerate(lines, 1) if i not in lines_to_remove
    ]

    if dry_run:
        logging.info("Dry run: The following import statements would be removed:")
        for line_number, import_statement, _end in unused_imports:
            logging.info(f"Line {line_number}: {import_statement.strip()}")
    else:
        try:
            with open(filepath, "w") as f:
                f.writelines(new_lines)
            logging.info(f"Removed unused imports from {filepath}")
            for line_number, import_statement, _end in unused_imports:
                logging.info(f"Removed: Line {line_number}: {import_statement.strip()}")

        except IOError as e:
            logging.error(f"Error writing to file: {filepath} - {e}")


def main():
    """
    Main function to execute the unused import removal process.
    """
    parser = setup_argparse()
    args = parser.parse_args()

    filepath = args.filepath
    dry_run = args.dry_run
    aggressive = args.aggressive

    # Input Validation
    if not os.path.exists(filepath):
        logging.error(f"Error: File '{filepath}' does not exist.")
        sys.exit(1)

    if not filepath.endswith(".py"):
        logging.warning(f"Warning: File '{filepath}' does not have a '.py' extension. Proceeding anyway.")
    
    try:
        unused_imports, _ = find_unused_imports(filepath, aggressive)
        if unused_imports is None:
            # The file could not be read or parsed. Reporting success
            # here would claim a clean file that was never examined.
            sys.exit(1)
        remove_unused_imports(filepath, unused_imports, dry_run)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        logging.error(traceback.format_exc()) # Log the full traceback for debugging
        sys.exit(1)


if __name__ == "__main__":
    main()