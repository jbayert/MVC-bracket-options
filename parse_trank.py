"""Parse barttorvik T-Rank HTML files into CSV."""
import re
import csv
import os

DATA_DIR = "T-rank data"
OUT_FILE = "data/trank_mvc.csv"

COLUMNS = ["year", "trank", "team", "conf", "games", "record",
           "adj_oe", "adj_de", "adj_em", "barthag",
           "efg_pct", "efg_d_pct", "tor", "tord",
           "orb", "drb", "ftr", "ftrd",
           "two_p_pct", "two_p_d_pct", "three_p_pct", "three_p_d_pct",
           "three_pr", "three_prd", "adj_t", "wab", "seed", "ncaa_result"]

def strip_tags(s):
    return re.sub(r"<[^>]+>", " ", s).strip()

def parse_num(s):
    s = s.strip().replace(" ", "")
    try:
        return float(s)
    except ValueError:
        return s if s else None

def parse_file(path, year):
    with open(path, encoding="utf-8") as f:
        content = f.read()

    rows = re.findall(
        r'<tr[^>]*class="seedrow[^"]*"[^>]*>(.*?)</tr>',
        content, re.DOTALL
    )

    records = []
    for row in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        vals = [strip_tags(c) for c in cells]

        # Extract team name and optional seed/NCAA result from cell 1
        team_cell = cells[1] if len(cells) > 1 else ""
        team_match = re.search(r'team\.php[^>]+>([^<]+)', team_cell)
        team = team_match.group(1).strip() if team_match else vals[1].split()[0]

        seed_match = re.search(r'(\d+)\s+seed', team_cell)
        seed = int(seed_match.group(1)) if seed_match else None

        ncaa_match = re.search(r'<span[^>]*>([^<]+)</span>', team_cell)
        ncaa_result = ncaa_match.group(1).strip() if ncaa_match else None

        # vals layout: [rank, team, conf, games, record, adjoe, adjde, barthag,
        #               efg, efgd, tor, tord, orb, drb, ftr, ftrd,
        #               2p, 2pd, 3p, 3pd, 3pr, 3prd, adjt, wab]
        # Each stat cell has "value  rank" — take just the first token
        def first(v):
            parts = v.split()
            return parts[0] if parts else None

        try:
            adj_oe = parse_num(first(vals[5]))
            adj_de = parse_num(first(vals[6]))
            adj_em = round(adj_oe - adj_de, 2) if isinstance(adj_oe, float) and isinstance(adj_de, float) else None

            records.append({
                "year": year,
                "trank": parse_num(vals[0]),
                "team": team,
                "conf": first(vals[2]),
                "games": parse_num(vals[3]),
                "record": first(vals[4]),
                "adj_oe": adj_oe,
                "adj_de": adj_de,
                "adj_em": adj_em,
                "barthag": parse_num(first(vals[7])),
                "efg_pct": parse_num(first(vals[8])),
                "efg_d_pct": parse_num(first(vals[9])),
                "tor": parse_num(first(vals[10])),
                "tord": parse_num(first(vals[11])),
                "orb": parse_num(first(vals[12])),
                "drb": parse_num(first(vals[13])),
                "ftr": parse_num(first(vals[14])),
                "ftrd": parse_num(first(vals[15])),
                "two_p_pct": parse_num(first(vals[16])),
                "two_p_d_pct": parse_num(first(vals[17])),
                "three_p_pct": parse_num(first(vals[18])),
                "three_p_d_pct": parse_num(first(vals[19])),
                "three_pr": parse_num(first(vals[20])),
                "three_prd": parse_num(first(vals[21])),
                "adj_t": parse_num(first(vals[22])),
                "wab": parse_num(first(vals[23])) if len(vals) > 23 else None,
                "seed": seed,
                "ncaa_result": ncaa_result,
            })
        except (IndexError, TypeError):
            print(f"  WARNING: skipped row in {year}: {vals[:4]}")

    return records

def main():
    all_records = []
    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.endswith(".htm"):
            continue
        year = int(fname.replace(".htm", ""))
        if year == 2020:
            continue
        path = os.path.join(DATA_DIR, fname)
        rows = parse_file(path, year)
        print(f"{year}: {len(rows)} teams")
        all_records.extend(rows)

    os.makedirs("data", exist_ok=True)
    with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(all_records)

    print(f"\nWrote {len(all_records)} rows to {OUT_FILE}")

if __name__ == "__main__":
    main()
