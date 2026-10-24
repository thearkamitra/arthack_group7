import argparse
import os
import uvicorn
from .api import create_app

parser = argparse.ArgumentParser(
    description="Local Inner Landscape session coordinator"
)
parser.add_argument("--host", default="127.0.0.1")
parser.add_argument("--port", type=int, default=4173)
parser.add_argument(
    "--demo-lan",
    action="store_true",
    help="Allow synthetic-data LAN headset tests over HTTP",
)
parser.add_argument(
    "--enable-paid",
    action="store_true",
    help="Explicit opt-in after budget/test approval; permits paid voice/media requests",
)
args = parser.parse_args()
if args.host not in ("127.0.0.1", "localhost") and not args.demo_lan:
    parser.error("Non-loopback binding requires --demo-lan and synthetic data only")
if args.enable_paid:
    os.environ["INNER_LANDSCAPE_ENABLE_PAID"] = "1"
uvicorn.run(create_app(), host=args.host, port=args.port, access_log=False)
