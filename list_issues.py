import urllib.request, json, os

req = urllib.request.Request("https://api.github.com/repos/evolveer/manufacturing_emulator/issues?state=all&per_page=100")
req.add_header("Authorization", f"Bearer {os.environ['GH_TOKEN']}")
req.add_header("Accept", "application/vnd.github+json")
req.add_header("X-GitHub-Api-Version", "2022-11-28")

try:
    with urllib.request.urlopen(req) as response:
        issues = json.loads(response.read().decode())
        print(f"Total issues: {len(issues)}")
        for issue in issues:
            print(f"- #{issue['number']}: {issue['title']}")
except Exception as e:
    print(f"Error: {e}")
