import os
import subprocess
import time
import argparse
from datetime import datetime

# ========== CONFIG ==========
NUCLEI_TEMPLATES = "/home/exploiter/nuclei-templates/"
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1379480233228505199/h6dOJBqlhq25wDi4jw9tFueqMiwx9szPEoYbVooje9rMO47CWsLKltU2Uux2NsOJzoLX"  # Add if needed
DELAY_BETWEEN_PHASES = 30  # Seconds
NUCLEI_BINARY = "nuclei" # Change if in different path
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

def run_nuclei(input_file, severity, tags, outfile):
    print(f"\n[+] Running Nuclei for severity: {severity} ({tags})")
    cmd = (
        f"{NUCLEI_BINARY} -l {input_file} -t {NUCLEI_TEMPLATES} "
        f"-s {severity} -tags {tags} -c 25 -rl 100 -retries 1 "
        f"-o {outfile} -silent"
    )
    try:
        subprocess.run(cmd, shell=True, check=True)
        notify_discord(f"✅ Nuclei phase `{severity}` completed. Check: `{outfile}`")
    except subprocess.CalledProcessError as e:
        print(f"[!] Nuclei error in {severity}: {e}")
        notify_discord(f"❌ Nuclei scan failed in phase `{severity}`")

def generate_html_report():
    html_path = os.path.join(OUTPUT_BASE, "report.html")
    with open(html_path, "w") as html:
        html.write("<html><head><title>Nuclei Report</title></head><body>")
        html.write(f"<h1>Nuclei Scan Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</h1>")
        for sev in ["info", "low", "medium_high_critical"]:
            file = os.path.join(OUTPUT_BASE, f"{sev}.txt")
            if os.path.exists(file):
                html.write(f"<h2>{sev.upper()} Results</h2><pre>")
                with open(file, "r") as f:
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

    # Phased Nuclei Scanning
    run_nuclei(input_file, "info", "exposure,disclosure", os.path.join(OUTPUT_BASE, "info.txt"))
    time.sleep(DELAY_BETWEEN_PHASES)
    run_nuclei(input_file, "low", "low-hanging", os.path.join(OUTPUT_BASE, "low.txt"))
    time.sleep(DELAY_BETWEEN_PHASES)
    run_nuclei(input_file, "medium,high,critical", "rce,sqli,xss,ssrf,lfi,auth", os.path.join(OUTPUT_BASE, "medium_high_critical.txt"))

    generate_html_report()
    print("\n🎯 Scan completed.")

if __name__ == "__main__":
    main()
