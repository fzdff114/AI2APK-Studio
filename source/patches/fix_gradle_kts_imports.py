#!/usr/bin/env python3
"""Apply the Kotlin-DSL import fix required by Gradle's script compilation."""
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

required = ["URL(", "MessageDigest.getInstance", "ZipFile(aapt2Aar)"]
missing = [item for item in required if item not in source]
if missing:
    raise SystemExit("patch failed; missing expected Kotlin-DSL symbols: " + ", ".join(missing))

path.write_text(source, encoding="utf-8")
print("Patched Gradle Kotlin DSL java.* package references.")
