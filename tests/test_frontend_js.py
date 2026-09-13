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

    web = Path(__file__).resolve().parents[1] / "web"
    for filename in [
        "capital_os.html",
        "market_intelligence.html",
        "learning.html",
        "portfolio_health.html",
    ]:
        html = (web / filename).read_text(encoding="utf-8")
        scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, flags=re.S)
        inline_scripts = [s for s in scripts if s.strip()]
        assert inline_scripts, f"no inline JavaScript found in {filename}"

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
        assert result.returncode == 0, f"{filename}: {result.stderr}"
