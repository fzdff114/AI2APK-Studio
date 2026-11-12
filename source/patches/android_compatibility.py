#!/usr/bin/env python3
"""Android XML parser compatibility and Java project regression patch."""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: android_compatibility.py <project-root>")
root = Path(sys.argv[1])
if not (root / "app/src/main/java/com/ai2apk/studio/MainActivity.java").is_file():
    raise SystemExit("invalid AI2APK Studio source directory")

def edit(rel, old, new):
    p = root / rel
    s = p.read_text(encoding="utf-8")
    if new in s:
        return
    if old not in s:
        raise SystemExit("patch context not found: " + rel)
    p.write_text(s.replace(old, new, 1), encoding="utf-8")

xml = r'''package com.ai2apk.studio.core;

import org.xml.sax.InputSource;
import java.io.StringReader;
import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;

/** Portable XML parsing for Android platform providers. */
public final class XmlUtils {
    private XmlUtils() {}

    public static DocumentBuilder newDocumentBuilder() throws ParserConfigurationException {
        DocumentBuilderFactory f = DocumentBuilderFactory.newInstance();
        f.setNamespaceAware(true);
        f.setExpandEntityReferences(false);
        feature(f, XMLConstants.FEATURE_SECURE_PROCESSING, true);
        feature(f, "http://apache.org/xml/features/disallow-doctype-decl", true);
        feature(f, "http://xml.org/sax/features/external-general-entities", false);
        feature(f, "http://xml.org/sax/features/external-parameter-entities", false);
        feature(f, "http://apache.org/xml/features/nonvalidating/load-external-dtd", false);
        try { f.setXIncludeAware(false); }
        catch (UnsupportedOperationException | AbstractMethodError ignored) {}
        DocumentBuilder b = f.newDocumentBuilder();
        // Android XML providers vary; this resolver always prevents external reads.
        b.setEntityResolver((publicId, systemId) -> new InputSource(new StringReader("")));
        return b;
    }

    private static void feature(DocumentBuilderFactory f, String name, boolean value) {
        try { f.setFeature(name, value); }
        catch (ParserConfigurationException | IllegalArgumentException | UnsupportedOperationException ignored) {}
    }
}
'''
xml_file = root / "app/src/main/java/com/ai2apk/studio/core/XmlUtils.java"
xml_file.parent.mkdir(parents=True, exist_ok=True)
xml_file.write_text(xml, encoding="utf-8")

edit("app/src/main/java/com/ai2apk/studio/core/ProjectRepairEngine.java",
     "import javax.xml.parsers.DocumentBuilderFactory;\n", "")
edit("app/src/main/java/com/ai2apk/studio/core/ProjectRepairEngine.java",
'''        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        Document doc = factory.newDocumentBuilder().parse(manifest);''',
'''        Document doc = XmlUtils.newDocumentBuilder().parse(manifest);''')

edit("app/src/main/java/com/ai2apk/studio/core/SdkPlatformManager.java",
     "import javax.xml.parsers.DocumentBuilderFactory;\n", "")
edit("app/src/main/java/com/ai2apk/studio/core/SdkPlatformManager.java",
'''            DocumentBuilderFactory f = DocumentBuilderFactory.newInstance();
            f.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
            Document d = f.newDocumentBuilder().parse(in);''',
'''            Document d = XmlUtils.newDocumentBuilder().parse(in);''')

edit("app/src/main/java/com/ai2apk/studio/core/OnDeviceBuilder.java",
     "import javax.xml.parsers.DocumentBuilderFactory;\n", "")
edit("app/src/main/java/com/ai2apk/studio/core/OnDeviceBuilder.java",
'''            DocumentBuilderFactory f = DocumentBuilderFactory.newInstance(); f.setNamespaceAware(true);
            f.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
            org.w3c.dom.Document d = f.newDocumentBuilder().parse(manifest);''',
'''            org.w3c.dom.Document d = XmlUtils.newDocumentBuilder().parse(manifest);''')

edit("app/src/main/java/com/ai2apk/studio/MainActivity.java",
'''TextView buildNote = text("首版重点支持 Java 原生 Android 工程。Kotlin / Compose、AAR 传递依赖和复杂 Gradle 插件暂不支持。", 11, 0xFF667085, false);''',
'''TextView buildNote = text("支持 Java 原生 Android 工程，保留原始 .java 源码，不会强制转换语言。Kotlin / Compose、远程 Maven/AAR 依赖及复杂 Gradle 插件暂不支持。", 11, 0xFF667085, false);''')

edit("tools/smoke/run.sh",
'''  "$ROOT/app/src/main/java/com/ai2apk/studio/core/ProjectAnalyzer.java" \\
  "$ROOT/app/src/main/java/com/ai2apk/studio/core/ProjectRepairEngine.java" \\''',
'''  "$ROOT/app/src/main/java/com/ai2apk/studio/core/ProjectAnalyzer.java" \\
  "$ROOT/app/src/main/java/com/ai2apk/studio/core/XmlUtils.java" \\
  "$ROOT/app/src/main/java/com/ai2apk/studio/core/ProjectRepairEngine.java" \\''')

test_path = root / "tools/smoke/ProjectSmokeTest.java"
test = test_path.read_text(encoding="utf-8")
if "testExistingJavaProjectManifest(root);" not in test:
    test = test.replace(
'''            testLooseAiFiles(root);
            System.out.println("ALL SMOKE TESTS PASSED");''',
'''            testLooseAiFiles(root);
            testExistingJavaProjectManifest(root);
            System.out.println("ALL SMOKE TESTS PASSED");''', 1)
    method = r'''
    private static void testExistingJavaProjectManifest(File root) throws Exception {
        File project = new File(root, "existing-java-project");
        File javaDir = new File(project, "app/src/main/java/org/example/existing");
        require(javaDir.mkdirs(), "cannot create Java project source folder");
        String java = "package org.example.existing;\n" +
                "import android.app.Activity;\n" +
                "public class MainActivity extends Activity {}\n";
        Files.write(new File(javaDir, "MainActivity.java").toPath(), java.getBytes(StandardCharsets.UTF_8));
        String manifest = "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
                "<manifest xmlns:android=\"http://schemas.android.com/apk/res/android\" package=\"org.example.existing\">\n" +
                "  <application android:label=\"Existing Java App\">\n" +
                "    <activity android:name=\".MainActivity\" android:exported=\"true\">\n" +
                "      <intent-filter><action android:name=\"android.intent.action.MAIN\"/>" +
                "<category android:name=\"android.intent.category.LAUNCHER\"/></intent-filter>\n" +
                "    </activity>\n  </application>\n</manifest>\n";
        Files.write(new File(project, "app/src/main/AndroidManifest.xml").toPath(), manifest.getBytes(StandardCharsets.UTF_8));
        new ProjectRepairEngine().repair(project);
        ProjectAnalyzer.Summary summary = ProjectAnalyzer.analyze(project);
        require(summary.javaFiles == 1 && summary.hasManifest && summary.hasGradle,
                "existing Java project was not detected: " + summary);
        String repaired = new String(Files.readAllBytes(new File(project, "app/src/main/AndroidManifest.xml").toPath()), StandardCharsets.UTF_8);
        require(repaired.contains("Existing Java App") && repaired.contains(".MainActivity"),
                "existing Manifest details were not preserved: " + repaired);
        System.out.println("PASS: repair an existing Java/Gradle project with AndroidManifest.xml");
    }
'''
    marker = "    private static void require(boolean condition, String message) {"
    if marker not in test:
        raise SystemExit("smoke test method marker not found")
    test = test.replace(marker, method + "\n" + marker, 1)
    test_path.write_text(test, encoding="utf-8")

changelog = root / "CHANGELOG_CN.md"
history = changelog.read_text(encoding="utf-8")
if "## 1.0.1（兼容性修复）" not in history:
    history += """
## 1.0.1（兼容性修复）

- 修复部分 Android XML 解析器不支持 Apache Xerces 特性，导致已有 Java 工程在编译前中断的问题。
- 对 XML 解析采用可选安全特性与外部实体拦截。
- 增加已有 Java/Gradle 工程的 Manifest 回归测试。
- 不转换、不删除导入的 Java 源码。
"""
    changelog.write_text(history, encoding="utf-8")

print("Android XML compatibility and Java project regression patch applied.")
