import os
import re
import argparse
from dotenv import load_dotenv
import yaml
from mcrcon import MCRcon

load_dotenv()
HOST = os.getenv("RCON_HOST")
PORT = int(os.getenv("RCON_PORT"))
PASSWORD = os.getenv("RCON_PASSWORD")

with open("config/settings.yaml") as f:
    settings = yaml.safe_load(f)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        tps = 20.0
        online_players = 0
    else:
        with MCRcon(HOST, PASSWORD, port=PORT) as mcr:
            response = mcr.command("/tps")
            cleaned = re.sub(r'§.', '', response)
            values = re.findall(r'[\d.]+', cleaned)
            tps = float(values[3])

            response = mcr.command("/list")
            match = re.search(r'There are (\d+)', response)
            online_players = int(match.group(1))
    print(tps)
    print(online_players)

if __name__ == '__main__':
    main()
