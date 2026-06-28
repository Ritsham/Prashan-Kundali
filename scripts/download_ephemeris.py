import hashlib
import sys
from pathlib import Path
from urllib.request import urlopen


EPHEMERIS_FILES = {
    "sepl_18.se1": "https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/sepl_18.se1",
    "semo_18.se1": "https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/semo_18.se1",
    "seas_18.se1": "https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/seas_18.se1",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(name: str, url: str, target_dir: Path) -> dict:
    target = target_dir / name
    if target.exists() and target.stat().st_size > 0:
        return {"file": name, "status": "exists", "bytes": target.stat().st_size, "sha256": sha256(target)}

    with urlopen(url, timeout=60) as response:
        data = response.read()
    target.write_bytes(data)
    return {"file": name, "status": "downloaded", "bytes": len(data), "sha256": sha256(target)}


def main() -> int:
    target_dir = Path("ephemeris")
    target_dir.mkdir(exist_ok=True)

    print("Downloading Swiss Ephemeris files into ephemeris/")
    for name, url in EPHEMERIS_FILES.items():
        result = download_file(name, url, target_dir)
        print(f"{result['status']:10} {result['file']:12} {result['bytes']:>9} bytes  {result['sha256']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
