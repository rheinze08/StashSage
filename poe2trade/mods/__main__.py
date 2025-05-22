import sys
from poe2trade.mods.scrape_mods import main as scrape_mods
from poe2trade.mods.update_mods import main as update_mods

def main():
    args = sys.argv[1:]
    # If no arguments provided, run both functions
    if not args:
        args = ['scrape', 'update']

    if 'scrape' in args:
        print("Running get_mods_trade...")
        scrape_mods()

    if 'update' in args:
        print("\nRunning update_mods_trade...")
        update_mods()

if __name__ == "__main__":
    main()
