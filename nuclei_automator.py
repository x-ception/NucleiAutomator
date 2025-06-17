import os
import subprocess
import time
import argparse
from datetime import datetime

# ========== CONFIG ==========
NUCLEI_TEMPLATES = "/path/to/nuclei-templates/"
DISCORD_WEBHOOK = "YOUR_DISCORD_WEBHOOK"
DELAY_BETWEEN_PHASES = 30  # Seconds
NUCLEI_BINARY = "nuclei"
OUTPUT_BASE = f"output/scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
os.makedirs(OUTPUT_BASE, exist_ok=True)

# ========== UTILS ==========

def notify_discord(message):
    if not DISCORD_WEBHOOK.strip():
        return
    try:
        import requests
        requests.post(DISCORD_WEBHOOK, json={"content": message})
    except Exception as e:
        print(f"[!] Discord Error: {e}")

def run_nuclei_severity(input_file, severity, outfile):
    print(f"\n[+] Running Nuclei - Severity: {severity}")
    cmd = (
        f"{NUCLEI_BINARY} -l {input_file} -t {NUCLEI_TEMPLATES} "
        f"-s {severity} -c 25 -rl 100 -retries 1 "
        f"-o {outfile} -silent"
    )
    try:
        subprocess.run(cmd, shell=True, check=True)
        notify_discord(f"✅ Nuclei phase `{severity}` completed. Check: `{outfile}`")
    except subprocess.CalledProcessError as e:
        print(f"[!] Nuclei error in {severity}: {e}")
        notify_discord(f"❌ Nuclei scan failed in phase `{severity}`")

def run_nuclei_tags(input_file, tags, outfile):
    print(f"\n[+] Running Nuclei - Tags: {tags}")
    cmd = (
        f"{NUCLEI_BINARY} -l {input_file} -t {NUCLEI_TEMPLATES} "
        f"-tags {tags} -c 25 -rl 100 -retries 1 "
        f"-o {outfile} -silent"
    )
    try:
        subprocess.run(cmd, shell=True, check=True)
        notify_discord(f"✅ Nuclei tag-based phase `{tags}` completed. Check: `{outfile}`")
    except subprocess.CalledProcessError as e:
        print(f"[!] Nuclei tag scan error: {e}")
        notify_discord(f"❌ Nuclei tag scan failed for `{tags}`")

def generate_html_report():
    html_path = os.path.join(OUTPUT_BASE, "report.html")
    with open(html_path, "w") as html:
        html.write("<html><head><title>Nuclei Report</title></head><body>")
        html.write(f"<h1>Nuclei Scan Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</h1>")

        for label, file in {
            "INFO": "info.txt",
            "LOW": "low.txt",
            "MEDIUM + HIGH": "medium_high.txt",
            "CRITICAL": "critical.txt",
            "TAGGED (rce,sqli,xss...)": "tagged.txt"
        }.items():
            full_path = os.path.join(OUTPUT_BASE, file)
            if os.path.exists(full_path):
                html.write(f"<h2>{label}</h2><pre>")
                with open(full_path, "r") as f:
                    html.write(f.read())
                html.write("</pre>")

        html.write("</body></html>")
    print(f"[+] HTML report generated: {html_path}")
    notify_discord("📝 Nuclei report is ready (HTML generated)")

# ========== MAIN ==========

def main():
    parser = argparse.ArgumentParser(description="Nuclei Automator - Automatically run phased Nuclei scans")
    parser.add_argument("-u", "--url", help="Single target URL")
    parser.add_argument("-l", "--list", help="File containing list of target URLs (http/https)")
    args = parser.parse_args()

    if not args.url and not args.list:
        parser.print_help()
        return

    input_file = os.path.join(OUTPUT_BASE, "targets.txt")

    # Save single URL or copy list
    if args.url:
        with open(input_file, "w") as f:
            f.write(args.url.strip() + "\n")
    elif args.list:
        if not os.path.isfile(args.list):
            print(f"[!] File not found: {args.list}")
            return
        subprocess.run(f"cp {args.list} {input_file}", shell=True)

    print(f"\n📌 Targets saved in: {input_file}")
    print(f"📁 Output will be saved in: {OUTPUT_BASE}")
    notify_discord("🚀 NucleiAutomator scan started!")

    # Severity-based scans
    run_nuclei_severity(input_file, "info", os.path.join(OUTPUT_BASE, "info.txt"))
    time.sleep(DELAY_BETWEEN_PHASES)

    run_nuclei_severity(input_file, "low", os.path.join(OUTPUT_BASE, "low.txt"))
    time.sleep(DELAY_BETWEEN_PHASES)

    run_nuclei_severity(input_file, "medium,high", os.path.join(OUTPUT_BASE, "medium_high.txt"))
    time.sleep(DELAY_BETWEEN_PHASES)

    run_nuclei_severity(input_file, "critical", os.path.join(OUTPUT_BASE, "critical.txt"))
    time.sleep(DELAY_BETWEEN_PHASES)

    # Tag-based scan
    run_nuclei_tags(input_file, "rce,sqli,xss,ssrf,lfi,auth", os.path.join(OUTPUT_BASE, "tagged.txt"))

    generate_html_report()
    print("\n🎯 Scan completed.")

if __name__ == "__main__":
    main()
