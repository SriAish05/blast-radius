# Robot Crawler (`crawler/`)

The crawler visits client websites using headless Chromium and records every script that loads, along with **who loaded it** (either the HTML page or an upstream runtime script).

It implements **HANDBOOK.md Section 9.1** and outputs JSON files conforming strictly to **`contracts/crawl_example.json`** (Section 6.2).

---

## 🛠️ Prerequisites & Setup

Run these commands in your terminal:

```bash
# 1. Install Playwright library
pip install playwright

# 2. Download the Chromium browser engine
playwright install chromium
```

---

## 📁 File Structure

```
crawler/
├── crawl.py          # Main crawler script (Playwright + Chrome DevTools Protocol)
├── sites.json        # List of client websites and pages to crawl
├── test_crawl.py     # Automated test suite (local server simulating real chains)
├── README.md         # This guide
└── output/           # Destination for crawled page JSON files
```

---

## ⚙️ Configuration (`crawler/sites.json`)

List each client site, developer owner, and pages to visit:

```json
[
  {
    "client": "SmileCare Dental Clinic",
    "developer": "Teammate 3",
    "site": "https://dental-hospital-nine.vercel.app",
    "pages": ["/"]
  },
  {
    "client": "SmartMart",
    "developer": "Teammate 3",
    "site": "https://smartmart-demo.netlify.app",
    "pages": ["/"]
  },
  {
    "client": "Aurelis",
    "developer": "Teammate 3",
    "site": "https://frontend-fawn-mu-z8o5xkbha4.vercel.app",
    "pages": ["/"]
  },
  {
    "client": "Wedding hall",
    "developer": "Teammate 4",
    "site": "https://wedding-hall-demo.netlify.app",
    "pages": ["/"]
  },
  {
    "client": "Cafe",
    "developer": "Teammate 4",
    "site": "https://cafe-demo.vercel.app",
    "pages": ["/"]
  }
]
```

---

## 🚀 Running the Crawler

From the root of the project:

```bash
python crawler/crawl.py
```

Or with custom files:

```bash
python crawler/crawl.py path/to/custom_sites.json path/to/output_dir
```

---

## 📄 Output Format (`crawler/output/*.json`)

For each page visited, a JSON file is saved in `crawler/output/`:

```json
{
  "site": "https://dental-hospital-nine.vercel.app",
  "page": "https://dental-hospital-nine.vercel.app/",
  "crawled_at": "2026-10-17T23:39:16+05:30",
  "scripts": [
    {
      "url": "https://cdn-demo.netlify.app/chat-widget.js",
      "sha256": "...",
      "has_sri": false,
      "loaded_by": "page"
    },
    {
      "url": "https://cdn-demo.netlify.app/helper.js",
      "sha256": "...",
      "has_sri": false,
      "loaded_by": "https://cdn-demo.netlify.app/chat-widget.js"
    }
  ]
}
```

- `loaded_by`: `"page"` if loaded directly in the HTML `<head>` or `<body>`. If injected dynamically by another script, it contains that script's exact URL.
- `sha256`: SHA-256 hash of the downloaded script body.
- `has_sri`: `true` if the `<script>` tag has an `integrity="..."` attribute in the DOM, else `false`.

---

## 🧪 Running Automated Tests

To run the local test suite verifying multi-hop script chains, SRI detection, and safe site controls:

```bash
python crawler/test_crawl.py
```
