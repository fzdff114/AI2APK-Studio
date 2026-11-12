#!/usr/bin/env python3
"""Apply Android packaging fixes required for a clean Gradle Kotlin-DSL build."""
from pathlib import Path
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

required = [
    "URL(",
    "MessageDigest.getInstance",
    "ZipFile(aapt2Aar)",
    "META-INF/versions/9/OSGI-INF/MANIFEST.MF",
]
missing = [item for item in required if item not in source]
if missing:
    raise SystemExit("patch failed; missing expected symbols: " + ", ".join(missing))

path.write_text(source, encoding="utf-8")
print("Patched Gradle Kotlin DSL imports and duplicate Bouncy Castle metadata packaging.")
