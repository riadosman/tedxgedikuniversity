"""Generate independent deployment keys into an ignored file; never print secrets."""

import argparse
from pathlib import Path
import secrets
from urllib.parse import urlsplit

from cryptography.fernet import Fernet


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True, help="Hostname only, without https://")
    parser.add_argument("--output", default="../.local/vercel-production.env")
    args = parser.parse_args()
    domain = args.domain.strip()
    parsed = urlsplit("https://" + domain)
    if parsed.netloc != domain or parsed.path or parsed.username or parsed.port or "*" in domain:
        parser.error("Use a hostname only.")
    target = Path(args.output).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    template = (Path(__file__).resolve().parents[1] / ".env.vercel.example").read_text(encoding="utf-8")
    template = template.replace("REPLACE_WITH_GENERATED_SECRET", secrets.token_urlsafe(64))
    template = template.replace("REPLACE_WITH_GENERATED_FERNET_KEY", Fernet.generate_key().decode())
    template = template.replace("YOUR-PROJECT.vercel.app", domain)
    with target.open("x", encoding="utf-8") as output:
        output.write(template)
    print(f"Created {target}. Add your Neon DATABASE_URL and confirm the domain before use.")
    print("Keep this file private. Existing files and existing deployment keys are never overwritten.")


if __name__ == "__main__":
    main()
