import argparse
import json
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


def fetch(url, timeout=20):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.text


def normalize_space(s):
    return re.sub(r"\s+", " ", s).strip()


def scrape_kmt(start=0, max_pages=50, delay=0.5, base="https://kmt.vander-lingen.nl/data/reaction/doi/10.1021/jacsau.4c01276/start/"):
    records = []
    consecutive_empty = 0
    for i in range(max_pages):
        page_url = urljoin(base, str(start))
        html = fetch(page_url)
        soup = BeautifulSoup(html, "html.parser")
        anchors = [a for a in soup.find_all("a") if a.get_text(strip=True).lower() == "details"]
        if not anchors:
            consecutive_empty += 1
            if consecutive_empty >= 2:
                break
        else:
            consecutive_empty = 0
        for a in anchors:
            href = a.get("href") or ""
            row = a.find_parent(["tr", "div", "li", "article"]) or a.parent
            text = normalize_space(row.get_text(" ", strip=True)) if row else ""
            link = urljoin(page_url, href) if href else ""
            if not link and row:
                candidate = row.find("a", href=True)
                if candidate:
                    link = urljoin(page_url, candidate.get("href"))
            records.append({"text": text, "details_url": link, "page_url": page_url})
        if not records:
            full_text = normalize_space(soup.get_text(" ", strip=True))
            parts = [p.strip() for p in re.split(r"\bDetails\b", full_text) if p.strip()]
            for p in parts:
                snippet = p[-200:]
                records.append({"text": snippet, "details_url": "", "page_url": page_url})
        start += 1
        time.sleep(delay)
    return records


def scrape_ord(delay=0.5, base="https://open-reaction-database.org/"):
    html = fetch(base)
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a"):
        href = a.get("href") or ""
        txt = a.get_text(" ", strip=True)
        full = urljoin(base, href)
        if any(x in href.lower() for x in ["search", "dataset", "data", "doi", "record"]):
            links.append({"text": txt, "url": full})
    metas = []
    for m in soup.find_all("meta"):
        name = m.get("name") or m.get("property") or ""
        content = m.get("content") or ""
        if name and content:
            metas.append({"name": name, "content": content})
    title = soup.title.get_text(strip=True) if soup.title else ""
    return {"title": title, "links": links, "metas": metas}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", choices=["kmt", "ord"], required=False, default="ord")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--max-pages", type=int, default=50)
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()
    if args.site == "kmt":
        data = scrape_kmt(start=args.start, max_pages=args.max_pages)
        out = args.out or "kmt_reactions.json"
    else:
        data = scrape_ord()
        out = args.out or "ord_site.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(out)


if __name__ == "__main__":
    main()

