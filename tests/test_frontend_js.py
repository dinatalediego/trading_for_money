from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import pytest


def test_capital_os_inline_javascript_parses():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not available")

    html = (Path(__file__).resolve().parents[1] / "web" / "capital_os.html").read_text(
        encoding="utf-8"
    )
    scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, flags=re.S)
    inline_scripts = [s for s in scripts if s.strip()]
    assert inline_scripts, "no inline JavaScript found"

    source = "\n".join(inline_scripts)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".js", encoding="utf-8", delete=False
    ) as tmp:
        tmp.write(source)
        path = tmp.name

    result = subprocess.run(
        [node, "--check", path],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
