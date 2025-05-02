"""Main entry point for the OSINT system."""
import sys
import argparse
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.config import logger
from src.utils.logging_utils import setup_logger


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="OSINT Intelligence System")
    
    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Set up the system")
    
    # Collect command
    collect_parser = subparsers.add_parser("collect", help="Collect data")
    collect_parser.add_argument("--source", required=True, help="Source to collect from")
    
    # Query command
    query_parser = subparsers.add_parser("query", help="Query the system")
    query_parser.add_argument("--query", required=True, help="Query to run")
    
    return parser.parse_args()


def main():
    """Main entry point."""
    # Set up logger
    setup_logger("osint_system", "logs/osint_system.log")
    
    # Parse arguments
    args = parse_arguments()
    
    logger.info(f"Starting OSINT system with command: {args.command}")
    
    # Handle commands
    if args.command == "setup":
        logger.info("Setting up the system")
        # TODO: Implement setup command
        
    elif args.command == "collect":
        logger.info(f"Collecting data from {args.source}")
        # TODO: Implement collect command
        
    elif args.command == "query":
        logger.info(f"Running query: {args.query}")
        # TODO: Implement query command
        
    else:
        logger.error(f"Unknown command: {args.command}")
        print("Unknown command. Run with --help for usage information.")
        return 1
    
    logger.info("OSINT system finished successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())

