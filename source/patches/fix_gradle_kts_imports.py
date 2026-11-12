#!/usr/bin/env python3
"""Apply Android build fixes and set the packaged application version."""
from pathlib import Path
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: fix_gradle_kts_imports.py <app/build.gradle.kts>")

path = Path(sys.argv[1])
source = path.read_text(encoding="utf-8")

imports = [
    "import java.net.URL",
    "import java.security.MessageDigest",
    "import java.util.zip.ZipFile",
]
for item in reversed(imports):
    if item not in source:
        source = item + "\n" + source

source = source.replace("java.net.URL(", "URL(")
source = source.replace("java.security.MessageDigest.", "MessageDigest.")
source = source.replace("java.util.zip.ZipFile(", "ZipFile(")

# These multi-release JAR metadata entries are duplicated by three Bouncy Castle
# modules and are not needed at Android runtime. Exclude only this exact metadata file.
needle = "        resources {\n"
exclude = '            excludes += "META-INF/versions/9/OSGI-INF/MANIFEST.MF"\n'
if exclude.strip() not in source:
    if needle not in source:
        raise SystemExit("patch failed; Android packaging.resources block was not found")
    source = source.replace(needle, needle + exclude, 1)

# The GitHub pre-release is 1.0.0, so align the Android package's own version
# rather than only changing the GitHub Release title.
def replace_or_insert(pattern: str, replacement: str, label: str) -> None:
    global source
    updated, count = re.subn(pattern, replacement, source, count=1, flags=re.MULTILINE)
    if count:
        source = updated
        return
    block = re.search(r"(?m)^(\s*)defaultConfig\s*\{", source)
    if not block:
        raise SystemExit(f"patch failed; defaultConfig block not found for {label}")
    indent = block.group(1) + "    "
    insertion = f"{indent}{label}\n"
    pos = block.end()
    source = source[:pos] + "\n" + insertion + source[pos:]

replace_or_insert(r"^(\s*versionCode\s*=\s*)\d+\s*$", r"\g<1>10000", "versionCode = 10000")
replace_or_insert(r'^(\s*versionName\s*=\s*)["\'][^"\']*["\']\s*$', r'\g<1>"1.0.0"', 'versionName = "1.0.0"')

required = [
    "URL(",
    "MessageDigest.getInstance",
    "ZipFile(aapt2Aar)",
    "META-INF/versions/9/OSGI-INF/MANIFEST.MF",
    "versionCode = 10000",
    'versionName = "1.0.0"',
]
missing = [item for item in required if item not in source]
if missing:
    raise SystemExit("patch failed; missing expected symbols: " + ", ".join(missing))

path.write_text(source, encoding="utf-8")
print("Patched Kotlin DSL imports, duplicate Bouncy Castle metadata, and app version 1.0.0.")
