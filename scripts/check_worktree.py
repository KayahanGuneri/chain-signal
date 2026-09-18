"""Check reviewable changes without modifying the real Git index."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GIT = ["git", "-c", f"safe.directory={ROOT.as_posix()}"]


def git(*args: str, input_bytes: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [*GIT, *args], cwd=ROOT, input=input_bytes, capture_output=True, check=False
    )


def checked(*args: str, input_bytes: bytes | None = None) -> bytes:
    result = git(*args, input_bytes=input_bytes)
    if result.returncode:
        raise RuntimeError(
            result.stderr.decode("utf-8", errors="replace")
            + result.stdout.decode("utf-8", errors="replace")
        )
    print("PASS: git " + " ".join(args))
    return result.stdout


def paths(output: bytes) -> list[str]:
    return [item.decode("utf-8") for item in output.split(b"\0") if item]


def main() -> None:
    index_before = checked("ls-files", "--stage", "-z")
    checked("diff", "--check")
    checked("diff", "--cached", "--check")
    changed = paths(checked("diff", "--name-only", "-z", "HEAD"))
    untracked = paths(checked("ls-files", "--others", "--exclude-standard", "-z"))
    existing = [path for path in set(changed + untracked) if (ROOT / path).is_file()]
    text_count = 0
    for path in existing:
        content = (ROOT / path).read_bytes()
        if Path(path).suffix.lower() == ".png":
            if not content.startswith(b"\x89PNG\r\n\x1a\n"):
                raise RuntimeError("Expected a PNG image: " + path)
            continue
        content.decode("utf-8", errors="strict")
        if content.startswith(b"\xef\xbb\xbf") or b"\r" in content:
            raise RuntimeError("Expected UTF-8 without BOM and LF: " + path)
        text_count += 1
    print(f"PASS: UTF-8 without BOM and LF for {text_count} changed/new text files")

    patch = checked("diff", "--binary", "--no-ext-diff")
    for path in untracked:
        addition = git("diff", "--no-index", "--binary", "--", "/dev/null", path)
        if addition.returncode not in (0, 1):
            raise RuntimeError(addition.stderr.decode("utf-8", errors="replace"))
        patch += addition.stdout
    if patch:
        # Validate remaining additions against the current index, including staged work.
        # --check never applies the patch or stages files.
        checked("apply", "--cached", "--check", "--whitespace=error-all", "-", input_bytes=patch)
    assert checked("ls-files", "--stage", "-z") == index_before, "Git index changed"
    print("PASS: real Git index unchanged")
    print(checked("status", "--short").decode("utf-8"))


if __name__ == "__main__":
    main()
