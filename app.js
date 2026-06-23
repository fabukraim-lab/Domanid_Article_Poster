/**
 * DomanID - Main Application Logic
 * Automatically fetches from Google Sheets CSVs and renders the domains dynamically.
 */

// --- CONFIGURATION ---
const PREMIUM_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTu-hMWPh-WbM--mMk7tZjJmgSlRDO6k8VFMk_lmoiNWP2-_267ev0rBwXC5jPvDPenXmRQNeLB-8-H/pub?output=csv";
const ALL_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSqCdsEOjGGzEH5vKY7f_TMdobdDNYNcM24d9GDjGyrxZfHR4lomIuJUc6GzZLQ27OeQst-WYpIC0h1/pub?output=csv";

// Debounce utility
function debounce(fn, delay) {
    let timer;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

// Store data in memory for fast searching
let premiumDomains = [];
let allDomains = [];

// Fallback/Mock Data if user hasn't provided their CSV URL yet or if fetch fails
const MOCK_PREMIUM = [
    { title: 'Meta.com', description: 'Ultra premium short domain for tech giants.', link: '#' },
    { title: 'Crypto.net', description: 'Perfect for the next big cryptocurrency project.', link: '#' },
    { title: 'AI.org', description: 'Prime domain for open-source AI initiatives.', link: '#' }
];

const MOCK_ALL = [
    { title: 'TechStartup.com', description: 'Catchy and highly brandable startup name.', link: '#' },
    { title: 'FoodDelivery.app', description: 'Great for food delivery aggregators.', link: '#' },
    { title: 'CloudStorage.io', description: 'Ideal for modern cloud infrastructure.', link: '#' },
    { title: 'FinancePro.com', description: 'The absolute best name for financial services.', link: '#' },
    { title: 'SmartHome.net', description: 'Perfect for smart home automation.', link: '#' }
];

const MOCK_SOLD = [
    { title: 'GulfVentures.com', description: 'Acquired for an undisclosed amount.', link: '#' },
    { title: 'DubaiTech.net', description: 'Sold to a Dubai-based holding group.', link: '#' },
    { title: 'ArabShop.com', description: 'Bought by an e-commerce giant.', link: '#' }
];

/**
 * Parses CSV content professionally, handling quoted fields and commas inside text.
 */
function parseCSV(csvText) {
    const lines = csvText.split(/\r?\n/);
    const result = [];
    
    // Simple but robust CSV line parser for quoted strings
    const parseCSVLine = (text) => {
        const row = [];
        let inQuotes = false;
        let currentValue = '';
        
        for (let i = 0; i < text.length; i++) {
            const char = text[i];
            const nextChar = text[i + 1];
            
            if (char === '"' && inQuotes && nextChar === '"') {
                currentValue += '"'; // Escaped quote
                i++;
            } else if (char === '"') {
                inQuotes = !inQuotes;
            } else if (char === ',' && !inQuotes) {
                row.push(currentValue.trim());
                currentValue = '';
            } else {
                currentValue += char;
            }
        }
        row.push(currentValue.trim());
        return row;
    };

    // Skip header (i=0), process data lines
    for (let i = 1; i < lines.length; i++) {
        if (!lines[i].trim()) continue;
        const columns = parseCSVLine(lines[i]);
        
        // We expect columns: [Title, Description, Link, ...]
        // Clean and format the link
        let rawLink = columns[2] || '#';
        let formattedLink = rawLink;
        
        // If it's a domain name (no protocol and contains a dot), prepend https://
        if (rawLink !== '#' && !rawLink.startsWith('http') && rawLink.includes('.')) {
            formattedLink = `https://${rawLink}`;
        }

        result.push({
            title: columns[0] || 'Unknown Domain',
            description: columns[1] || 'A premium digital asset.',
            link: formattedLink
        });
    }
    return result;
}

/**
 * Creates the HTML for a single Domain Card
 */
function createDomainCard(domain, isPremium = false) {
    const card = document.createElement('div');
    card.className = 'domain-card glass-panel';
    card.setAttribute('itemscope', '');
    card.setAttribute('itemtype', 'https://schema.org/Product');
    
    const domainTitle = domain.title || domain.domain || 'Unknown.com';
    const domainDescription = domain.description || domain.price || 'A premium digital asset.';
    
    card.innerHTML = `
        <div class="domain-header" style="flex-direction: column; align-items: flex-start; gap: 10px;">
            <div style="display: flex; justify-content: space-between; width: 100%; align-items: center;">
                <h3 class="domain-name" style="font-size: 1.6rem; word-break: break-all;" itemprop="name">${domainTitle}</h3>
                ${isPremium ? '<span class="premium-badge">Premium</span>' : ''}
            </div>
            <meta itemprop="category" content="${isPremium ? 'Premium Domain' : 'Domain'}">
        </div>
        <p style="font-size: 1.1rem; color: var(--text-muted); margin-bottom: 20px; font-weight: normal; line-height: 1.6; flex-grow: 1;" itemprop="description">
            ${domainDescription}
        </p>
        <ul class="domain-features" style="margin-top: auto;">
            <li><span class="gradient-text">✓</span> Instant Secure Transfer</li>
            <li><span class="gradient-text">✓</span> 100% Buyer Protection</li>
        </ul>
        <a href="${domain.link || '#'}" target="_blank" class="btn-glow" style="width: 100%;" itemprop="url" onclick="gtag('event', 'domain_click', {domain: '${domainTitle}', type: '${isPremium ? 'premium' : 'standard'}', url: '${domain.link || '#'}'});">
            ${isPremium ? 'Buy Now' : 'Make an Offer'}
        </a>
        <link itemprop="availability" href="https://schema.org/InStock">
    `;
    
    return card;
}

/**
 * Renders an array of domains to a specific grid element
 */
function renderDomains(domains, gridElementId, isPremium) {
    const grid = document.getElementById(gridElementId);
    if (!grid) return;
    
    if (domains.length === 0) {
        grid.innerHTML = `<p style="text-align:center; grid-column: 1/-1; color: var(--text-muted);">No domains found matching criteria.</p>`;
        return;
    }
    
    grid.innerHTML = ''; // Clear existing content
    domains.forEach(d => grid.appendChild(createDomainCard(d, isPremium)));
}

/**
 * Fetches and initializes the domains from CSV
 */
async function loadDomains() {
    const premiumLoader = document.getElementById('premiumLoader');
    const allLoader = document.getElementById('allLoader');
    
    if(premiumLoader) premiumLoader.style.display = 'block';
    if(allLoader) allLoader.style.display = 'block';

    try {
        if (PREMIUM_CSV_URL.includes("MOCK_URL")) {
            premiumDomains = MOCK_PREMIUM;
        } else {
            const premRes = await fetch(PREMIUM_CSV_URL);
            if(premRes.ok) {
                const csvData = await premRes.text();
                premiumDomains = parseCSV(csvData);
            } else {
                premiumDomains = MOCK_PREMIUM;
            }
        }
    } catch(err) {
        console.error("Failed to load Premium Domains:", err);
        premiumDomains = MOCK_PREMIUM;
    }

    try {
        if (ALL_CSV_URL.includes("MOCK_URL")) {
            allDomains = MOCK_ALL;
        } else {
            const allRes = await fetch(ALL_CSV_URL);
            if(allRes.ok) {
                const csvData = await allRes.text();
                allDomains = parseCSV(csvData);
            } else {
                allDomains = MOCK_ALL;
            }
        }
    } catch(err) {
        console.error("Failed to load All Domains:", err);
        allDomains = MOCK_ALL;
    }
    
    if(premiumLoader) premiumLoader.style.display = 'none';
    if(allLoader) allLoader.style.display = 'none';

    renderDomains(premiumDomains, 'premiumGrid', true);
    renderDomains(allDomains, 'allGrid', false);
}

/**
 * Search Functionality
 */
const handleSearch = debounce(function() {
    const query = document.getElementById('searchInput').value.toLowerCase().trim();
    
    if (!query) {
        renderDomains(premiumDomains, 'premiumGrid', true);
        renderDomains(allDomains, 'allGrid', false);
        renderDomains(MOCK_SOLD, 'soldGrid', false);
        return;
    }
    
    // Track search query (only if meaningful length)
    if (query.length >= 2 && typeof gtag === 'function') {
        gtag('event', 'search', { search_term: query });
    }
    
    const filteredPremium = premiumDomains.filter(d => 
        (d.title || d.domain || '').toLowerCase().includes(query) || 
        (d.description || d.price || '').toLowerCase().includes(query)
    );
    
    const filteredAll = allDomains.filter(d => 
        (d.title || d.domain || '').toLowerCase().includes(query) || 
        (d.description || d.price || '').toLowerCase().includes(query)
    );
    
    renderDomains(filteredPremium, 'premiumGrid', true);
    renderDomains(filteredAll, 'allGrid', false);
    
    // Render Recently Sold
    const filteredSold = MOCK_SOLD.filter(d => 
        (d.title || d.domain || '').toLowerCase().includes(query) || 
        (d.description || d.price || '').toLowerCase().includes(query)
    );
    renderDomains(filteredSold, 'soldGrid', false);
}, 300);

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    loadDomains();
    
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', handleSearch);
    }
    
    const searchBtn = document.getElementById('searchBtn');
    if (searchBtn) {
        searchBtn.addEventListener('click', function() {
            handleSearch();
            if (typeof gtag === 'function') {
                const q = document.getElementById('searchInput').value.trim();
                if (q) gtag('event', 'search_btn', { search_term: q });
            }
        });
    }

    // Mobile Menu Toggle
    const mobileMenu = document.getElementById('mobile-menu');
    const navLinks = document.querySelector('.nav-links');
    
    if (mobileMenu && navLinks) {
        mobileMenu.addEventListener('click', () => {
            mobileMenu.classList.toggle('is-active');
            navLinks.classList.toggle('active');
        });

        // Close menu when clicking a link
        navLinks.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                mobileMenu.classList.remove('is-active');
                navLinks.classList.remove('active');
            });
        });
    }
});
