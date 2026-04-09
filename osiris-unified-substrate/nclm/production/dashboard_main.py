"""Launch dashboard: python -m nclm.production.dashboard [--port 8411]"""
import argparse
from .dashboard import run_dashboard

def main():
    parser = argparse.ArgumentParser(description="OSIRIS NCLM Dashboard")
    parser.add_argument("--port", type=int, default=8411, help="HTTP port")
    parser.add_argument("--root", default=None, help="Project root directory")
    args = parser.parse_args()
    run_dashboard(port=args.port, root=args.root)

if __name__ == "__main__":
    main()
