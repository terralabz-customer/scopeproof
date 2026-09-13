"""A deliberately synthetic catalogue; these are not a freelancer's live offers."""

from copy import deepcopy

CATALOG_VERSION = "synthetic-2026-09-13.1"
CATALOG = {
    "landing": {
        "id": "landing", "name": "One-page static landing page", "currency": "USD", "base_price": 120,
        "description": "One static responsive page, up to five sections, using supplied copy and images.",
        "capabilities": {
            "one_page": "One static HTML/CSS page, up to five sections",
            "responsive": "Responsive layout for mobile and desktop",
            "supplied_assets": "Insert client-supplied final copy and images",
        },
        "exclusions": ["Login, payments, databases and booking systems", "Copywriting, domain purchase, hosting and deployment"],
        "deliverables": ["HTML and CSS source files", "Responsive layout checklist", "Local preview instructions"],
    },
    "node_api": {
        "id": "node_api", "name": "One Node.js API endpoint", "currency": "USD", "base_price": 90,
        "description": "One Node.js/Express JSON endpoint in a supplied repository, with no database or authentication.",
        "capabilities": {
            "one_endpoint": "One Node.js/Express JSON endpoint",
            "supplied_repository": "Use a client-supplied existing Node.js repository",
            "endpoint_contract": "Implement an explicitly supplied request and response contract",
        },
        "exclusions": ["Authentication, payments, databases and third-party APIs", "Hosting, deployment and additional endpoints"],
        "deliverables": ["Endpoint source code", "Request and response examples", "Endpoint test and local run instructions"],
    },
    "csv": {
        "id": "csv", "name": "Small CSV cleanup", "currency": "USD", "base_price": 60,
        "description": "One CSV with at most 10,000 rows: trim whitespace and remove exact duplicate rows, retaining the original.",
        "capabilities": {
            "one_file": "Clean one CSV file containing at most 10,000 rows",
            "trim": "Trim leading and trailing whitespace",
            "exact_duplicates": "Remove exact duplicate rows",
            "preserve_original": "Write a new output file and preserve the input",
        },
        "exclusions": ["Fuzzy matching, inferred corrections and enrichment", "Sensitive records, external APIs and production database changes"],
        "deliverables": ["Cleaned CSV as a new file", "Original retained unchanged", "Row-count and cleanup audit", "Repeatable cleanup script"],
    },
    "faq": {
        "id": "faq", "name": "Approved FAQ widget", "currency": "USD", "base_price": 110,
        "description": "One static FAQ widget using up to 20 client-approved question/answer pairs on one existing website.",
        "capabilities": {
            "one_widget": "One FAQ widget on one existing website",
            "approved_answers": "Display up to 20 client-approved question/answer pairs",
            "fallback": "Show a supplied contact link when no approved answer matches",
        },
        "exclusions": ["AI-generated answers, private document retrieval and account access", "CRM integrations, visitor tracking, hosting and API subscriptions"],
        "deliverables": ["FAQ widget source files", "Approved question/answer data", "Fallback behavior and integration instructions"],
    },
}


def get_catalog() -> dict:
    """Return an independent snapshot so a caller cannot mutate pricing policy."""
    return {"synthetic": True, "version": CATALOG_VERSION, "services": deepcopy(list(CATALOG.values()))}


EXAMPLES = [
    {
        "id": "clear-landing", "title": "A clear landing-page brief",
        "brief": "Build one static landing page with 4 sections. Make the layout responsive for mobile and desktop. I will supply the final copy and images.",
        "change_request": "",
    },
    {
        "id": "scope-creep", "title": "A small change with a big impact",
        "brief": "Build one static landing page with 4 sections. Make the layout responsive for mobile and desktop. I will supply the final copy and images.",
        "change_request": "Also add user login and a subscription checkout with Stripe payments.",
    },
    {
        "id": "csv-guardrails", "title": "Clean data without changing the original",
        "brief": "Clean one CSV file with 8,000 rows. Trim leading and trailing whitespace. Remove exact duplicate rows. Save a new output file and keep the original unchanged.",
        "change_request": "",
    },
]
