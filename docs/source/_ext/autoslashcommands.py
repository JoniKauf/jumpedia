import importlib
import importlib.util
import os
import pkgutil
import sys
from pathlib import Path
from types import ModuleType

from docutils.parsers.rst import Directive
from sphinx.application import Sphinx


class AutoSlashCommands(Directive):
    required_arguments = 1
    has_content = False

    def run(self):
        # 1. Find <root>
        # autoslashcommands.py → .../docs/source/_ext → parents[3] = <root>
        root = Path(__file__).resolve().parents[3]

        # 2. Dotted module name (e.g. "src.discord_.cogs")
        dotted = self.arguments[0]

        # 3. Convert dotted import to a filesystem path
        rel_path = dotted.replace(".", os.path.sep)
        goal_dir = root / rel_path

        if not goal_dir.is_dir():
            raise RuntimeError(f"Directory '{goal_dir}' does not exist")

        # 4. Ensure <root> becomes importable
        root_str = str(root)
        if root_str not in sys.path:
            sys.path.insert(0, root_str)

        # 5. Import all modules from that directory
        modules: list[ModuleType] = []

        for info in pkgutil.iter_modules([goal_dir]):
            modname = info.name

            file_path = goal_dir / f"{modname}.py"

            # Fully qualified module name relative to <root>
            fqmn = f"{dotted}.{modname}"

            spec = importlib.util.spec_from_file_location(fqmn, file_path)
            if spec is None:
                raise RuntimeError(f"Cannot create spec for {file_path}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            modules.append(module)

        input(tuple(mod.__name__ for mod in modules))
        # Do something with the modules (render docs, build nodes, etc.)
        return []


def setup(app: Sphinx):
    app.add_directive("autoslashcommands", AutoSlashCommands)

    return {"version": "1.0", "parallel_read_safe": True, "parallel_write_safe": True}
