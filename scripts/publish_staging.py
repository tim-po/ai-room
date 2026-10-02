"""Route only the authorized staging hostname; retain a private rollback snapshot.
Uses operator Cloudflare configuration; never prints API credentials or tunnel config.
"""
import json
from pathlib import Path
import tomllib
import urllib.request

config = tomllib.loads(Path('/home/claude/bot-swarm/config/secrets.toml').read_text())['cloudflare']
url = f"https://api.cloudflare.com/client/v4/accounts/{config['account_id']}/cfd_tunnel/{config['tunnel_id']}/configurations"

def api(method='GET', data=None):
    request = urllib.request.Request(url, method=method,
        data=json.dumps(data).encode() if data is not None else None,
        headers={'Authorization': 'Bearer '+config['api_token'], 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    if not result['success']:
        raise RuntimeError('Staging route update failed')
    return result['result']['config']

before = api()
backup = Path('instance/tunnel-pre-platform.json')
if not backup.exists():
    backup.write_text(json.dumps(before))
    backup.chmod(0o600)
matching = [rule for rule in before['ingress'] if rule.get('hostname') == 'airoom.nolimlabs.uk']
assert len(matching) == 1, 'Expected one existing dedicated staging hostname'
matching[0]['service'] = 'http://127.0.0.1:8098'
after = api('PUT', {'config': before})
assert after == before
print('Dedicated staging hostname routes to port 8098; other ingress rules unchanged.')
