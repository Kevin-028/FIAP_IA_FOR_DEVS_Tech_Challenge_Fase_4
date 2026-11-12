"""Baixa o treino aberto do PhysioNet Challenge 2019 (um .psv por paciente)."""
from __future__ import annotations

import os
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(ROOT, "hospital_data", "fase4", "challenge-2019")
PREFIX = "challenge-2019/1.0.0/training/"
NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}


def list_keys() -> list[str]:
    keys = []
    token = None
    while True:
        query = f"list-type=2&prefix={urllib.parse.quote(PREFIX)}&max-keys=1000"
        if token:
            query += "&continuation-token=" + urllib.parse.quote(token, safe="")
        with urllib.request.urlopen(
            "https://physionet-open.s3.amazonaws.com/?" + query, timeout=60
        ) as response:
            tree = ET.parse(response)
        for node in tree.findall(".//s3:Contents/s3:Key", NS):
            if node.text and node.text.endswith(".psv"):
                keys.append(node.text)
        truncated = tree.find("s3:IsTruncated", NS)
        if truncated is None or truncated.text != "true":
            break
        nxt = tree.find("s3:NextContinuationToken", NS)
        token = nxt.text if nxt is not None else None
        if not token:
            break
    return keys


def _fetch(key: str) -> str:
    relative = key.split("challenge-2019/1.0.0/", 1)[1]
    path = os.path.join(DEST, relative.replace("/", os.sep))
    if os.path.isfile(path) and os.path.getsize(path) > 0:
        return "skip"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    url = "https://physionet-open.s3.amazonaws.com/" + urllib.parse.quote(key)
    urllib.request.urlretrieve(url, path)
    return "ok"


def main() -> None:
    keys = list_keys()
    print(f"{len(keys)} arquivos")
    done = 0
    with ThreadPoolExecutor(max_workers=24) as pool:
        futures = [pool.submit(_fetch, key) for key in keys]
        for future in as_completed(futures):
            future.result()
            done += 1
            if done % 500 == 0 or done == len(keys):
                print(f"{done}/{len(keys)}", flush=True)
    print("ok", DEST)


if __name__ == "__main__":
    main()
