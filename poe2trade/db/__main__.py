import argparse
from poe2trade.db.scrape_selenium_cat import main as scrape_selenium_main
from poe2trade.db.parse_cat import main as parse_main
from poe2trade.db.matrix_cat import main as matrix_main
from poe2trade.db.train_super_cat import main as train_super_main
from poe2trade.db.score_super_cat import main as score_super_main
from poe2trade.db.train_unsuper_cat import main as train_unsuper_main

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
    valid_actions = {"scrape_selenium", "parse", "matrix", "train_super", "score_super", "train_unsuper"}
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
        print('No actions found...')

    if not categories:
        print("No categories provided.")
        return

    # Run each action as requested.
    if "scrape_selenium" in actions_found:
        print(f"\nRunning scrape selenium for categories: {categories}")
        scrape_selenium_main(categories)

    if "parse" in actions_found:
        print(f"\nRunning parse for categories: {categories}")
        parse_main(categories)

    if "matrix" in actions_found:
        print(f"\nCreating feature matrix for categories: {categories}")
        matrix_main(categories)

    if "train_super" in actions_found:
        print(f"\nTraining supervised models for categories: {categories}")
        train_super_main(categories)

    if "score_super" in actions_found:
        print(f"\nScoring records using supervised models for categories: {categories}")
        score_super_main(categories)

    if "train_unsuper" in actions_found:
        print(f"\nTraining unsupervised models for categories: {categories}")
        train_unsuper_main(categories)

if __name__ == "__main__":
    main()
