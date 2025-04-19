import re
import pandas as pd

def parse_mod(mod_str: str) -> (str, float, float, bool, int, int, int):
    """
    Normalize a mod string and extract its numeric range, along with eligibility for multiplicity,
    and determine which defensive stats are affected (Armour, Evasion, Energy Shield).

    The function performs three tasks:
      1. Normalizes the mod string by:
         - Converting to lowercase.
         - Stripping whitespace.
         - Removing any leading '+'.
         - Replacing all digits (and decimals) with '#' characters.
      2. Extracts numeric tokens from the original mod string to determine a range:
         - If only a single number is present, then min_value and max_value are both that number.
         - If a single range (e.g., 4-7) is present, then min_value is set to the lower bound (4)
           and max_value is set to the upper bound (7).
         - If two ranges are present (e.g., "between (4-7) and (6-10)"), then min_value is the
           lower bound of the first range (4) and max_value is the upper bound of the second range (10).
         - If no numeric tokens are found, both min_value and max_value default to 1.0.
         - Additionally, if a dash-defined range is detected (e.g., "2-5"), the mod is considered
           ineligible for multiplicity calculations; otherwise, it is eligible.
      3. Determines whether the mod affects Armour, Evasion, or Energy Shield by keyword analysis.

    Parameters
    ----------
    mod_str : str
        The raw mod string.

    Returns
    -------
    tuple of (str, float, float, bool, int, int, int)
        A tuple containing:
          - The normalized mod pattern.
          - The min_value.
          - The max_value.
          - A boolean indicating if the mod is eligible for multiplicity calculations.
          - An integer (1 or 0) indicating if the mod affects Armour.
          - An integer (1 or 0) indicating if the mod affects Evasion.
          - An integer (1 or 0) indicating if the mod affects Energy Shield.
    """
    # Normalize the mod string
    pattern = mod_str.lower().strip()
    pattern = re.sub(r"^\+(\s*)", "", pattern)
    pattern = re.sub(r"\d+(\.\d+)?", "#", pattern)
    pattern = pattern.strip()

    # Check for explicit numeric range using a dash (e.g., "2-5")
    range_matches = re.findall(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)', mod_str)
    if range_matches:
        eligible_for_multiplicity = False
        if len(range_matches) == 1:
            min_value = float(range_matches[0][0])
            max_value = float(range_matches[0][1])
        else:
            # For two (or more) ranges, use the first lower bound and the last upper bound.
            min_value = float(range_matches[0][0])
            max_value = float(range_matches[-1][1])
    else:
        eligible_for_multiplicity = True
        # Extract individual numeric tokens if no dash range pattern is found.
        tokens = re.findall(r'(\d+(?:\.\d+)?)', mod_str)
        if tokens:
            if len(tokens) == 1:
                min_value = max_value = float(tokens[0])
            else:
                # Use the first token as the min and the last as the max.
                min_value = float(tokens[0])
                max_value = float(tokens[-1])
        else:
            min_value = max_value = 1.0

    # Determine if the mod affects Armour, Evasion, or Energy Shield
    mod_lower = mod_str.lower()
    affects_armour = 1 if "armour" in mod_lower else 0
    affects_evasion = 1 if "evasion" in mod_lower else 0
    affects_energy_shield = 1 if "energy shield" in mod_lower else 0

    return pattern, min_value, max_value, eligible_for_multiplicity, affects_armour, affects_evasion, affects_energy_shield


def compare_mods(base_mod: str, compare_mod: str):
    """
    Compare two mod strings and determine if the base_mod is a valid multiple of the compare_mod.

    To succeed the following conditions must be met:
      - Both mods must have the same normalized pattern.
      - Both mods must have the same eligibility for multiplicity.
      - The base_mod's min value must be greater than or equal to the compare_mod's min value,
        and the base_mod's max value must be less than or equal to the compare_mod's max value.
      
    If these conditions are met and the mods are eligible for multiplicity calculations,
    the function calculates the number of multiples by dividing the base_mod's numeric value
    (its min value is used as the representative) by that of the compare_mod. If the division
    does not yield an exact multiple (within a negligible tolerance), the match fails.
    
    Parameters
    ----------
    base_mod : str
        The mod string to be compared (the "base" mod).
    compare_mod : str
        The mod string to compare against.
    
    Returns
    -------
    tuple(bool, int or None)
        - (False, None) if any condition fails.
        - (True, multiples) if the mods match and, when eligible for multiplicity,
          multiples is the number of times the compare_mod fits into the base_mod.
          If not eligible for multiplicity, multiples is returned as None.
    """
    (base_pattern, base_min, base_max, base_multi,
     base_armour, base_evasion, base_es) = parse_mod(base_mod)
    (cmp_pattern, cmp_min, cmp_max, cmp_multi,
     cmp_armour, cmp_evasion, cmp_es) = parse_mod(compare_mod)

    # Check if normalized patterns match.
    if base_pattern != cmp_pattern:
        return (False, None)

    # Check if both mods share the same multiplicity eligibility.
    if base_multi != cmp_multi:
        return (False, None)

    # Check that base_mod's numeric range is within compare_mod's range.
    if base_min <= cmp_min or base_max >= cmp_max:
        return (False, None)

    # If eligible for multiplicity, calculate the number of multiples.
    if base_multi:
        # Ensure the base_mod's numeric value is an exact multiple of compare_mod's value.
        if abs(base_min % cmp_min) > 1e-9:
            return (False, None)
        multiples = int(round(base_min / cmp_min))
        return (True, multiples)

    # For mods not eligible for multiplicity, a successful match returns True with no multiple calculation.
    return (True, None)
