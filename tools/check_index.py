#!/usr/bin/env python3
"""يتحقق من index.json مقابل ملفات pdf/ .

الاستخدام:
    python tools/check_index.py          # فحص فقط
    python tools/check_index.py --fix    # يضبط حقل "available" حسب وجود الملف فعلاً
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.json"
PDF_DIR = ROOT / "pdf"
WARN_MB = 50    # GitHub يحذّر فوق 50MB
MAX_MB = 100    # GitHub يرفض فوق 100MB


def main() -> int:
    fix = "--fix" in sys.argv
    data = json.loads(INDEX.read_text(encoding="utf-8"))

    errors, warnings, changes = [], [], []
    ids, files = set(), set()
    available_count = 0
    total = 0

    for cat in data.get("categories", []):
        for law in cat.get("laws", []):
            total += 1
            for key in ("id", "title", "file"):
                if not law.get(key):
                    errors.append(f"قانون بدون الحقل '{key}': {law}")
            lid, f = law.get("id"), law.get("file", "")

            if lid in ids:
                errors.append(f"id مكرر: {lid}")
            ids.add(lid)
            if f in files:
                errors.append(f"اسم ملف مكرر: {f}")
            files.add(f)

            if not f.lower().endswith(".pdf"):
                errors.append(f"[{lid}] الملف يجب أن ينتهي بـ .pdf: {f}")
            if " " in f:
                warnings.append(f"[{lid}] تجنّب المسافات في اسم الملف: {f}")

            path = PDF_DIR / f
            exists = path.is_file()
            declared = law.get("available", True)

            if exists:
                size_mb = path.stat().st_size / 1024 / 1024
                if size_mb > MAX_MB:
                    errors.append(f"[{lid}] الملف أكبر من {MAX_MB}MB (يرفضه GitHub): {size_mb:.0f}MB")
                elif size_mb > WARN_MB:
                    warnings.append(f"[{lid}] الملف كبير ({size_mb:.0f}MB) وسيبطئ التنزيل")

            if declared and not exists:
                if fix:
                    law["available"] = False
                    changes.append(f"{lid}: available → false (الملف غير موجود)")
                else:
                    errors.append(f"[{lid}] available=true لكن الملف غير موجود في pdf/: {f}")
            elif not declared and exists:
                if fix:
                    law["available"] = True
                    changes.append(f"{lid}: available → true (الملف موجود)")
                else:
                    warnings.append(f"[{lid}] الملف موجود لكن available=false (استخدم --fix)")

            if law.get("available", True):
                available_count += 1

    for pdf in sorted(PDF_DIR.glob("*.pdf")):
        if pdf.name not in files:
            warnings.append(f"ملف غير مذكور في الفهرس: {pdf.name}")

    if fix and changes:
        INDEX.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    print(f"القوانين: {total} | متاحة: {available_count} | قريبًا: {total - available_count}")
    for c in changes:
        print("  ✎", c)
    for w in warnings:
        print("  ⚠", w)
    for e in errors:
        print("  ✖", e)
    if errors:
        print(f"\nفشل الفحص: {len(errors)} خطأ")
        return 1
    print("\nالفحص ناجح ✔")
    return 0


if __name__ == "__main__":
    sys.exit(main())
