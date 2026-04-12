# DEPRECATED: Unified into osiris_cli.py
# This file is now an alias and should not be used as an entry point.

import asyncio
import sys
import logging
import argparse
from pathlib import Path

# Setup paths
SCRIPT_DIR = Path(__file__).parent.resolve()
SDK_PATH = SCRIPT_DIR / "copilot-sdk-dnalang" / "src"

if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("osiris_chat")

try:
    from dnalang_sdk.chat_system.orchestrator import create_chat_orchestrator
except ImportError as e:
    logger.error(f"Failed to import OSIRIS chat system: {e}")
    logger.error(f"SDK path: {SDK_PATH}")
    sys.exit(1)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="OSIRIS Chat Interface — Intelligent Chatbot-Driven System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python osiris_chat.py                 # Start interactive chat
  python osiris_chat.py --no-tui        # Plain text mode
  python osiris_chat.py --no-agents     # Disable agent swarm
  
Chat naturally, no command syntax needed. Type [?] for help, [q] to quit.
        """
    )
    
    parser.add_argument(
        "--no-tui",
        action="store_true",
        help="Disable rich TUI (plain text mode)"
    )
    
    parser.add_argument(
        "--no-agents",
        action="store_true",
        help="Disable agent swarm parallel execution"
    )
    
    parser.add_argument(
        "--state-dir",
        type=str,
        help="Custom state directory"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    # Adjust logging
    if args.debug:
        logging.getLogger("dnalang_sdk").setLevel(logging.DEBUG)
        logging.getLogger("osiris_chat").setLevel(logging.DEBUG)
    
    # Create orchestrator
    logger.info("Initializing OSIRIS Chat System...")
    
    try:
        orchestrator = create_chat_orchestrator(
            state_dir=Path(args.state_dir) if args.state_dir else None,
            enable_tui=not args.no_tui,
            enable_agents=not args.no_agents,
        )
    except Exception as e:
        logger.error(f"Failed to create orchestrator: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    logger.info("OSIRIS Chat System initialized successfully")
    
    # Run interactive session
    try:
        asyncio.run(orchestrator.interactive_session())
    except Exception as e:
        logger.error(f"Error during session: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    finally:
        # Print session summary
        summary = orchestrator.get_session_summary()
        logger.info(f"Session Summary: {summary}")
        print("\n✓ OSIRIS Session Complete")
        print(f"  Interactions: {summary['interactions']}")
        print(f"  Duration: {summary['duration_seconds']:.1f}s")
        if summary['agent_reports'] > 0:
            print(f"  Agent Reports: {summary['agent_reports']}")


if __name__ == "__main__":
    main()
