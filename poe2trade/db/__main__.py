import argparse
from poe2trade.db.scrape_cat import main as scrape_main
from poe2trade.db.parse_cat import main as parse_main
from poe2trade.db.features_cat import main as features_main
from poe2trade.db.train_cat import main as train_main
from poe2trade.db.ml_cat import main as ml_main

def main():
    """
    Run poe2trade db pipeline with multiple actions.

    Example usage:
      python -m poe2trade.db scrape parse train ml Body_Armour Weapons
      python -m poe2trade.db trade ml Body_Armour
    """
    parser = argparse.ArgumentParser(
        description="Run poe2trade db pipeline: scrape, parse, features, train, ml (trade is an alias for ml)"
    )
    # All positional arguments are parsed; valid actions are those that appear in the known list.
    parser.add_argument(
        "actions", nargs="+", help="Actions to perform: scrape, parse, features, train, ml, trade"
    )
    # --model is ignored since all models are now run.
    parser.add_argument(
        "--model", type=str, default="all",
        help="(Ignored) All models are now run."
    )

    args = parser.parse_args()

    # "trade" is an alias for "ml"
    valid_actions = {"scrape", "parse", "features", "train", "ml", "trade"}
    actions_found = []
    categories = []

    # Process all positional arguments: if the arg is a valid action, record it; otherwise, treat it as a category.
    for arg in args.actions:
        arg_low = arg.lower()
        if arg_low in valid_actions:
            actions_found.append(arg_low)
        else:
            categories.append(arg)

    if not actions_found:
        # If no actions are provided, set defaults.
        actions_found = ["scrape", "parse"]

    if not categories:
        print("No categories provided.")
        return

    # Run each action as requested.
    if "scrape" in actions_found:
        print(f"Running scrape for categories: {categories}")
        scrape_main(categories)

    if "parse" in actions_found:
        print(f"\nRunning parse for categories: {categories}")
        parse_main(categories)

    if "features" in actions_found:
        print(f"\nRunning feature extraction for categories: {categories}")
        features_main(categories)

    if "train" in actions_found:
        print(f"\nTraining models for categories: {categories}")
        train_main(categories)

    # "ml" and "trade" both trigger the same function: ml_main
    if "ml" in actions_found or "trade" in actions_found:
        print(f"\nRunning ML predictions for categories: {categories}")
        ml_main(categories)

if __name__ == "__main__":
    main()
