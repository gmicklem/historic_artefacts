#!/usr/bin/env python3
"""Export every public list of an InterMine mine (default: HumanMine).

Usage:
    python3 -I scripts/export_humanmine_public_lists.py BASE_URL OUTPUT_DIR

BASE_URL is the mine's service root, e.g. https://www.humanmine.org/humanmine/service
OUTPUT_DIR receives lists.json, lists.tsv, members/*.tsv, members/INDEX.tsv,
export.log. Read-only, sequential requests with a 0.3 s pause, one retry on a
transient error, aborts if the service refuses repeatedly. Stdlib only.
"""
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

PAUSE = 0.3
# Per list type: view paths (first is the class root used in the IN constraint).
VIEWS = {
    "Gene": ["Gene.primaryIdentifier", "Gene.symbol", "Gene.secondaryIdentifier", "Gene.organism.name"],
    "Protein": ["Protein.primaryAccession", "Protein.primaryIdentifier", "Protein.symbol",
                "Protein.name", "Protein.organism.name"],
    "SNP": ["SNP.primaryIdentifier", "SNP.secondaryIdentifier", "SNP.symbol", "SNP.name",
            "SNP.organism.name"],
}
DEFAULT_VIEW = ["{c}.primaryIdentifier", "{c}.symbol", "{c}.name"]

log_lines = []
refusals = 0


def log(msg):
    log_lines.append(msg)
    print(msg, flush=True)


def fetch(url, data=None):
    """GET/POST with one retry; abort after repeated refusals."""
    global refusals
    last = None
    for attempt in (1, 2):
        try:
            req = urllib.request.Request(url, data=data,
                                         headers={"User-Agent": "historic_artefacts-export/1.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                body = r.read().decode("utf-8")
            time.sleep(PAUSE)
            refusals = 0
            return body
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (403, 429) or e.code >= 500:
                refusals += 1
                if refusals >= 3:
                    log("ABORT: service refused repeatedly (HTTP %d) for %s" % (e.code, url))
                    sys.exit(2)
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
        time.sleep(2)
    raise RuntimeError("request failed twice: %s: %s" % (url, last))


def safe_name(name):
    # "/" and whitespace -> "_"; ":" -> "__" (a colon is not allowed in Windows file names)
    return re.sub(r"[/\s]", "_", name).replace(":", "__")


def one_line(s):
    return re.sub(r"\s+", " ", s or "").strip()


def main(base, out):
    base = base.rstrip("/")
    os.makedirs(os.path.join(out, "members"), exist_ok=True)

    for ep in ("version/release", "version/intermine"):
        url = base + "/" + ep
        log("GET %s -> %s" % (url, fetch(url).strip()))

    url = base + "/lists?format=json"
    raw = fetch(url)
    with open(os.path.join(out, "lists.json"), "w", encoding="utf-8") as f:
        f.write(raw)
    lists = json.loads(raw)["lists"]
    log("GET %s -> %d lists" % (url, len(lists)))

    with open(os.path.join(out, "lists.tsv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["name", "type", "size", "dateCreated", "title", "description"])
        for l in lists:
            w.writerow([one_line(l["name"]), l["type"], l["size"], l.get("dateCreated", ""),
                        one_line(l.get("title")), one_line(l.get("description"))])

    index = []
    mismatches = []
    seen = {}
    total = 0
    for l in lists:
        name, typ = l["name"], l["type"]
        fn = safe_name(name) + ".tsv"
        if fn in seen:
            raise RuntimeError("file name collision: %r and %r" % (name, seen[fn]))
        seen[fn] = name
        view = VIEWS.get(typ) or [p.format(c=typ) for p in DEFAULT_VIEW]
        esc = name.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
        # outer join on organism so a missing organism does not drop a row
        join = '<join path="%s.organism" style="OUTER"/>' % typ if any(
            p.endswith("organism.name") for p in view) else ""
        q = ('<query model="genomic" view="%s">%s<constraint path="%s" op="IN" value="%s"/></query>'
             % (" ".join(view), join, typ, esc))
        body = urllib.parse.urlencode({"query": q, "format": "tsv", "size": 100000}).encode()
        url = base + "/query/results"
        text = fetch(url, data=body)
        rows = [r for r in text.split("\n") if r.strip()]
        with open(os.path.join(out, "members", fn), "w", encoding="utf-8", newline="") as f:
            f.write("\t".join(view) + "\n")
            for r in rows:
                f.write(r + "\n")
        n = len(rows)
        total += n
        index.append((fn, name, n))
        log("POST %s list=%s type=%s -> %d rows (size in lists.json: %d)" % (url, name, typ, n, l["size"]))
        if n != l["size"]:
            mismatches.append((name, l["size"], n))

    with open(os.path.join(out, "members", "INDEX.tsv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["file", "list_name", "rows_exported"])
        w.writerows(index)

    log("SUMMARY lists=%d files=%d rows=%d sum_size=%d" %
        (len(lists), len(index), total, sum(l["size"] for l in lists)))
    if mismatches:
        for name, size, n in mismatches:
            log("MISMATCH %s: size=%d exported=%d" % (name, size, n))
    else:
        log("No mismatches between list size and exported row count.")
    with open(os.path.join(out, "export.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines) + "\n")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
