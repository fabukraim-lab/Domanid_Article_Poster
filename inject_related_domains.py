import os
import re
import html as html_mod
from datetime import datetime

ARTICLES_DIR = "articles"
TEMPLATE_PATH = "article_template.html"

DOMAINS_DATA = [
    {"domain": "attorneyauto.com", "premium": True, "link": "https://domanid.com/#all", "description": "Premium domain for car accident legal services. High SEO potential targeting legal clients.", "keywords": ["attorney", "auto", "car accident", "legal", "lawyer", "injury", "personal injury", "law firm", "accident lawyer", "legal marketing"]},
    {"domain": "dentalimplantsservice.com", "premium": True, "link": "https://domanid.com/#all", "description": "Perfect domain for dental implant clinics. SEO-rich, builds trust, memorable for patients.", "keywords": ["dental", "implant", "dentist", "dental clinic", "teeth", "oral", "cosmetic dentistry", "dental care"]},
    {"domain": "digitately.com", "premium": True, "link": "https://domanid.com/#all", "description": "Creative brandable domain for digital agencies, tech startups, and app developers.", "keywords": ["digital", "tech", "startup", "agency", "brandable", "technology", "software", "app", "creative", "design", "web"]},
    {"domain": "lawyerslegaladvice.com", "premium": True, "link": "https://domanid.com/#all", "description": "Premium domain for legal advice platforms. Keyword-rich, authoritative, trust-building.", "keywords": ["lawyer", "legal", "legal advice", "law firm", "counsel", "solicitor", "legal help", "attorney"]},
    {"domain": "poolcleanermiami.com", "premium": True, "link": "https://domanid.com/#all", "description": "Premium local domain for Miami pool cleaning services. SEO-friendly and brandable.", "keywords": ["pool", "cleaning", "miami", "pool service", "swimming", "pools", "local business", "pool maintenance"]},
    {"domain": "bestdeodorants.com", "premium": False, "link": "https://domanid.com/#all", "description": "Keyword-rich domain for deodorant and personal care e-commerce. Memorable and brandable.", "keywords": ["deodorant", "beauty", "personal care", "hygiene", "body care", "fragrance", "cosmetic", "ecommerce"]},
    {"domain": "besteuropevacations.com", "premium": False, "link": "https://domanid.com/#all", "description": "Excellent domain for European travel deals. SEO-optimized for tours and holiday packages.", "keywords": ["europe", "vacation", "travel", "tourism", "holiday", "trip", "destination", "tour", "travel agency"]},
    {"domain": "bestlawyercaraccident.com", "premium": False, "link": "https://domanid.com/#all", "description": "Targeted domain for car accident legal services. SEO-rich for PPC and organic traffic.", "keywords": ["lawyer", "car accident", "legal", "injury", "auto accident", "accident lawyer", "personal injury"]},
    {"domain": "buyslivercoins.com", "premium": False, "link": "https://domanid.com/#all", "description": "Ideal domain for silver coin trading and precious metals e-commerce. Trustworthy and direct.", "keywords": ["silver", "coin", "investment", "precious metal", "collectible", "bullion", "metal investing"]},
    {"domain": "cardrivinginstructors.com", "premium": False, "link": "https://domanid.com/#all", "description": "Perfect domain for driving schools and instructor networks. SEO-optimized for learner traffic.", "keywords": ["driving", "instructor", "driving school", "driver education", "learner", "driving lesson", "driving test"]},
    {"domain": "chevroletdealership.com", "premium": False, "link": "https://domanid.com/#all", "description": "Strong brandable domain for Chevrolet dealerships. High keyword relevance for auto sales.", "keywords": ["chevrolet", "dealership", "car dealer", "auto", "automotive", "car sales", "vehicle"]},
    {"domain": "clinicvictoria.com", "premium": False, "link": "https://domanid.com/#all", "description": "Professional domain for medical or beauty clinics. Great for local SEO and client trust.", "keywords": ["clinic", "victoria", "medical", "health", "healthcare", "doctor", "beauty clinic", "medical practice"]},
    {"domain": "companyinspector.com", "premium": False, "link": "https://domanid.com/#all", "description": "Keyword-rich domain for business audits and compliance services. Authoritative and memorable.", "keywords": ["company", "inspection", "business audit", "compliance", "due diligence", "investigation", "business"]},
    {"domain": "createproposal.com", "premium": False, "link": "https://domanid.com/#all", "description": "Brandable domain for proposal platforms and business templates. Versatile and action-oriented.", "keywords": ["proposal", "template", "business plan", "presentation", "contract", "pitch", "document"]},
    {"domain": "flowershopboston.com", "premium": False, "link": "https://domanid.com/#all", "description": "Perfect local domain for Boston flower shops. SEO-friendly for local delivery and orders.", "keywords": ["flower", "boston", "florist", "flower shop", "gift", "bouquet", "flower delivery"]},
    {"domain": "garagefloortiling.com", "premium": False, "link": "https://domanid.com/#all", "description": "Domain for flooring and renovation businesses. SEO-optimized and professionally brandable.", "keywords": ["garage", "flooring", "tile", "renovation", "home improvement", "floor", "contractor", "remodeling"]},
    {"domain": "gilbertarizonahome.com", "premium": False, "link": "https://domanid.com/#all", "description": "Targeted real estate domain for Gilbert, Arizona. Perfect for local realtors and listings.", "keywords": ["real estate", "gilbert", "arizona", "home", "house", "property", "realtor", "real estate agent"]},
    {"domain": "hotelsmajorca.com", "premium": False, "link": "https://domanid.com/#all", "description": "Ideal domain for Majorca hotel booking and travel sites. SEO-friendly for tourism marketing.", "keywords": ["hotel", "majorca", "travel", "tourism", "accommodation", "resort", "vacation", "booking"]},
    {"domain": "hotelsvictorville.com", "premium": False, "link": "https://domanid.com/#all", "description": "Perfect domain for Victorville hotel listings. Optimized for local search and PPC campaigns.", "keywords": ["hotel", "victorville", "travel", "accommodation", "lodging", "motel", "local business"]},
    {"domain": "lawyeremploymentdiscrimination.com", "premium": False, "link": "https://domanid.com/#all", "description": "Niche legal domain for employment discrimination cases. High SEO value for specialized queries.", "keywords": ["lawyer", "employment", "discrimination", "labor law", "workplace", "employment law", "harassment"]},
    {"domain": "lifeinsuranceinstantly.com", "premium": False, "link": "https://domanid.com/#all", "description": "Strong domain for instant life insurance platforms. SEO and PPC optimized for conversions.", "keywords": ["life insurance", "insurance", "life coverage", "financial planning", "insurance quote", "term life"]},
    {"domain": "modernisedfurniture.com", "premium": False, "link": "https://domanid.com/#all", "description": "Brandable domain for modern furniture and home decor e-commerce. Memorable and stylish.", "keywords": ["furniture", "modern", "decor", "home", "interior design", "furnishings", "home improvement"]},
    {"domain": "nurseslicenses.com", "premium": False, "link": "https://domanid.com/#all", "description": "Keyword-rich domain for nursing license resources. Strong SEO for professional certification.", "keywords": ["nurse", "nursing", "license", "certification", "healthcare", "medical education", "nursing license"]},
    {"domain": "rentalcarcharlotte.com", "premium": False, "link": "https://domanid.com/#all", "description": "Targeted domain for Charlotte car rentals. Local SEO-optimized for travel and tourism.", "keywords": ["car rental", "charlotte", "rental car", "travel", "transportation", "rent a car"]},
    {"domain": "rosedeliver.com", "premium": False, "link": "https://domanid.com/#all", "description": "Elegant domain for flower and gift delivery services. Memorable and brandable for local markets.", "keywords": ["roses", "flower delivery", "gift", "florist", "delivery", "bouquet", "flower"]},
    {"domain": "singaporetravelagent.com", "premium": False, "link": "https://domanid.com/#all", "description": "Professional domain for Singapore travel agencies. SEO-rich for tourism and vacation packages.", "keywords": ["singapore", "travel", "travel agent", "tourism", "vacation", "travel agency", "tour"]},
    {"domain": "thebostonhouse.com", "premium": False, "link": "https://domanid.com/#all", "description": "Targeted domain for Boston real estate and rental brands. Local SEO-friendly and memorable.", "keywords": ["boston", "real estate", "house", "home", "property", "rental", "realtor", "housing"]},
    {"domain": "unitehealthinsurance.com", "premium": False, "link": "https://domanid.com/#all", "description": "Strong brandable domain for health insurance providers. Builds trust and drives conversions.", "keywords": ["health insurance", "insurance", "healthcare", "medical", "coverage", "health plan", "benefits"]},
    {"domain": "windowtintingvegas.com", "premium": False, "link": "https://domanid.com/#all", "description": "Local business domain for Las Vegas window tinting. SEO-rich and service-focused branding.", "keywords": ["window tinting", "las vegas", "auto tint", "window film", "car tint", "tint"]},
    {"domain": "womanclothesstore.com", "premium": False, "link": "https://domanid.com/#all", "description": "E-commerce domain for women's clothing. SEO-friendly, brandable, and fashion-focused.", "keywords": ["women", "clothing", "fashion", "apparel", "ecommerce", "store", "style", "wardrobe"]},
]

CATEGORY_BOOSTS = {
    "legal": ["attorneyauto.com", "lawyerslegaladvice.com", "bestlawyercaraccident.com", "lawyeremploymentdiscrimination.com"],
    "law": ["attorneyauto.com", "lawyerslegaladvice.com", "bestlawyercaraccident.com", "lawyeremploymentdiscrimination.com"],
    "technology": ["digitately.com"],
    "tech": ["digitately.com"],
    "digital": ["digitately.com"],
    "travel": ["besteuropevacations.com", "hotelsmajorca.com", "singaporetravelagent.com", "besteuropevacations.com"],
    "tourism": ["besteuropevacations.com", "hotelsmajorca.com", "singaporetravelagent.com"],
    "health": ["clinicvictoria.com", "dentalimplantsservice.com", "unitehealthinsurance.com", "lifeinsuranceinstantly.com", "nurseslicenses.com"],
    "medical": ["dentalimplantsservice.com", "clinicvictoria.com", "unitehealthinsurance.com"],
    "dental": ["dentalimplantsservice.com"],
    "seo": ["attorneyauto.com", "bestlawyercaraccident.com", "dentalimplantsservice.com", "poolcleanermiami.com"],
    "real estate": ["gilbertarizonahome.com", "thebostonhouse.com"],
    "insurance": ["lifeinsuranceinstantly.com", "unitehealthinsurance.com"],
    "ecommerce": ["bestdeodorants.com", "buyslivercoins.com", "womanclothesstore.com", "modernisedfurniture.com", "rosedeliver.com", "flowershopboston.com"],
    "retail": ["bestdeodorants.com", "womanclothesstore.com", "flowershopboston.com", "rosedeliver.com"],
    "automotive": ["attorneyauto.com", "chevroletdealership.com", "rentalcarcharlotte.com", "cardrivinginstructors.com", "windowtintingvegas.com"],
    "car": ["attorneyauto.com", "chevroletdealership.com", "rentalcarcharlotte.com", "cardrivinginstructors.com", "bestlawyercaraccident.com"],
    "business": ["companyinspector.com", "createproposal.com", "digitately.com"],
    "startup": ["digitately.com", "createproposal.com"],
    "investment": ["buyslivercoins.com", "attorneyauto.com"],
    "branding": ["digitately.com", "attorneyauto.com"],
    "fashion": ["womanclothesstore.com", "modernisedfurniture.com"],
    "home": ["gilbertarizonahome.com", "thebostonhouse.com", "modernisedfurniture.com", "garagefloortiling.com"],
    "local": ["poolcleanermiami.com", "windowtintingvegas.com", "flowershopboston.com", "rentalcarcharlotte.com", "garagefloortiling.com", "hotelsvictorville.com", "thebostonhouse.com", "gilbertarizonahome.com"],
    "domain": [],  # all domains are related to domains, skip broad match
}


def extract_title_category_content(html_content):
    title_match = re.search(r'<title>(.*?)\s*-\s*DomanID</title>', html_content, re.IGNORECASE)
    title = title_match.group(1) if title_match else ""

    cat_match = re.search(r'<span class="article-meta">([^|]+?)\s*\|', html_content)
    category = cat_match.group(1).strip() if cat_match else ""

    kw_match = re.search(r'<meta name="keywords" content="([^"]+)">', html_content)
    keywords = kw_match.group(1).strip() if kw_match else ""

    body_match = re.search(r'<div class="article-body">(.*?)</div>\s*', html_content, re.DOTALL)
    body_text = ""
    if body_match:
        body_text = re.sub(r'<[^>]+>', ' ', body_match.group(1))
        body_text = re.sub(r'\s+', ' ', body_text).strip().lower()

    return title, category, keywords, body_text


def score_domain(domain_info, title, category, keywords, body_text):
    score = 0
    domain_name = domain_info["domain"]
    kw_list = domain_info["keywords"]
    title_lower = title.lower()
    category_lower = category.lower()
    keywords_lower = keywords.lower()

    for kw in kw_list:
        kw_lower = kw.lower()
        if kw_lower in title_lower:
            score += 5
        if kw_lower in category_lower:
            score += 4
        if kw_lower in keywords_lower:
            score += 3
        if body_text and kw_lower in body_text:
            score += 1

    for cat_key, domains in CATEGORY_BOOSTS.items():
        if cat_key in category_lower or cat_key in title_lower:
            if domain_name in domains:
                score += 4

    if domain_info["premium"]:
        score += 2

    return score


def get_domain_card_html(d):
    premium_badge = '<span class="premium-badge">Premium</span>' if d["premium"] else ""
    return f'''
            <a href="{d['link']}" class="domain-card-inline" target="_blank">
                <div class="domain-card-header">
                    <span class="domain-name">{d['domain']}</span>
                    {premium_badge}
                </div>
                <p class="domain-desc">{html_mod.escape(d['description'])}</p>
                <span class="domain-cta">Explore Domain &rarr;</span>
            </a>'''


def get_related_domains_html(title, category, keywords, body_text, max_domains=3):
    scored = []
    for d in DOMAINS_DATA:
        s = score_domain(d, title, category, keywords, body_text)
        if s > 0:
            scored.append((s, d))

    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [d for _, d in scored[:max_domains]]

    if not selected:
        return ""

    cards = "".join(get_domain_card_html(d) for d in selected)
    return f'''
        <div class="related-premium-domains">
            <h3>Related Premium Domains</h3>
            <p class="section-subtitle">Domain names that complement this topic</p>
            <div class="domains-inline-grid">{cards}
            </div>
        </div>'''


def inject_related_domains(filepath):
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    if 'class="related-premium-domains"' in content:
        print(f"  Skipped (already has related domains): {filepath}")
        return

    title, category, keywords, body_text = extract_title_category_content(content)
    related_html = get_related_domains_html(title, category, keywords, body_text)

    if not related_html:
        print(f"  Skipped (no matching domains): {filepath}")
        return

    cta_patterns = [
        (r'<div class="cta-box">', '<div class="cta-box">'),
        (r'<div style="margin-top: 50px; padding: 30px; background: var\(--primary-50\);\s*border: 1px solid var\(--primary-200\);\s*border-radius: 20px;\s*text-align: center;">', '<div style="margin-top: 50px; padding: 30px; background: var(--primary-50); border: 1px solid var(--primary-200); border-radius: 20px; text-align: center;">'),
    ]
    new_content = content
    for pattern, replacement in cta_patterns:
        new_content = re.sub(pattern, related_html + "\n\n            " + replacement, new_content, count=1)
        if new_content != content:
            break

    if new_content == content:
        print(f"  WARNING: Could not find CTA in: {filepath}")
        return

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"  Injected related domains: {filepath}")


def update_template():
    if not os.path.exists(TEMPLATE_PATH):
        print(f"Template not found: {TEMPLATE_PATH}")
        return

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    if "{{RELATED_DOMAINS}}" in content:
        print("Template already has {{RELATED_DOMAINS}} placeholder.")
    else:
        content = content.replace("<!-- CTA -->", "            {{RELATED_DOMAINS}}\n\n            <!-- CTA -->")
        with open(TEMPLATE_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        print("Added {{RELATED_DOMAINS}} placeholder to template.")

    css_block = """.related-premium-domains {
    margin: 40px 0;
}
.related-premium-domains h3 {
    font-family: 'Playfair Display', serif;
    font-size: 1.5rem;
    color: var(--text-heading);
    margin-bottom: 8px;
    text-align: center;
}
.section-subtitle {
    text-align: center;
    color: var(--text-muted);
    margin-bottom: 24px;
    font-size: 1rem;
}
.domains-inline-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 20px;
}
.domain-card-inline {
    display: block;
    padding: 24px;
    background: linear-gradient(135deg, rgba(12, 74, 110, 0.08), rgba(8, 47, 73, 0.05));
    border: 1px solid var(--border-light);
    border-radius: 16px;
    text-decoration: none;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.domain-card-inline:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-md);
    border-color: var(--primary-500);
}
.domain-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 8px;
}
.domain-name {
    font-family: 'Playfair Display', serif;
    font-size: 1.2rem;
    font-weight: 700;
    color: var(--text-heading);
    word-break: break-all;
}
.premium-badge {
    font-size: 0.7rem;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 20px;
    background: linear-gradient(135deg, #fbbf24, #f59e0b);
    color: #111827;
    white-space: nowrap;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.domain-desc {
    color: var(--text-secondary);
    font-size: 0.9rem;
    line-height: 1.5;
    margin: 0 0 12px;
}
.domain-cta {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--primary-500);
}
@media (max-width: 480px) {
    .domains-inline-grid {
        grid-template-columns: 1fr;
    }
    .domain-card-inline {
        padding: 16px;
    }
}"""

    if ".related-premium-domains" in content:
        print("Template CSS already has .related-premium-domains styles.")
    else:
        content = content.replace("</style>", css_block + "\n    </style>")
        with open(TEMPLATE_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        print("Added .related-premium-domains CSS to template.")


def main():
    print("=== Inject Related Premium Domains into Articles ===\n")

    print("1. Updating template...")
    update_template()
    print()

    print("2. Processing existing articles...")
    if not os.path.exists(ARTICLES_DIR):
        print(f"Articles directory not found: {ARTICLES_DIR}")
        return

    files = sorted(os.listdir(ARTICLES_DIR))
    html_files = [f for f in files if f.endswith(".html") and f != "index.html"]
    print(f"Found {len(html_files)} article files.")

    updated = 0
    for fname in html_files:
        filepath = os.path.join(ARTICLES_DIR, fname)
        prev_content = open(filepath, "r", encoding="utf-8", errors="replace").read()
        inject_related_domains(filepath)
        new_content = open(filepath, "r", encoding="utf-8", errors="replace").read()
        if prev_content != new_content:
            updated += 1

    print(f"\nUpdated {updated} of {len(html_files)} articles.")
    print("Done.")


if __name__ == "__main__":
    main()
