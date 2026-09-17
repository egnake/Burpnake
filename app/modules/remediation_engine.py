"""
Remediation & Taxonomy Engine
Maps vulnerabilities to CWE IDs, OWASP Top 10 (2021) categories, and language-specific secure code remediation patterns.
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional, List

@dataclass
class RemediationBlueprint:
    cwe_id: str
    cwe_name: str
    cwe_url: str
    owasp_category: str
    guidance: str
    code_examples: Dict[str, str]

REMEDIATION_DATABASE: Dict[str, RemediationBlueprint] = {
    "sqli": RemediationBlueprint(
        cwe_id="CWE-89",
        cwe_name="Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')",
        cwe_url="https://cwe.mitre.org/data/definitions/89.html",
        owasp_category="A03:2021 - Injection",
        guidance="Use parameterized queries (prepared statements) or an established Object-Relational Mapper (ORM). Never concatenate untrusted user input directly into SQL strings.",
        code_examples={
            "python": "# Python (sqlite3 / psycopg2)\ncursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))",
            "node": "// Node.js (pg / mysql2)\nconst result = await db.query('SELECT * FROM users WHERE id = $1', [userId]);",
            "java": "// Java (PreparedStatement)\nPreparedStatement stmt = conn.prepareStatement('SELECT * FROM users WHERE id = ?');\nstmt.setString(1, userId);",
            "go": "// Go (database/sql)\nrow := db.QueryRow('SELECT * FROM users WHERE id = $1', userId)",
        }
    ),
    "xss": RemediationBlueprint(
        cwe_id="CWE-79",
        cwe_name="Improper Neutralization of Input During Web Page Generation ('Cross-site Scripting')",
        cwe_url="https://cwe.mitre.org/data/definitions/79.html",
        owasp_category="A03:2021 - Injection",
        guidance="Contextually encode all user-supplied data before rendering it in the DOM. Utilize Content-Security-Policy (CSP) with strict nonce directives.",
        code_examples={
            "python": "# Python (Flask / Jinja2 auto-escapes by default)\n# In templates: {{ user_input | e }}\n# With HTML Sanitization:\nimport bleach\nclean_html = bleach.clean(raw_html, tags=['b', 'i', 'u'])",
            "node": "// Node.js (DOMPurify)\nimport DOMPurify from 'isomorphic-dompurify';\nconst clean = DOMPurify.sanitize(userProvidedHtml);",
            "java": "// Java (OWASP Java Encoder)\nString safeHtml = Encode.forHtml(userProvidedText);",
            "go": "// Go (html/template auto-escapes)\ntmpl.Execute(w, data)",
        }
    ),
    "idor": RemediationBlueprint(
        cwe_id="CWE-639",
        cwe_name="Authorization Bypass Through User-Controlled Key",
        cwe_url="https://cwe.mitre.org/data/definitions/639.html",
        owasp_category="A01:2021 - Broken Access Control",
        guidance="Enforce authorization checks on every request verifying that the authenticated user owns or has explicit permission to access the requested resource. Prefer cryptographically secure random UUIDs over predictable sequential IDs.",
        code_examples={
            "python": "# Python (FastAPI / Django)\ndef get_document(doc_id: str, current_user: User = Depends(get_current_user)):\n    doc = db.query(Document).filter(Document.id == doc_id, Document.owner_id == current_user.id).first()\n    if not doc:\n        raise HTTPException(status_code=404, detail='Not found')",
            "node": "// Node.js (Express)\nconst document = await Document.findOne({ _id: req.params.id, ownerId: req.user.id });\nif (!document) return res.status(404).json({ error: 'Resource not found' });",
            "java": "// Java (Spring Security)\n@PreAuthorize('#document.ownerId == authentication.principal.id')\npublic Document getDocument(@P('document') Document document) { return document; }",
            "go": "// Go\nerr := db.QueryRow('SELECT * FROM documents WHERE id = $1 AND owner_id = $2', docID, userID).Scan(&doc)",
        }
    ),
    "ssrf": RemediationBlueprint(
        cwe_id="CWE-918",
        cwe_name="Server-Side Request Forgery (SSRF)",
        cwe_url="https://cwe.mitre.org/data/definitions/918.html",
        owasp_category="A10:2021 - Server-Side Request Forgery (SSRF)",
        guidance="Validate and sanitize user-supplied URLs against an allowlist of approved domains and protocols. Resolve domain names to IP addresses and verify they do not fall within private/loopback/cloud-metadata ranges (e.g., 127.0.0.0/8, 10.0.0.0/8, 169.254.169.254).",
        code_examples={
            "python": "# Python (ipaddress validation)\nimport socket, ipaddress\nip = socket.gethostbyname(target_host)\nif ipaddress.ip_address(ip).is_private or ipaddress.ip_address(ip).is_loopback:\n    raise ValueError('Forbidden destination IP')",
            "node": "// Node.js\nconst isPrivateIp = require('private-ip');\nif (isPrivateIp(resolvedIp)) throw new Error('Restricted IP');",
            "java": "// Java\nInetAddress addr = InetAddress.getByName(host);\nif (addr.isSiteLocalAddress() || addr.isLoopbackAddress()) throw new SecurityException('SSRF blocked');",
            "go": "// Go\nip := net.ParseIP(host)\nif ip.IsPrivate() || ip.IsLoopback() { return errors.New('invalid IP') }",
        }
    ),
    "open_redirect": RemediationBlueprint(
        cwe_id="CWE-601",
        cwe_name="URL Redirection to Untrusted Site ('Open Redirect')",
        cwe_url="https://cwe.mitre.org/data/definitions/601.html",
        owasp_category="A01:2021 - Broken Access Control",
        guidance="Restrict redirection destinations using a strict allowlist of authorized hostnames or relative paths (starting with a single forward slash).",
        code_examples={
            "python": "# Python (urllib.parse)\nfrom urllib.parse import urlparse\nparsed = urlparse(redirect_url)\nif parsed.netloc and parsed.netloc not in ALLOWED_HOSTS:\n    redirect_url = '/dashboard'",
            "node": "// Node.js\nconst url = new URL(targetUrl, 'https://example.com');\nif (url.origin !== 'https://example.com') return res.redirect('/home');",
            "java": "// Java\nif (!ALLOWED_REDIRECTS.contains(targetUrl)) targetUrl = \"/home\";",
            "go": "// Go\nif !strings.HasPrefix(target, \"/\") || strings.HasPrefix(target, \"//\") { target = \"/\" }",
        }
    ),
}

class RemediationEngine:
    """Provides remediation blueprints and CWE mappings."""

    def get_blueprint(self, vuln_type: str) -> RemediationBlueprint:
        clean_type = vuln_type.lower().replace("-", "_").replace(" ", "_")
        for key, bp in REMEDIATION_DATABASE.items():
            if key in clean_type:
                return bp
        
        # Generic fallback
        return RemediationBlueprint(
            cwe_id="CWE-699",
            cwe_name="Software Development Vulnerability",
            cwe_url="https://cwe.mitre.org/data/definitions/699.html",
            owasp_category="A04:2021 - Insecure Design",
            guidance="Follow defense-in-depth principles: validate all inputs against strict schemas, enforce strict access controls, and use automated static and dynamic security testing in the CI/CD pipeline.",
            code_examples={}
        )

remediation_engine = RemediationEngine()
