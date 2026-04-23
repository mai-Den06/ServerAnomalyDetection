import os
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
            tps = mcr.command("/tps")
            online_players = mcr.command("/list")
            # [TODO] 正規表現
    print(tps) # §6TPS from last 1m, 5m, 15m: §a20.0§r, §a20.0§r, §a20.0
    print(online_players) # There are 0 of a max of 20 players online:

if __name__ == '__main__':
    main()
