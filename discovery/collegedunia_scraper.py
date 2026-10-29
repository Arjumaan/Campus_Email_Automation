"""CollegeDunia India colleges scraper.

Fetches the list of colleges from CollegeDunia for ANY state in India
and resolves each college's official website URL, producing a list of dicts
suitable for writing to data/seed_colleges.csv or directly importing via auto_discovery.

Supported states include:
    Karnataka, Tamil Nadu, Maharashtra, Kerala, Delhi NCR, Uttar Pradesh,
    Andhra Pradesh, Telangana, Gujarat, Rajasthan, West Bengal, Punjab,
    Haryana, Madhya Pradesh, Bihar, Odisha, Assam, Goa, Uttarakhand,
    Jharkhand, Chhattisgarh, Himachal Pradesh, Jammu and Kashmir, Chandigarh,
    Puducherry, and all other Indian states and union territories.

Usage (standalone):
    python -m discovery.collegedunia_scraper --state "Tamil Nadu" --limit 10

Usage (as module):
    from discovery.collegedunia_scraper import scrape_colleges, scrape_karnataka_colleges
    colleges = scrape_colleges(state="Tamil Nadu", limit=50)  # any state
    karnataka = scrape_karnataka_colleges(limit=50)            # backward-compatible
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Optional
from urllib.parse import urlparse
import urllib.request
import urllib.error

log = logging.getLogger(__name__)

BASE_URL = "https://collegedunia.com"

# Standard list of Indian States and Union Territories
INDIAN_STATES = [
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chandigarh",
    "Chhattisgarh",
    "Delhi NCR",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jammu and Kashmir",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Puducherry",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
]

# Map friendly state names to CollegeDunia URL slugs
STATE_SLUG_MAP = {
    "andhra pradesh": "andhra-pradesh",
    "arunachal pradesh": "arunachal-pradesh",
    "assam": "assam",
    "bihar": "bihar",
    "chandigarh": "chandigarh",
    "chhattisgarh": "chhattisgarh",
    "delhi": "delhi-ncr",
    "delhi ncr": "delhi-ncr",
    "new delhi": "delhi-ncr",
    "goa": "goa",
    "gujarat": "gujarat",
    "haryana": "haryana",
    "himachal pradesh": "himachal-pradesh",
    "jammu and kashmir": "jammu-and-kashmir",
    "jammu & kashmir": "jammu-and-kashmir",
    "jharkhand": "jharkhand",
    "karnataka": "karnataka",
    "kerala": "kerala",
    "madhya pradesh": "madhya-pradesh",
    "maharashtra": "maharashtra",
    "manipur": "manipur",
    "meghalaya": "meghalaya",
    "mizoram": "mizoram",
    "nagaland": "nagaland",
    "odisha": "odisha",
    "orissa": "odisha",
    "puducherry": "puducherry",
    "pondicherry": "puducherry",
    "punjab": "punjab",
    "rajasthan": "rajasthan",
    "sikkim": "sikkim",
    "tamil nadu": "tamil-nadu",
    "tamilnadu": "tamil-nadu",
    "telangana": "telangana",
    "tripura": "tripura",
    "uttar pradesh": "uttar-pradesh",
    "uttarakhand": "uttarakhand",
    "west bengal": "west-bengal",
}

# Headers to mimic a real browser request
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
}


def get_state_slug(state: str) -> str:
    """Convert any state name into the CollegeDunia URL slug."""
    raw = (state or "").strip().lower()
    if raw.endswith("-colleges"):
        raw = raw[:-9]
    if raw in STATE_SLUG_MAP:
        return STATE_SLUG_MAP[raw]
    # Check if a mapped slug matches directly
    for slug in STATE_SLUG_MAP.values():
        if raw == slug:
            return slug
    # Fallback: slugify input
    slug = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return slug or "kerala"


def get_state_listing_url(state: str) -> str:
    """Return the CollegeDunia listing URL for the given state."""
    slug = get_state_slug(state)
    return f"{BASE_URL}/{slug}-colleges"


def _fetch(url: str, timeout: int = 15) -> str:
    """Fetch a URL and return the HTML as a string."""
    req = urllib.request.Request(url, headers=_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = "utf-8"
            ct = resp.headers.get("Content-Type", "")
            if "charset=" in ct:
                charset = ct.split("charset=")[-1].strip()
            return resp.read().decode(charset, errors="replace")
    except urllib.error.URLError as exc:
        log.warning("Fetch failed for %s: %s", url, exc)
        return ""


def _extract_json_ld(html: str) -> list:
    """Extract all JSON-LD blocks from an HTML page."""
    blocks = []
    for match in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.DOTALL | re.IGNORECASE,
    ):
        try:
            blocks.append(json.loads(match.group(1)))
        except json.JSONDecodeError:
            pass
    return blocks


def _get_college_urls_from_listing(html: str) -> list:
    """Extract college page URLs from the JSON-LD ItemList on the listing page."""
    urls = []
    for block in _extract_json_ld(html):
        if block.get("@type") == "ItemList":
            for item in block.get("itemListElement", []):
                url = item.get("url", "").strip()
                if url and "collegedunia.com" in url:
                    urls.append(url)
    return urls


def _slug_to_name(slug: str) -> str:
    """Convert a URL slug like '25621-national-law-school-of-india-university-nlsiu-bangalore'
    into a readable college name, stripping the leading ID number."""
    slug = re.sub(r"^\d+-", "", slug)
    return slug.replace("-", " ").title()


# Major Kerala cities and educational hubs for location inference
KERALA_CITIES = [
    "Kozhikode", "Calicut", "Kochi", "Cochin", "Thiruvananthapuram", "Trivandrum",
    "Ernakulam", "Thrissur", "Trichur", "Kottayam", "Kollam", "Quilon", "Palakkad",
    "Palghat", "Malappuram", "Kannur", "Cannanore", "Alappuzha", "Alleppey", "Kasaragod",
    "Pathanamthitta", "Wayanad", "Idukki", "Kalamassery", "Kovalam", "Kanjirappally",
    "Manjeri", "Thalassery", "Ponnani", "Cherthala", "Kayamkulam", "Thiruvalla", "Pala",
    "Mavelikara", "Angamaly", "Perumbavoor", "Irinjalakuda", "Varkala",
]


def _extract_city(name: str, address: dict, street: str) -> str:
    """Extract or infer city name from structured address, college name, or street."""
    # 1. addressLocality
    loc = (address.get("addressLocality") or "").strip()
    if loc and loc.lower() not in ("kerala", "india", "in"):
        return loc

    # 2. Check suffix after comma in college name (e.g., "... [NITC], Calicut")
    if "," in name:
        candidate = name.split(",")[-1].strip()
        candidate = re.sub(r"\s+(Kerala|India)$", "", candidate, flags=re.I).strip()
        if candidate and len(candidate) < 35:
            for c in KERALA_CITIES:
                if c.lower() in candidate.lower():
                    return c
            return candidate

    # 3. Check for city in name
    for c in KERALA_CITIES:
        if re.search(r"\b" + re.escape(c) + r"\b", name, re.I):
            return c

    # 4. Check for city in street address
    if street:
        for c in KERALA_CITIES:
            if re.search(r"\b" + re.escape(c) + r"\b", street, re.I):
                return c

    return ""


def _extract_college_info(college_url: str, html: str, default_state: str = "Kerala") -> dict:
    """Extract official website, city, state and institution type from a college page."""
    result = {
        "name": "",
        "website": "",
        "city": "",
        "state": default_state,
        "institution_type": "",
        "source_url": college_url,
    }

    # Extract name from URL slug as initial fallback
    path = urlparse(college_url).path
    slug = path.strip("/").split("/")[-1]
    result["name"] = _slug_to_name(slug)

    # Try JSON-LD first (most reliable)
    for block in _extract_json_ld(html):
        btype = block.get("@type", "")
        bname = (block.get("name") or "").strip()
        burl = str(block.get("url") or "")

        # Skip Collegedunia's own corporate organization block
        if "collegedunia" in bname.lower() or "collegedunia" in burl.lower():
            continue

        if btype in ("CollegeOrUniversity", "EducationalOrganization", "Organization", "University"):
            if bname:
                result["name"] = bname
            website = block.get("url", "") or block.get("sameAs", "")
            if isinstance(website, list):
                website = next((u for u in website if "collegedunia" not in str(u)), "")
            if website and "collegedunia" not in str(website):
                result["website"] = str(website).strip()
            address = block.get("address", {})
            if isinstance(address, dict):
                region = address.get("addressRegion", "").strip()
                if region and region.lower() not in ("india", "in"):
                    result["state"] = region
                street = address.get("streetAddress", "")
                result["city"] = _extract_city(result["name"], address, street)

    # If city is still blank, infer from college name
    if not result["city"] and result["name"]:
        result["city"] = _extract_city(result["name"], {}, "")

    # If no website found from JSON-LD, try canonical link tag
    if not result["website"]:
        canonical_match = re.search(
            r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', html, re.IGNORECASE
        )
        if canonical_match:
            url_val = canonical_match.group(1)
            if "collegedunia" not in url_val:
                result["website"] = url_val

    # Infer institution type
    itype = ""
    name_lower = result["name"].lower()
    url_lower = college_url.lower()
    if "university" in url_lower or "university" in name_lower:
        itype = "University"
    elif any(k in name_lower for k in ["engineering", "technology", "technical", "polytechnic"]):
        itype = "Engineering"
    elif any(k in name_lower for k in ["medical", "medicine", "nursing", "dental", "pharmacy"]):
        itype = "Medical"
    elif any(k in name_lower for k in ["law", "legal"]):
        itype = "Law"
    elif any(k in name_lower for k in ["management", "business", "mba", "commerce"]):
        itype = "Management"
    elif any(k in name_lower for k in ["arts", "science", "college"]):
        itype = "College"
    result["institution_type"] = itype

    return result


def _extract_name_from_html(html: str, fallback: str) -> str:
    """Try to get the clean college name from og:title or page title."""
    # If fallback is already a clean college name from JSON-LD, keep it!
    if fallback and not any(k in fallback for k in ["Fees", "Admission", "Review", "Cutoff", "Placement", "202"]):
        return fallback

    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if m:
        title = m.group(1).strip()
        title = re.split(r"\s*[:\-|]\s*(Collegedunia|Fees|Admission|Review|Courses|Cutoff|Ranking|Placement)", title, flags=re.IGNORECASE)[0].strip()
        if title and len(title) > 3:
            return title

    m2 = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if m2:
        title = m2.group(1).strip()
        title = re.split(r"\s*[:\-|]\s*(Collegedunia|Fees|Admission|Review|Courses|Cutoff|Ranking|Placement)", title, flags=re.IGNORECASE)[0].strip()
        if title and len(title) > 3:
            return title

    return fallback


def _find_official_website_in_html(html: str) -> str:
    """Last-resort: scan HTML for an 'Official Website' link."""
    pattern = re.compile(
        r'[Oo]fficial\s+[Ww]ebsite.*?href=["\']([^"\']+)["\']|'
        r'href=["\']([^"\']+)["\'][^>]*>.*?[Oo]fficial\s+[Ww]ebsite',
        re.DOTALL,
    )
    for m in pattern.finditer(html):
        url = m.group(1) or m.group(2) or ""
        url = url.strip()
        if url and url.startswith("http") and "collegedunia" not in url:
            return url
    return ""


# Major stream categories available on CollegeDunia
STREAM_CATEGORIES = [
    "engineering",
    "management",
    "medical",
    "science",
    "commerce",
    "arts",
    "law",
    "pharmacy",
    "architecture",
    "dental",
    "agriculture",
    "education",
    "hotel-management",
    "paramedical",
    "computer-applications",
    "design",
]

# Kerala district listing slugs on CollegeDunia
KERALA_DISTRICT_SLUGS = [
    "kochi",
    "thiruvananthapuram",
    "kozhikode",
    "kottayam",
    "thrissur",
    "kollam",
    "palakkad",
    "malappuram",
    "kannur",
    "alappuzha",
    "kasaragod",
    "pathanamthitta",
    "wayanad",
    "idukki",
]


def get_state_listing_urls(state: str, deep: bool = False) -> list[str]:
    """Return all listing URLs to scrape for the given state.

    If deep=True, expands to all stream categories and regional districts,
    discovering 500+ institutions instead of only the top 30 on the primary page.
    """
    slug = get_state_slug(state)
    urls = [f"{BASE_URL}/{slug}-colleges"]

    if not deep:
        return urls

    # Category listings for this state (e.g. /engineering/kerala-colleges)
    for cat in STREAM_CATEGORIES:
        urls.append(f"{BASE_URL}/{cat}/{slug}-colleges")

    # If state is Kerala, add all 14 district listings
    if slug == "kerala":
        for district in KERALA_DISTRICT_SLUGS:
            urls.append(f"{BASE_URL}/{district}-colleges")

    return urls


def _fetch_single_college(url: str, default_state: str) -> Optional[dict]:
    """Fetch and parse one college detail page. Returns dict or None."""
    page_html = _fetch(url)
    if not page_html:
        return None

    info = _extract_college_info(url, page_html, default_state=default_state)
    fallback_name = info["name"]
    better_name = _extract_name_from_html(page_html, fallback_name)
    if better_name != fallback_name:
        info["name"] = better_name

    if not info["website"]:
        info["website"] = _find_official_website_in_html(page_html)

    return info if info.get("website") else None


def scrape_colleges(
    state: str = "Kerala",
    limit: Optional[int] = None,
    delay: float = 0.5,
    verbose: bool = True,
    deep: bool = False,
    workers: int = 6,
) -> list:
    """Scrape CollegeDunia for colleges in any Indian state.

    Returns a list of dicts with keys:
        name, website, state, city, institution_type, source_url

    Only colleges where an official website could be resolved are returned.

    Args:
        state: Name of the Indian state (e.g. 'Kerala', 'Karnataka', etc.).
        limit: Maximum number of colleges to process (None = all available).
        delay: Delay in seconds between requests (for single-worker mode).
        verbose: Print progress to stdout.
        deep: If True, scrape across all streams and districts (discovers 500+ colleges).
        workers: Number of concurrent threads for detail page fetching.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    state_display = state.strip().title()
    listing_urls = get_state_listing_urls(state, deep=deep)

    if verbose:
        print(f"[CollegeDunia] Target State: {state_display}")
        print(f"[CollegeDunia] Scanning {len(listing_urls)} listing page(s) (deep={deep})...")

    college_urls = []
    seen_urls = set()

    for l_url in listing_urls:
        html = _fetch(l_url)
        if not html:
            continue
        extracted = _get_college_urls_from_listing(html)
        new_count = 0
        for u in extracted:
            if u not in seen_urls:
                seen_urls.add(u)
                college_urls.append(u)
                new_count += 1
        if verbose and deep and new_count > 0:
            slug_part = l_url.split("collegedunia.com/")[-1]
            print(f"  + {slug_part}: {len(extracted)} colleges ({new_count} new, cumulative: {len(college_urls)})")

    if not college_urls:
        log.error("No college URLs found for %s", state_display)
        return []

    total_found = len(college_urls)
    if verbose:
        print(f"[OK] Discovered {total_found} unique college URLs across {state_display}")

    if limit and limit > 0:
        college_urls = college_urls[:limit]
        if verbose:
            print(f"[INFO] Processing first {len(college_urls)} colleges (limit={limit})")

    results = []
    completed_count = 0
    total_to_fetch = len(college_urls)

    if workers > 1:
        if verbose:
            print(f"[INFO] Fetching college details with {workers} concurrent workers...")

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_fetch_single_college, u, state_display): u
                for u in college_urls
            }
            for fut in as_completed(futures):
                completed_count += 1
                try:
                    res = fut.result()
                    if res and res.get("website"):
                        results.append(res)
                        if verbose and (completed_count % 25 == 0 or completed_count == total_to_fetch):
                            print(f"  [{completed_count}/{total_to_fetch}] Resolved: {res['name']} ({len(results)} valid websites)")
                except Exception as exc:
                    log.debug("Worker fetch error: %s", exc)
    else:
        for i, url in enumerate(college_urls, start=1):
            if verbose and (i % 10 == 0 or i == 1):
                print(f"  [{i}/{len(college_urls)}] Fetching: {url}")
            res = _fetch_single_college(url, default_state=state_display)
            if res:
                results.append(res)
                if verbose:
                    print(f"    [+] {res['name']} -> {res['website']}")
            time.sleep(delay)

    if verbose:
        print(f"\n[DONE] Successfully resolved {len(results)} colleges with verified official websites out of {len(college_urls)} candidates for {state_display}")

    return results


def scrape_kerala_colleges(
    limit: Optional[int] = None,
    delay: float = 1.0,
    verbose: bool = True,
) -> list:
    """Convenience alias for scrape_colleges(state='Kerala', ...)."""
    return scrape_colleges(state="Kerala", limit=limit, delay=delay, verbose=verbose)


def scrape_karnataka_colleges(
    limit: Optional[int] = None,
    delay: float = 1.0,
    verbose: bool = True,
) -> list:
    """Backward-compatible alias for scrape_colleges(state='Karnataka', ...)."""
    return scrape_colleges(state="Karnataka", limit=limit, delay=delay, verbose=verbose)


if __name__ == "__main__":
    import argparse
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Scrape colleges for any Indian state from CollegeDunia")
    parser.add_argument("--state", default="Kerala", help="State name (e.g., 'Kerala', 'Tamil Nadu', 'Maharashtra', 'Karnataka')")
    parser.add_argument("--limit", type=int, default=5, help="Number of colleges to scrape (default: 5)")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests in seconds")
    args = parser.parse_args()

    colleges = scrape_colleges(state=args.state, limit=args.limit, delay=args.delay, verbose=True)
    for c in colleges:
        print("  %s | %s | %s | %s" % (c["name"], c["website"], c["city"], c["state"]))
