"""Report unsupported Node and npm versions before installing or starting the web app."""

import shutil
import subprocess
import sys


def version(command: str) -> str | None:
    if shutil.which(command) is None:
        return None
    result = subprocess.run(
        [command, "--version"], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


node = version("node")
npm = version("npm")
try:
    supported = (
        node is not None
        and npm is not None
        and int(node.lstrip("v").split(".")[0]) >= 22
        and int(npm.split(".")[0]) >= 10
    )
except ValueError:
    supported = False

if not supported:
    print(
        f"BottleIQ requires Node 22+ and npm 10+ (found Node {node or 'missing'}, npm {npm or 'missing'}). "
        "Install Node 22 or select it with 'nvm use --delete-prefix 22', then retry.",
        file=sys.stderr,
    )
    raise SystemExit(1)
