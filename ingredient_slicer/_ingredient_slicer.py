# Authors: Angus Watters, Melissa Terry 

import re
from typing import List, Dict, Any, Union, Tuple
from fractions import Fraction
from html import unescape
import warnings

# package imports
from . import _utils
from . import _regex_patterns
from . import _constants
# # from ._regex_patterns import IngredientTools

# # local dev import statements
# from ingredient_slicer import _utils
# from ingredient_slicer import _regex_patterns
# from ingredient_slicer import _constants

class IngredientSlicer:
    """
    A class to parse recipe ingredients into a standard format.

    Args:
        ingredient (str): The ingredient to parse.
        debug (bool): Whether to print debug statements (default is False)
    """

    # regex = IngredientTools()

    def __init__(self, ingredient: str, debug = False):
        self.ingredient          = ingredient
        self._standardized_ingredient = ingredient
        
        self._food              = None 
        self._quantity          = None    # the best quantity found in the ingredient string
        
        self._unit              = None    # the best unit found in the ingredient string
        self._standardized_unit = None   # "standard units" are the commonplace names for the found units (i.e. the standard unit of "oz" is "ounce")
        
        # make member variables for seconday quantities and units
        self._secondary_quantity = None
        self._secondary_unit     = None
        self._standardized_secondary_unit = None

        self._densities           = {}

        self._gram_weight         = None
        self._min_gram_weight     = None
        self._max_gram_weight     = None

        # "prep" are words that describe the state of the ingredient (i.e. "chopped", "diced", "minced")
        self._prep                  = []

        # "size modifiers" are words that describe the size of the ingredient (i.e. "large", "small", "medium")
        self._size_modifiers        = [] 

        # "dimensions" are numbers and units that describe the dimensions of the ingredient (i.e. "1 inch", "2 ft", "2cm x 3cm")
        self._dimensions            = []

        self._is_required           = True    # default sets the ingredient as a required ingredient

        self._staged_ingredient      = None    # standardized ingredient but keeping the parenthesis content

        self._parenthesis_content = None  # content of the parenthesis removed from the ingredient string
        self._parenthesis_notes   = []

        self.debug = debug

        self._parse()

        self._parsed_ingredient = self.to_json()
    
    def _find_units(self, ingredient: str) -> List[str]:
        """
        Find units in the ingredient string.
        Args:
            ingredient (str): The ingredient string to parse.
        Returns:
            List[str]: A list of units found in the ingredient string.
        """

        # split the input string on whitespaces
        split_ingredient = ingredient.split()

        matched_units = [i for i in split_ingredient if i in _constants.UNITS]

        return matched_units
    
    def _find_and_remove_percentages(self) -> None:
        """
        Find and remove percentages from the ingredient string.
        """
        # ingredient = "1 cup of 2% heavy cream"
        
        for key, pattern in _regex_patterns.PCT_REGEX_MAP.items():
            pattern_iter = pattern.finditer(self._standardized_ingredient)
            offset = 0
            for match in pattern_iter:
                match_string = match.group()
                start, end = match.start(), match.end()
                modified_start = start + offset
                modified_end = end + offset

                replacement_str = ""

                # Construct the modified string with the replacement applied
                self._standardized_ingredient = self._standardized_ingredient[:modified_start] + str(replacement_str) + self._standardized_ingredient[modified_end:]
                offset += len(str(replacement_str)) - (end - start)
                
        return
    
    def _replace_number_followed_by_inch_symbol(self) -> None:

        self._standardized_ingredient = _utils._replace_number_followed_by_inch_symbol(self._standardized_ingredient)

        return 
    
    def _find_and_replace_fraction_words(self) -> None:
        """ Find and replace fraction words with their corresponding numerical values in the parsed ingredient."""

        for key, pattern in _regex_patterns.NUMBER_WITH_FRACTION_WORD_MAP.items():
            
            pattern_iter = pattern.finditer(self._standardized_ingredient)
            offset = 0

            for match in pattern_iter:
                # print(f"Got a fraction word match with key: {key}") if self.debug else None
                match_string = match.group(0)
                start, end = match.start(), match.end()
                modified_start = start + offset
                modified_end = end + offset

                match_string = match_string.replace("-", " ")
                split_match = match_string.split(" ")

                split_match = [i.strip() for i in split_match]

                number_word = split_match[0]
                fraction_word = split_match[1]

                fraction_value, decimal = _constants.FRACTION_WORDS[fraction_word.lower()]

                updated_value = str(float(number_word) * float(decimal))
                self._standardized_ingredient = self._standardized_ingredient[:modified_start] + str(updated_value) + self._standardized_ingredient[modified_end:]

                offset += len(str(updated_value)) - (end - start)

        return 

    def _find_and_replace_numbers_separated_by_add_numbers(self) -> None:
        """Find numbers separated by "and", "&", "plus", or "+" and replace the matched strings with their sum of the 2 number values
        Examples:
        "1 and 0.5" -> "1.5"
        "1 & 0.5" -> "1.5"
        "2 plus 0.66" -> "2.66"
        "2 + 0.66" -> "2.66"
        """
        add_pattern_iter = _regex_patterns.NUMBERS_SEPARATED_BY_ADD_SYMBOLS_GROUPS.finditer(self._standardized_ingredient)

        offset = 0

        for match in add_pattern_iter:
            match_string = match.group(0)
            start, end = match.start(), match.end()
            modified_start = start + offset
            modified_end = end + offset

            first_number = float(match.group(1).strip())
            second_number = float(match.group(2).strip())

            updated_value = f" {_utils._make_int_or_float_str(str(first_number + second_number))} "

            self._standardized_ingredient = self._standardized_ingredient[:modified_start] + str(updated_value) + self._standardized_ingredient[modified_end:]

            offset += len(updated_value) - (end - start)
    
        return

    def _find_and_replace_casual_quantities(self):

        self._standardized_ingredient = _utils._find_and_replace_casual_quantities(self._standardized_ingredient)

        return 
    
    def _drop_special_dashes(self) -> None:
        self._standardized_ingredient = self._standardized_ingredient.replace("—", "-").replace("–", "-").replace("~", "-")
        return

    def _find_and_replace_prefixed_number_words(self) -> None:
        """ Replace prefixed number words with their corresponding numerical values in the parsed ingredient 
        Strings like "twenty five" are replaced with "25", or "thirty-two" is replaced with "32"
        """

        self._standardized_ingredient = _utils._find_and_replace_prefixed_number_words(self._standardized_ingredient)
        
        return

    def _find_and_replace_number_words(self) -> None:
        """
        Replace number words with their corresponding numerical values in the parsed ingredient.
        """
        self._standardized_ingredient = _utils._find_and_replace_number_words(self._standardized_ingredient)
        
        return

    def _clean_hyphen_padded_substrings(self) -> None:
        """Find and remove hyphens around "to", "or", and "and" substrings in the parsed ingredient.
        For example, "1-to-3 cups of soup" becomes "1 to 3 cups of soup" and "1-or-2 cups of soup" becomes "1 or 2 cups of soup"
        """

        substrings_to_fix = ["to", "or", "and", "&"]
        
        for substring in substrings_to_fix:
            self._standardized_ingredient = _utils._find_and_remove_hyphens_around_substring(self._standardized_ingredient, substring)

    def _clean_html_and_unicode(self) -> None:
        """Unescape fractions from HTML code coded fractions to unicode fractions."""
        self._standardized_ingredient = _utils._clean_html_and_unicode(self._standardized_ingredient)

        return
    
    def _replace_unicode_fraction_slashes(self) -> None:
        """Replace unicode fraction slashes with standard slashes in the parsed ingredient."""

        # Replace unicode fraction slashes with standard slashes
        self._standardized_ingredient = self._standardized_ingredient.replace('\u2044', '/') # could use .replace('\u2044', '\u002F'), or just .replace("⁄", "/")
        
        return 
    
    def _replace_emojis(self) -> None:
        """Remove emojis from the ingredient string."""
        
        self._standardized_ingredient = _utils._remove_emojis(self._standardized_ingredient)

        return

    def _add_whitespace(self):
        # regex pattern to match consecutive sequences of letters or digits
        pattern = _regex_patterns.CONSECUTIVE_LETTERS_DIGITS        
        # pattern = re.compile(r'([a-zA-Z]+)(\d+)|(\d+)([a-zA-Z]+)')

        # replace consecutive sequences of letters or digits with whitespace-separated sequences
        self._standardized_ingredient = re.sub(pattern, r'\1 \2\3 \4', self._standardized_ingredient)
    
    def _convert_fractions_to_decimals(self) -> None:
        """
        Convert fractions in the parsed ingredient to their decimal equivalents.
        """
        self._standardized_ingredient = _utils._convert_fractions_to_decimals(self._standardized_ingredient)
        
        return
    
    def _force_ws_between_numbers_and_chars(self):
        
        """Forces spaces between numbers and units and between units and numbers.
        End result is a string with a space between numbers and units and between units and numbers.
        Examples:
        "1cup" becomes "1 cup"
        "cup1" becomes "cup 1" 
        and ultimately "1cup" becomes "1 - cup" and "cup1" becomes "cup - 1"
        """

        self._standardized_ingredient = _utils._force_ws_between_numbers_and_chars(self._standardized_ingredient)

        return 
    
    def _extract_dimensions(self) -> None:
        """
        Extract dimensions from the parsed ingredient.
        """

        self._standardized_ingredient, self._dimensions = _utils._extract_dimensions(self._standardized_ingredient)
        return

    def _average_ranges(self) -> None:
        """ Average all hyphen separated ranges of numbers in the parsed ingredient. """
        self._standardized_ingredient = _utils.avg_ranges(self._standardized_ingredient)
        return
    
    def _fix_ranges(self):
        """
        Fix ranges in the parsed ingredient.
        Given a parsed ingredient, this method will fix ranges of numbers that are separated by one or more hyphens, ranges of numbers that are preceded by "between" and followed by "and" or "&", and ranges that are separated by "to" or "or".
        Examples:
        - "1-2 oz" -> "1 - 2 oz"
        - "between 1 and 5" -> "1 - 5"
        - "1 to 5" -> "1 - 5"

        """

        # Update ranges of numbers that are separated by one or more hyphens
        self._standardized_ingredient = _utils._update_ranges(self._standardized_ingredient, _regex_patterns.QUANTITY_DASH_QUANTITY)

        # Update ranges of numbers that are preceded by "between" and followed by "and" or "&"
        self._standardized_ingredient = _utils._update_ranges(self._standardized_ingredient, _regex_patterns.BETWEEN_QUANTITY_AND_QUANTITY)

        # Update ranges that are separated by "to" 
        self._standardized_ingredient = _utils._update_ranges(self._standardized_ingredient, _regex_patterns.QUANTITY_TO_QUANTITY)
  
        # Update ranges that are separated by "or"
        self._standardized_ingredient = _utils._update_ranges(self._standardized_ingredient, _regex_patterns.QUANTITY_OR_QUANTITY)
 
        # check and merge any misleading ranges
        self._standardized_ingredient = _utils._merge_misleading_ranges(self._standardized_ingredient)

        return
    
    def _remove_repeat_units_in_ranges(self) -> None:
        
        self._standardized_ingredient = _utils._remove_repeat_units_in_ranges(self._standardized_ingredient)
        
        return
    
    def _remove_x_separators(self):
        """
        Remove "x" separators from the ingredient string and replace with whitespace
        Examples:
            >>> _removed_x_separators("1x2 cups")
            '1 2 cups'
            >>> _remove_x_separators("5 x cartons of eggs")
            "5   cartons of eggs"
        """

        def replace_x(match):
            return match.group().replace('x', ' ').replace('X', ' ')

        # Replace "x"/"X" separators with whitespace
        self._standardized_ingredient = _regex_patterns.X_AFTER_NUMBER.sub(replace_x, self._standardized_ingredient)

    def _merge_spaced_numbers(self, spaced_numbers: str) -> str:
        """ Add or multiply the numbers in a string separated by a space.
        If the second number is less than 1, then add the two numbers together, otherwise multiply them together.
        This was the most generic form of dealing with numbers seperated by spaces that i could come up with
        (i.e. 2 1/2 cups means 2.5 cups but in other contexts a number followed by a non fraction means to multiply the numbers 2 8 oz means 16 oz)
        Args:
            spaced_numbers (str): A string of numbers separated by a space.
        Returns:
            str: string containing the sum OR the product of the numbers in the string. 
        Examples:
            >>> _merge_spaced_numbers('2 0.5')
            '2.5'
            >>> _merge_spaced_numbers('2 8')
            '16'
        """

        # Get the numbers from the spaced seperated string
        split_numbers = re.findall(_regex_patterns.SPLIT_SPACED_NUMS, spaced_numbers)

        # If the second number is less than 1, then add the two numbers together, otherwise multiply them together
        # This was the most generic form of dealing with numbers seperated by spaces 
        # (i.e. 2 1/2 cups means 2.5 cups but in other contexts a number followed by a non fraction means to multiply the numbers 2 8 oz means 16 oz)
        try:
            merged_totals = [_utils._make_int_or_float_str(str(float(first) + float(second)) if float(second) < 1 else str(float(first) * float(second))) for first, second in split_numbers]
        except:
            warnings.warn(f"error while merging {split_numbers}...")
            merged_totals = [""]
        # # READABLE VERSION of above list comprehension: 
        # This is the above list comprehensions split out into 2 list comprehensions for readability
        # merged_totals = [float(first) + float(second) if float(second) < 1 else float(first) * float(second) for first, second in split_numbers]

        # return merged_totals
        return merged_totals[0] if merged_totals else ""

    def _which_merge_on_spaced_numbers(self, spaced_numbers: str) -> str:
        """ Inform whether to add or multiply the numbers in a string separated by a space.
        Args:
            spaced_numbers (str): A string of numbers separated by a space.
        Returns:
            str: string indicating whether to add or multiply the numbers in the string.
        """

        split_numbers = re.findall(_regex_patterns.SPLIT_SPACED_NUMS, spaced_numbers)
        # split_numbers = [("2", "1")]

        # If the second number is less than 1, then note the numbers should be "added", otherwise they should be "multiplied"
        # This was the most generic form of dealing with numbers seperated by spaces 
        # (i.e. 2 1/2 cups means 2.5 cups but in other contexts a number followed by a non fraction means
        #  to multiply the numbers 2 8 oz means 16 oz)
        try:
            add_or_multiply = ["add" if float(second) < 1 else "multiply" for first, second in split_numbers]
        except:
            warnings.warn(f"error while deciding whether to note '{split_numbers}' as numbers to 'add' or 'multiply'...")
            add_or_multiply = [""]

        return add_or_multiply[0] if add_or_multiply else ""
    
    def _merge_multi_nums(self) -> None:
        """
        Replace unicode and standard fractions with their decimal equivalents in the parsed ingredient (v2).
        Assumes that numeric values in string have been padded with a space between numbers and non numeric characters and
        that any fractions have been converted to their decimal equivalents.
        Args:
            ingredient (str): The ingredient string to parse.
        Returns:
            str: The parsed ingredient string with the numbers separated by a space merged into a single number (either added or multiplied).
        
        >>> _merge_multi_nums('2 0.5 cups of sugar')
        '2.5 cups of sugar'
        >>> _merge_multi_nums('1 0.5 pounds skinless, boneless chicken breasts, cut into 0.5 inch pieces')
        '1.5 pounds skinless, boneless chicken breasts, cut into 0.5 inch pieces'
        """

        # go the spaced numbers matches and get each spaced seperated numbers match AND 
        # try and get the units that follow them so we can correctly match each spaced number with its corresponding unit
        spaced_nums = []
        units = []

        # Create iterable of the matched spaced numbers to insert updated values into the original string
        spaced_matches = re.finditer(_regex_patterns.SPACE_SEP_NUMBERS, self._standardized_ingredient)
        # spaced_matches = re.finditer(regex_map.SPACE_SEP_NUMBERS, ingredient)

        # initialize offset and replacement index values for updating the ingredient string, 
        # these will be used to keep track of the position of the match in the string
        offset = 0
        replacement_index = 0

        # Update the ingredient string with the merged values
        for match in spaced_matches:
            # print(f"Ingredient string: {ingredient}")

            # Get the start and end positions of the match
            start, end = match.start(), match.end()

            # search for the first unit that comes after the spaced numbers
            unit_after_match = re.search(_regex_patterns.UNITS_PATTERN,  self._standardized_ingredient[end:])
            
            if unit_after_match:
                units.append(unit_after_match.group())

            # add the spaced number to the list
            spaced_nums.append(match.group())

            merged_quantity = self._merge_spaced_numbers(match.group())
            merge_operation = self._which_merge_on_spaced_numbers(match.group())

            modified_start = start + offset
            modified_end = end + offset

            self._standardized_ingredient = self._standardized_ingredient[:modified_start] + str(merged_quantity) + self._standardized_ingredient[modified_end:]

            # Update the offset for subsequent replacements
            offset += len(merged_quantity) - (end - start)
            replacement_index += 1

    def _replace_a_or_an_quantities(self) -> None:
        """
        Replace "a" or "an" with "1" in the parsed ingredient if no number is present in the ingredient string.
        """
        self._standardized_ingredient = _utils._replace_a_or_an_quantities(self._standardized_ingredient)
        return 
    
    def _drop_special_characters(self):

        # Drop unwanted periods and replace them with whitespace
        self._standardized_ingredient = self._standardized_ingredient.replace(".", " ")

    def _separate_dimensions(self) -> None:
        """
        Split the dimensions from the parsed ingredient.
        """
        # Split the dimensions from the ingredient
        self._standardized_ingredient, self._dimensions = _utils._separate_dimensions(self._standardized_ingredient)
        return

    def _separate_parenthesis(self):
        
        """Get the content of any parenthesis and store it for analysis later on, also remove those parenthesis from the ingredient.
        Updates the parenthesis_content and _reduced_ingredient variables
        """

        ingredient_without_parenthesis, parenthesis = _utils._split_by_parenthesis(self._standardized_ingredient)

        self._staged_ingredient       = self._standardized_ingredient
        self._standardized_ingredient = ingredient_without_parenthesis # TODO: TESTING THIS OUT
        self._parenthesis_content     = parenthesis
    
    def _standardize(self):
        
        # define a list containing the class methods that should be called in order on the input ingredient string
        methods = [
            self._drop_special_dashes,
            self._find_and_remove_percentages,
            self._replace_number_followed_by_inch_symbol,
            self._find_and_replace_casual_quantities,
            self._find_and_replace_prefixed_number_words, 
            self._find_and_replace_number_words,
            self._find_and_replace_fraction_words, 
            self._clean_html_and_unicode,
            self._replace_unicode_fraction_slashes,
            self._replace_emojis,
            self._convert_fractions_to_decimals,
            self._force_ws_between_numbers_and_chars,
            self._remove_repeat_units_in_ranges,
            self._separate_dimensions,
            self._remove_x_separators,
            self._clean_hyphen_padded_substrings, # TODO: Still needs tests written for this
            self._merge_multi_nums,
            self._fix_ranges,  # TODO: NEW place for fix_ranges() (THIS MIGHT BREAK THINGS) ---> need to decide where this should go
            self._find_and_replace_numbers_separated_by_add_numbers, 
            self._replace_a_or_an_quantities,
            self._average_ranges,
            self._separate_parenthesis
        ]
        
        # call each method in the list on the input ingredient string
        for method in methods:
            method()

        self._standardized_ingredient = _utils._remove_extra_whitespaces(self._standardized_ingredient)

        return

    def extract_first_quantity_unit(self) -> None:

        """
        Extract the first unit and quantity from an ingredient string.
        Function will extract the first unit and quantity from the ingredient string and set the self._quantity and self._unit member variables.
        Quantities and ingredients are extracted in this order and if any of the previous steps are successful, the function will return early.
        1. Check for basic units (e.g. 1 cup, 2 tablespoons)
        2. Check for nonbasic units (e.g. 1 fillet, 2 carrot sticks)
        3. Check for quantity only, no units (e.g. 1, 2)

        If none of the above steps are successful, then the self._quantity and self._unit member variables will be set to None.

        Args:
            ingredient (str): The ingredient string to parse.
        Returns:
            dict: A dictionary containing the first unit and quantity found in the ingredient string.
        Examples:
            >>> extract_first_unit_quantity('1 1/2 cups diced tomatoes, 2 tablespoons of sugar, 1 stick of butter')
            {'quantity': '1 1/2', 'unit': 'cups'}
            >>> extract_first_unit_quantity('2 1/2 cups of sugar')
            {'quantity': '2 1/2', 'unit': 'cups'}
        """
        
        # ---- STEP 1: CHECK FOR QUANTITY - BASIC UNITS (e.g. 1 cup, 2 tablespoons) ----
        # Example: "1.5 cup of sugar" -> quantity: "1.5", unit: "cup"

        # get the first number followed by a basic unit in the ingredient string
        basic_unit_matches = _regex_patterns.QUANTITY_BASIC_UNIT_GROUPS.findall(self._standardized_ingredient) # TODO: testing

        # remove any empty matches
        valid_basic_units = [i for i in basic_unit_matches if len(i) > 0]

        # debugging message
        basic_units_message = f"Valid basic units: {valid_basic_units}" if valid_basic_units else f"No valid basic units found..."

        # if we have valid single number quantities, then set the self._quantity and the self._unit member variables and exit the function
        if basic_unit_matches and valid_basic_units:
            self._quantity = valid_basic_units[0][0].strip()
            self._unit = valid_basic_units[0][1].strip()
            return 

        # ---- STEP 2: CHECK FOR QUANTITY - NONBASIC UNITS (e.g. 1 fillet, 2 carrot sticks) ----
        # Example: "1 fillet of salmon" -> quantity: "1", unit: "fillet"

        # If no basic units are found, then check for anumber followed by a nonbasic units
        nonbasic_unit_matches = _regex_patterns.QUANTITY_NON_BASIC_UNIT_GROUPS.findall(self._standardized_ingredient) # TODO: testing

        # remove any empty matches
        valid_nonbasic_units = [i for i in nonbasic_unit_matches if len(i) > 0]

        # debugging message
        nonbasic_units_message = f"Valid non basic units: {valid_nonbasic_units}" if valid_nonbasic_units else f"No valid non basic units found..."

        # if we found a number followed by a non basic unit, then set the self._quantity and the self._unit member variables and exit the function
        if nonbasic_unit_matches and valid_nonbasic_units:
            self._quantity = valid_nonbasic_units[0][0].strip()
            self._unit = valid_nonbasic_units[0][1].strip()
            return
        
        # ---- STEP 3: CHECK FOR ANY QUANTITIES or ANY UNITS in the string, and use the first instances (if they exist) ----
        # Example: "cups, 2 juice of lemon" -> quantity: "2", unit: "juice"

        # if neither basic nor nonbasic units are found, then get all of the numbers and all of the units
        quantity_matches = _regex_patterns.ALL_NUMBERS.findall(self._standardized_ingredient) # TODO: testing
        unit_matches     = _regex_patterns.UNITS_PATTERN.findall(self._standardized_ingredient) # TODO: testing

        # remove any empty matches
        valid_quantities = [i for i in quantity_matches if len(i) > 0]
        valid_units     = [i for i in unit_matches if len(i) > 0]

        # debugging messages
        all_quantities_message = f"Valid quantities: {valid_quantities}" if valid_quantities else f"No valid quantities found..."
        all_units_message = f"Valid units: {valid_units}" if valid_units else f"No valid units found..."

        # if either have valid quantities then set the best quantity and best unit to 
        # the first valid quantity and units found, otherwise set as None
        # TODO: Drop this "if valid_quantities or valid_units"...?
        if valid_quantities or valid_units:
            self._quantity = valid_quantities[0].strip() if valid_quantities else None
            self._unit = valid_units[0].strip() if valid_units else None
            return

        # ---- STEP 4: NO MATCHES ----
        # just print a message if no valid quantities or units are found and return None
        # best_quantity and best_unit are set to None by default and will remain that way if no units or quantities were found.
        no_matches_message = f"No valid quantities or units found..."

        return 
    
    def _check_if_required_parenthesis(self, parenthesis_list: list) -> bool:
        """
        Check if the parenthesis content contains the word "optional".
        Args:
            parenthesis_list (list): A list of strings containing the content of the parenthesis in the ingredient string.
        Returns:
            bool: A boolean indicating whether the word "optional" is found in the parenthesis content.
        """

        optional_set = set(["option", "options", "optional", "opt.", "opts.", "opt", "opts", "unrequired"])
        required_set = set(["required", "requirement", "req.", "req"])
        
        # regex match for the words "optional" or "required" in the parenthesis content
        optional_match_flag = any([True if _regex_patterns.OPTIONAL_STRING.findall(i) else False for i in parenthesis_list])
        required_match_flag = any([True if _regex_patterns.REQUIRED_STRING.findall(i) else False for i in parenthesis_list])

        # check if any of the words in the parenthesis content are in the optional or required sets
        optional_str_flag = any([any([True if word in optional_set else False for word in i.replace("(", "").replace(")", "").replace(",", " ").split()]) for i in parenthesis_list])
        required_str_flag = any([any([True if word in required_set else False for word in i.replace("(", "").replace(")", "").replace(",", " ").split()]) for i in parenthesis_list])
        
        is_required = (True if required_match_flag or required_str_flag else False) or (False if optional_match_flag or optional_str_flag else True)

        return is_required

    def _check_if_required_string(self, ingredient: str) -> bool:
        """
        Check the ingredient string for optional or required text
        Args:
            ingredient (str): The ingredient string to parse.
        Returns:
            bool: A boolean indicating whether the ingredient is required or not.
        """
        # ingredient = reduced
        optional_set = set(["option", "options", "optional", "opt.", "opts.", "opt", "opts", "unrequired"])
        required_set = set(["required", "requirement", "req.", "req"])

        # regex match for the words "optional" or "required" in the ingredient string
        optional_match_flag = True if _regex_patterns.OPTIONAL_STRING.findall(ingredient) else False
        required_match_flag = True if _regex_patterns.REQUIRED_STRING.findall(ingredient) else False
        
        # check if any of the words in the ingredient string are in the optional or required sets
        optional_str_flag = any([True if word in optional_set else False for word in ingredient.replace(",", " ").split()])
        required_str_flag = any([True if word in required_set else False for word in ingredient.replace(",", " ").split()])

        # if any "required" strings were matched or found, or if no "optional" strings were matched or found, then the ingredient is required
        is_required = (True if required_match_flag or required_str_flag else False) or (False if optional_match_flag or optional_str_flag else True)

        return is_required
    
    def _is_ingredient_required(self) -> bool:
        """
        Check if the ingredient is required or optional
        Returns a boolean indicating whether the ingredient is required or optional.
        """

        # check if the ingredient string contains the word "optional" or "required"
        # ingredient_is_required = self._check_if_required_string(self._reduced_ingredient)
        ingredient_is_required = self._check_if_required_string(self._standardized_ingredient) # TODO: testing this out

        # check the parenthesis content for the word "optional" or "required"
        parenthesis_is_required = self._check_if_required_parenthesis(self._parenthesis_content)

        # if BOTH of the above conditions are True then return True otherwise return False
        return True if ingredient_is_required and parenthesis_is_required else False
    
    def _address_quantity_only_parenthesis(self, parenthesis: str) -> None:
        """
        Address the case where the parenthesis content only contains a quantity.
        Attempts to update self._quantity, self._unit, self._secondary_quantity, and self._secondary_unit given 
        information from the parenthesis string and the current self._quantity and self._unit
        (e.g. "(3)", "(2.5)", "(1/2)")
        Args:
            parenthesis (str): The content of the parenthesis in the ingredient string.
        Returns:
            None
        """

        # Set a None Description
        description = None

        # pull out the parenthesis quantity values
        numbers_only = _utils._extract_quantities_only(parenthesis) # NOTE: testing this out

        # if no numbers only parenthesis, then just return the original ingredient
        if not numbers_only:
            # print(f"\n > Return early from QUANTITY parenthesis") if self.debug else None
            description = f"not a quantity only parenthesis"
            self._parenthesis_notes.append(description)
            return
        
        is_approximate_quantity = _utils._is_approximate_quantity_only_parenthesis(parenthesis)

        # if the quantity is approximate, then add a note to the parenthesis notes and return early
        if is_approximate_quantity:
            description = f"approximate quantity only"
            self._parenthesis_notes.append(description)
            return

        # pull out the self._quantity from the parenthesis
        parenthesis_quantity = numbers_only[0]

        # if there is not a unit or a quantity, then we can use the parenthesis number as the quantity and
        #  return the ingredient with the new quantity
        # TODO: OR the unit MIGHT be the food OR might be a "SOMETIMES_UNIT", maybe do that check here, not sure yet...
        if not self._quantity and not self._unit:
            description = f"maybe unit is: the 'food' or a 'sometimes unit'"
            self._parenthesis_notes.append(description)

            self._quantity = parenthesis_quantity
            return
        
        # if there is a quantity but no unit, we can try to merge (multiply) the current quantity and the parenthesis quantity 
        # then the unit is also likely the food 
        # TODO: OR the unit MIGHT be the food OR might be a "SOMETIMES_UNIT", maybe do that check here, not sure yet...
        if self._quantity and not self._unit:
            updated_quantity = str(float(self._quantity) * float(parenthesis_quantity))
            
            description = f"maybe unit is: the 'food' or a 'sometimes unit'"
            self._parenthesis_notes.append(description)

            # set the secondary quantity to the ORIGINAL quantity/units
            self._secondary_quantity = self._quantity 

            # Update the quantity with the updated merged quantity
            self._quantity = _utils._make_int_or_float_str(updated_quantity)
            # self._quantity = updated_quantity

            # return [updated_quantity, self._unit, description]
            return
        
        # if there is a unit but no quantity, then we can use the parenthesis number as the quantity and 
        # return the ingredient with the new quantity
        if not self._quantity and self._unit:
            # updated_quantity = numbers_only[0]
            description = f"used quantity from parenthesis"
            self._parenthesis_notes.append(description)

            # set the secondary quantity to the ORIGINAL quantity/units
            self._secondary_quantity = self._quantity 

            # set the quantity to the parenthesis quantity
            self._quantity = parenthesis_quantity

            return

        # if there is a quantity and a unit, then we can try
        # to merge (multiply) the current quantity and the parenthesis quantity
        # then return the ingredient with the new quantity
        if self._quantity and self._unit:
            # if there is a quantity and a unit, then we can try to merge (multiply) the current quantity and the parenthesis quantity
            # then return the ingredient with the new quantity

            description = f"multiplied starting quantity with parenthesis quantity"
            self._parenthesis_notes.append(description)

            updated_quantity = str(float(self._quantity) * float(parenthesis_quantity))

            # set the secondary quantity to the ORIGINAL quantity/units
            self._secondary_quantity = self._quantity 

            # Update the quantity with the updated merged quantity (original quantity * parenthesis quantity)
            self._quantity = _utils._make_int_or_float_str(updated_quantity)
            # self._quantity = updated_quantity

            return

        description = f"used quantity from parenthesis with quantity only"
        self._parenthesis_notes.append(description)
        
        # set the secondary quantity to the ORIGINAL quantity/units
        self._secondary_quantity = self._quantity 

        # update the quantity with the parenthesis quantity value
        self._quantity = parenthesis_quantity

        return
    
    def _address_equivalence_parenthesis(self, parenthesis: str) -> None:
        """
        Address the case where the parenthesis content contains any equivalence strings like "about" or "approximately", followed by a quantity and then a unit later in the sting.
        Attempts to update self._quantity, self._unit, self._secondary_quantity, and self._secondary_unit given 
        information from the parenthesis string and the current self._quantity and self._unit
        e.g. "(about 3 ounces)", "(about a 1/3 cup)", "(approximately 1 large tablespoon)"

        Args:
            parenthesis (str): A string containing parenthesis from the ingredients string
        Returns:
            None
        """

        # print(f"""Ingredient: '{self._reduced_ingredient}'\nParenthesis: '{parenthesis}'\nQuantity: '{self._quantity}'\nUnit: '{self._unit}'""") if self.debug else None

        
        # Set a None Description
        description = None

        # check for the equivelency pattern (e.g. "<equivelent string> <quantity> <unit>" )
        equivalent_quantity_unit = _utils._extract_equivalent_quantity_units(parenthesis)
        # equivalent_quantity_unit = _regex_patterns.EQUIV_QUANTITY_UNIT_GROUPS.findall(parenthesis)
        # equivalent_quantity_unit = [item for i in [regex.EQUIV_QUANTITY_UNIT_GROUPS.findall(i) for i in parenthesis] for item in i]

        # remove parenthesis and then split on whitespace
        split_parenthesis = parenthesis.replace("(", "").replace(")", "").split()

        # Case when: NO equivelence quantity unit matches 
        #           OR parenthesis contains a quantity per unit like string in the parenthesis (i.e. "(about 2 ounces each)" contains "each")
        # Then return early with NO UPDATES and keep the current quantity/unit as is
        if not equivalent_quantity_unit or any([True if i in _constants.QUANTITY_PER_UNIT_STRINGS else False for i in split_parenthesis]):
            # print(f"\n > Return early from EQUIVALENCE parenthesis") if self.debug else None
            description = f"not a equivalence quantity unit parenthesis"
            self._parenthesis_notes.append(description)
            return
        
        # pull out the suffix word, parenthesis quantity and unit
        parenthesis_suffix, parenthesis_quantity, parenthesis_unit = equivalent_quantity_unit[0]
        
        # Case when: NO quantity, NO unit:
            # if no quantity AND no unit, then we can use the parenthesis quantity-unit as our quantity and unit
        if not self._quantity and not self._unit:

            description = f"used equivalence quantity unit as our quantity and unit"
            self._parenthesis_notes.append(description)

            # set quantity/unit to the parenthesis values
            self._quantity = parenthesis_quantity
            self._unit = parenthesis_unit

            return
        
        # Case when: YES quantity, NO unit:
            # we can assume the equivelent quantity units 
            # in the parenthesis are actually a better fit for the quantities and units so 
            # we can use those are our quantities/units and then stash the original quantity in the "description" field 
            # with a "maybe quantity is " prefix in front of the original quantity for maybe use later on
        if self._quantity and not self._unit:

            # stash the old quantity with a trailing string before changing best_quantity
            description = f"maybe quantity is: {' '.join(self._quantity)}"
            self._parenthesis_notes.append(description)

            # make the secondary_quantity the starting quantity before converting the quantity to the value found in the parenthesis
            self._secondary_quantity = self._quantity

            # set the quantity/unit to the parenthesis values
            self._quantity = parenthesis_quantity
            self._unit = parenthesis_unit

            return 

        # Case when: NO quantity, YES unit:
            # if there is no quantity BUT there IS a unit, then the parenthesis units/quantities are probably "better" so use the
            # parenthesis quantity/units and then stash the old unit in the description
        if not self._quantity and self._unit:

            # stash the old quantity with a trailing "maybe"
            description = f"maybe unit is: {self._unit}"
            self._parenthesis_notes.append(description)

            # make the secondary_unit the starting unit before converting the unit to the unit string found in the parenthesis
            self._secondary_unit = self._unit

            self._quantity = parenthesis_quantity
            self._unit = parenthesis_unit

            # return [parenthesis_quantity, parenthesis_unit, description]
            return 
        
        # Case when: YES quantity, YES unit:
            # if we already have a quantity AND a unit, then we likely found an equivalent quantity/unit
            # we will choose to use the quantity/unit pairing that is has a unit in the BASIC_UNITS_SET
        if self._quantity and self._unit:
            parenthesis_unit_is_basic = parenthesis_unit in _constants.BASIC_UNITS_SET
            unit_is_basic = self._unit in _constants.BASIC_UNITS_SET

            # Case when BOTH are basic units:  (# TODO: Maybe we should use parenthesis quantity/unit instead...?)
            #   use the original quantity/unit (stash the parenthesis in the description)
            if parenthesis_unit_is_basic and unit_is_basic:
                description = f"maybe quantity/unit is: {parenthesis_quantity}/{parenthesis_unit}"
                self._parenthesis_notes.append(description)
                # return [self._quantity, self._unit, description]

                # set the secondary quantity/units to the values in the parenthesis
                self._secondary_quantity = parenthesis_quantity
                self._secondary_unit = parenthesis_unit

                return
            
            # Case when NEITHER are basic units:    # TODO: this can be put into the above condition but thought separated was more readible.
            #   use the original quantity/unit (stash the parenthesis in the description)
            if not parenthesis_unit_is_basic and not unit_is_basic:
                description = f"maybe quantity/unit is: {parenthesis_quantity}/{parenthesis_unit}"
                self._parenthesis_notes.append(description)
                # return [self._quantity, self._unit, description]
                
                # set the secondary quantity/units to the values in the parenthesis
                self._secondary_quantity = parenthesis_quantity
                self._secondary_unit = parenthesis_unit

                return

            # Case when: YES basic parenthesis unit, NO basic original unit: 
            #   then use the parenthesis quantity/unit (stash the original in the description)
            if parenthesis_unit_is_basic:
                description = f"maybe quantity/unit is: {self._quantity}/{self._unit}"
                self._parenthesis_notes.append(description)
                
                # set the secondary quantity/units to the original quantity/units
                self._secondary_quantity = self._quantity
                self._secondary_unit = self._unit

                # update the primary quantities/units to the parenthesis values
                self._quantity = parenthesis_quantity
                self._unit = parenthesis_unit
                
                # return [parenthesis_quantity, parenthesis_unit, description]
                return

            # Case when: NO basic parenthesis unit, YES basic original unit: 
            #   then use the original quantity/unit (stash the parenthesis in the description)
            if unit_is_basic:
                description = f"maybe quantity/unit is: {parenthesis_quantity}/{parenthesis_unit}"
                self._parenthesis_notes.append(description)

                # set the secondary quantity/units to the original quantity/units
                self._secondary_quantity = parenthesis_quantity
                self._secondary_unit = parenthesis_unit

                return

        description = f"used quantity/units from parenthesis with equivalent quantity/units"
        self._parenthesis_notes.append(description)

        # set the secondary quantity/units to the original quantity/units
        self._secondary_quantity = self._quantity
        self._secondary_unit = self._unit

        self._quantity = parenthesis_quantity
        self._unit = parenthesis_unit

        return
    
    def _address_quantity_unit_only_parenthesis(self, parenthesis: str) -> None:
        """
        Address the case where the parenthesis content contains exactly a quantity and unit (NOT prefixed by any equivalence strings like "about" or "approximately").
        Attempts to update self._quantity, self._unit, self._secondary_quantity, and self._secondary_unit given 
        information from the parenthesis string and the current self._quantity and self._unit
        e.g. "(3 ounces)", "(3 ounces each)", "(a 4 cup scoop)"

        Args:
            parenthesis (str): A string containing parenthesis from the ingredients string
        Returns:
            None
        """

        # print(f"""Ingredient: '{self._standardized_ingredient}'\nParenthesis: '{parenthesis}'\nQuantity: '{self._quantity}'\nUnit: '{self._unit}'""") if self.debug else None

        # Set a None Description
        description = None

        # pull out quantity unit only pattern
        quantity_unit_only = _utils._extract_quantity_unit_pairs(parenthesis)

        # if no numbers only parenthesis, then just return the original ingredient
        if not quantity_unit_only:
            description = f"not a quantity unit only parenthesis"
            self._parenthesis_notes.append(description)
            return
        
        # pull out the parenthesis quantity and unit
        parenthesis_quantity, parenthesis_unit = quantity_unit_only[0]

        # Case when: NO quantity, NO unit:
            # if no quantity AND no unit, then we can use the parenthesis self._quantity-unit as our self._quantity and unit
        if not self._quantity and not self._unit:
            # updated_quantity, updated_unit = quantity_unit_only[0]
            # print(f"\n > Case when: NO quantity, NO unit") if self.debug else None

            description = f"used quantity/unit from parenthesis with no quantity/unit"
            self._parenthesis_notes.append(description)

            # set the secondary quantity/units to the original quantity/units
            self._secondary_quantity = self._quantity
            self._secondary_unit = self._unit

            self._quantity = parenthesis_quantity
            self._unit = parenthesis_unit

            return

        # Case when: YES quantity, NO unit:
            # if there is a quantity but no unit, we can try to merge (multiply) the current quantity and the parenthesis quantity 
            # then use the unit in the parenthesis
        if self._quantity and not self._unit:
            # print(f"\n > Case when: YES quantity, NO unit") if self.debug else None

            # quantity_unit_only[0][0]
            updated_quantity = str(float(self._quantity) * float(parenthesis_quantity))

            description = f"multiplied starting quantity with parenthesis quantity"
            self._parenthesis_notes.append(description)

            # set the secondary quantity/units to the original quantity/units
            self._secondary_quantity = self._quantity
            self._secondary_unit = self._unit

            self._quantity = _utils._make_int_or_float_str(updated_quantity)
            self._unit = parenthesis_unit

            return

        # Case when: NO quantity, YES unit:
            # if there is no quantity BUT there IS a unit, then the parenthesis units/quantities are either:
            # 1. A description/note (i.e. cut 0.5 inch slices)
            # 2. A quantity and unit (i.e. 2 ounces)
            # either case, just return the parenthesis units to use those
        if not self._quantity and self._unit:
            # print(f"\n > Case when: NO quantity, YES unit") if self.debug else None

            description = f"No quantity but has units, used parenthesis. maybe quantity/unit is: {self._quantity}/{self._unit}"
            self._parenthesis_notes.append(description)

            # set the secondary quantity/units to the original quantity/units
            self._secondary_quantity = self._quantity
            self._secondary_unit = self._unit

            self._quantity = parenthesis_quantity
            self._unit = parenthesis_unit

            return

        # Case when: YES quantity, YES unit:
            # if we already have a quantity AND a unit, then we likely just found a description 
            # OR we may have found an equivalence quantity unit.
            # we will choose to use the quantity/unit pairing that is has a unit in the BASIC_UNITS_SET
        if self._quantity and self._unit:
            # print(f"\n > Case when: YES quantity, YES unit") if self.debug else None

            # flags for if original unit/parenthesis unit are in the set of basic units (BASIC_UNITS_SET) or not
            parenthesis_unit_is_basic = parenthesis_unit in _constants.BASIC_UNITS_SET
            unit_is_basic = self._unit in _constants.BASIC_UNITS_SET

            # Case when BOTH are basic units: 
            #   use the original quantity/unit (stash the parenthesis in the description)
            if parenthesis_unit_is_basic and unit_is_basic:
                # print(f"\n >>> Case when: BASIC parenthesis unit, BASIC unit") if self.debug else None

                description = f"maybe quantity/unit is: {parenthesis_quantity}/{parenthesis_unit}"
                self._parenthesis_notes.append(description)

                # set the secondary quantity/units to the parenthesis quantity/units
                self._secondary_quantity = parenthesis_quantity
                self._secondary_unit = parenthesis_unit
                return
            
            # Case when NEITHER are basic units:    # TODO: this can be put into the above condition but thought separated was more readible.
            #   use the original quantity/unit AND set the secondary quantity/units to the PARENTHESIS values 
            #   (stash the parenthesis in the description)
            if not parenthesis_unit_is_basic and not unit_is_basic:
                # print(f"\n >>> Case when: NOT BASIC parenthesis unit, NOT BASIC unit") if self.debug else None
                description = f"maybe quantity/unit is: {parenthesis_quantity}/{parenthesis_unit}"
                self._parenthesis_notes.append(description)

                # set the secondary quantity/units to the parenthesis quantity/units
                self._secondary_quantity = parenthesis_quantity
                self._secondary_unit = parenthesis_unit
                return

            # Case when: YES basic parenthesis unit, NO basic original unit (EXPLICIT):
            #  Try to merge (multiply) the current quantity and the parenthesis quantity
            #  AND set the secondary quantity/units to the ORIGINAL values
            if parenthesis_unit_is_basic and not unit_is_basic:
                # print(f"\n >>> Case when: BASIC parenthesis unit, NOT BASIC unit (EXPLICIT)") if self.debug else None
                updated_quantity = str(float(self._quantity) * float(parenthesis_quantity))

                description = f"multiplied starting quantity with parenthesis quantity"
                self._parenthesis_notes.append(description)

                # set the secondary quantity/units to the original quantity/units
                self._secondary_quantity = self._quantity
                self._secondary_unit = self._unit

                # self._quantity = updated_quantity
                self._quantity = _utils._make_int_or_float_str(updated_quantity)
                self._unit = parenthesis_unit

                return

            # TODO: I think this condition can be dropped, gets covered by previous condition...
            # Case when: YES basic parenthesis unit, NO basic original unit (IMPLICITLY): 
            #   then use the parenthesis quantity/unit AND set the secondary quantity/units to the ORIGINAL values
            #   (stash the original in the description)
            if parenthesis_unit_is_basic:
                # print(f"\n >>> Case when: BASIC parenthesis unit, NOT BASIC unit (IMPLICIT)") if self.debug else None
                description = f"maybe quantity/unit is: {self._quantity}/{self._unit}"
                self._parenthesis_notes.append(description)

                # set the secondary quantity/units to the original quantity/units
                self._secondary_quantity = self._quantity
                self._secondary_unit = self._unit

                self._quantity = parenthesis_quantity
                self._unit = parenthesis_unit

                return

            # Case when: NO basic parenthesis unit, YES basic original unit: 
            #   then just keep the original quantity/unit AND set the secondary quantity/units to the PARENTHESIS values
            #   (stash the original in the description)
            if unit_is_basic:
                # print(f"\n >>> Case when: NOT BASIC parenthesis unit, BASIC unit (IMPLICIT)") if self.debug else None
                description = f"maybe quantity/unit is: {self._quantity}/{self._unit}"
                self._parenthesis_notes.append(description)

                # set the secondary quantity/units to the parenthesis quantity/units
                self._secondary_quantity = parenthesis_quantity
                self._secondary_unit = parenthesis_unit

                return
        
        # print(f"\n ----> Case when: ALL OTHER CASES FAILED") if self.debug else None

        # TODO: Don't think this should ever happen, need to rethink this part
        # Case when: All other conditions were NOT met:
            # just set the quantity/unit to the parenthesis values 
            # and then put the original quantity/units in the secondary quantity/units
        description = f"used quantity/units from parenthesis with quantity/units only"
        self._parenthesis_notes.append(description)

        # set the secondary quantity/units to the ORIGINAL quantity/units
        self._secondary_quantity = self._quantity 
        self._secondary_unit = self._unit

        # set the primary quantity/units to the parenthesis quantity/units
        self._quantity = parenthesis_quantity
        self._unit = parenthesis_unit

        return
    
    def _add_standard_units(self) -> None:
        """
        Add standard units to the parsed ingredient if they are present in the
        constants units to standard units map.
        If the "unit"/"secondary_unit" exists and it is present in the unit to standard unit map, 
        then get the standard unit name for the unit and set the "standardized_unit" and "standardized_secondary_unit" member variables.
        """

        if self._unit and self._unit in _constants.UNIT_TO_STANDARD_UNIT:
            self._standardized_unit = _constants.UNIT_TO_STANDARD_UNIT[self._unit]
        
        if self._secondary_unit and self._secondary_unit in _constants.UNIT_TO_STANDARD_UNIT:
            self._standardized_secondary_unit = _constants.UNIT_TO_STANDARD_UNIT[self._secondary_unit]

        return 

    def _prioritize_weight_units(self) -> None:
        """
        Prioritize weight units over volume units if both are present in the parsed ingredient.
        If the first unit is not a weight unit but the secondary_unit is a weight unit, then swap them so 
        the weight unit is always given as the primary unit.
        (i.e. unit = "cups", secondary_unit = "ounces" --> Swap them so that unit = "ounces" and secondary_unit = "cups")
        """

        # # if the first unit is already a weight, just return early
        if self._unit in _constants.WEIGHT_UNITS_SET:
            return 
        
        # TODO: first part of this if statement is probably redundent...
        # if the first unit is NOT a weight and the second unit IS a weight, then swap them
        if self._unit not in _constants.WEIGHT_UNITS_SET and self._secondary_unit in _constants.WEIGHT_UNITS_SET:

            # print(f"Swapping first quantity/units with second quantity/units") if self.debug else None
            # print(f"Swapping first quantity/units with second quantity/units") if self.debug else None

            # switch the units and quantities with the secondary units and quantities
            self._quantity, self._secondary_quantity = self._secondary_quantity, self._quantity
            self._unit, self._secondary_unit = self._secondary_unit,  self._unit
            self._standardized_unit, self._standardized_secondary_unit = self._standardized_secondary_unit, self._standardized_unit

        return 
    
    def _extract_foods(self, ingredient: str) -> str:
        """Does a best effort attempt to extract foods from the ingredient by 
        removing all extraneous details, words, characters and hope we get left with the food.
        """

        # print(f"Best effort extraction of food words from: {ingredient}") if self.debug else None

        # Apply _utils._remove_parenthesis_from_str() to remove parenthesis content
        ingredient = _utils._remove_parenthesis_from_str(ingredient)

        # check for obscure/tricky edge case foods and if found, return them as the food (i.e. half-and-half, etc.)
        edge_food = _utils._extract_edge_case_foods(ingredient)
        if edge_food:
            return edge_food

        # regular expressions to find and remove from the ingredient
        # NOTE: important to remove "parenthesis" first and "stop words" last to.
        # Parenthesis can contain other patterns and they need to be dealt with first (i.e. "(about 8 oz)" contains a number and a unit)
        patterns_map = {
            # "parenthesis" : _regex_patterns.SPLIT_BY_PARENTHESIS, # NOTE: testing this removal
            "units" : _regex_patterns.UNITS_PATTERN,
            "numbers" : _regex_patterns.ALL_NUMBERS,
            "prep words" : _regex_patterns.PREP_WORDS_PATTERN,
            "ly-words" : _regex_patterns.WORDS_ENDING_IN_LY,
            "unit modifiers" : _regex_patterns.UNIT_MODIFIERS_PATTERN,
            "dimension units" : _regex_patterns.DIMENSION_UNITS_PATTERN,
            "approximate strings" : _regex_patterns.APPROXIMATE_STRINGS_PATTERN,
            "size modifiers" : _regex_patterns.SIZE_MODIFIERS_PATTERN,
            "casual quantities" : _regex_patterns.CASUAL_QUANTITIES_PATTERN,
            "stop words" : _regex_patterns.STOP_WORDS_PATTERN
        }

        for key, pattern in patterns_map.items():
            ingredient = _utils._find_and_remove(ingredient, pattern)
        
        ingredient = re.sub(r'[^\w\s]', '', ingredient) # remove any special characters
        ingredient = re.sub(r'\s+', ' ', ingredient).strip() # remove any extra whitespace

        return ingredient
    
    def _extract_prep_words(self, ingredient: str) -> str:
        """Get prep words from the ingredient (including words ending in 'ly')"""

        ly_ending_words = set(_regex_patterns.WORDS_ENDING_IN_LY.findall(ingredient))
        ly_ending_words = list(ly_ending_words - _constants.APPROXIMATE_STRINGS) # remove any accidental match overlaps like "approximately"

        prep_words = _regex_patterns.PREP_WORDS_PATTERN.findall(ingredient)
        prep_words.extend(ly_ending_words) # combine the prep words with the 'ly' ending words
        prep_words = list(set(prep_words)) # unique 
        prep_words.sort()       

        return prep_words
    
    def _extract_size_modifiers(self, ingredient: str) -> str:
        """Extract size modifier words from the ingredient"""

        size_modifiers = _regex_patterns.SIZE_MODIFIERS_PATTERN.findall(ingredient)
        size_modifiers.sort()

        return size_modifiers

    def _add_food_density(self):
        """Add food densities to the units variables if they are the only possible units after the ingredient has been parsed."""
        # ingredient = "2 1/2 cups of sugar (about 1/2 inch squares of sugar)"
        
        if _utils._has_volume_unit(self._unit, self._standardized_unit, self._secondary_unit, self._standardized_secondary_unit):
            densities       = _utils._get_food_density(self._food, "dice")
            self._densities = densities

    def _add_gram_weights(self):
        """Add gram weights to the units variables if they are the only possible units after the ingredient has been parsed."""
        
        grams_map = _utils._get_gram_weight(self._food, self._quantity, self._unit, self._densities, "dice")

        if grams_map:
            self._gram_weight     = grams_map.get("gram_weight", None)
            self._min_gram_weight = grams_map.get("min_gram_weight", None)
            self._max_gram_weight = grams_map.get("max_gram_weight", None)

        return
    
    def _add_gram_weights_for_single_item_foods(self):

        if not self._gram_weight:
            # print(f'THIS IS A SINGLE ITEM FOOD: {self._food}') if self.debug else None
            # NOTE: this is an arbitrary fuzzy string matching ratio of 0.85 for now, probably want this to be pretty strict 
            # NOTE: so we don't get false positives (maybe even just make it 0.95 or 1 to just only match single character differences)
            gram_weight = _utils._get_single_item_gram_weight(self._food, self._quantity)

            self._gram_weight = gram_weight

        return 

    def _get_food_units(self):
        """If no units were found, check for possible 'food units', and use those if they are found"""

        if not self._unit and not self._standardized_unit:
            food_unit     = _utils._get_food_unit(self._standardized_ingredient)
            std_food_unit = _constants.FOOD_UNIT_TO_STANDARD_FOOD_UNIT.get(food_unit)

            self._unit              = food_unit
            self._standardized_unit = std_food_unit
        
        return 
    
    def _set_default_quantities(self):
        """Set a default quantity if no quantity was found"""
        
        is_weight_or_volume_unit = _utils._is_weight_unit(self._standardized_unit) or _utils._is_volumetric_unit(self._standardized_unit)
        missing_primary_quantity = self._quantity is None
        
        if is_weight_or_volume_unit and missing_primary_quantity:
            self._quantity = "1"

        return

    def _get_animal_protein_gram_weight(self):
        """If the food is an animal protein, then get the gram weight for that protein"""
        if not self._gram_weight:
            gram_weight = _utils._get_animal_protein_gram_weight(self._quantity, self._unit)
            if not gram_weight:
                gram_weight = _utils._get_animal_protein_gram_weight(self._secondary_quantity, self._secondary_unit)
            
            self._gram_weight = gram_weight

        return 
    
    def _address_parenthesis(self) -> None:
        """
        Address any parenthesis that were in the ingredient.
        """
        # print(f"Addressing parenthesis: '{self._parenthesis_content}'") if self.debug else None

        # loop through each of the parenthesis in the parenthesis content and apply address_parenthesis functions 
        for parenthesis in self._parenthesis_content:

            # address the case where the parenthesis content only contains a quantity
            self._address_quantity_only_parenthesis(parenthesis)
            
            self._address_equivalence_parenthesis(parenthesis)

            self._address_quantity_unit_only_parenthesis(parenthesis)

        return

    def _parse(self):
        # TODO: process parenthesis content

        print(f"Standardizing ingredient: \n > '{self.ingredient}'") if self.debug else None

        # ----------------------------------- STEP 1 ------------------------------------------
        # ---- Get the input ingredient string into a standardized form ----
        # -------------------------------------------------------------------------------------

        # run the standardization method to cleanup raw ingredient and create the "standard_ingredient" and "_reduced_ingredient" member variables 
        self._standardize()

        print(f"Standardized ingredient: \n > '{self._standardized_ingredient}'") if self.debug else None
        # ----------------------------------- STEP 2 ------------------------------------------
        # ---- Check if there is any indication of the ingredient being required/optional ----
        # -------------------------------------------------------------------------------------

        # run the is_required method to check if the ingredient is required or optional and set the "is_required" member variable to the result
        self._is_required = self._is_ingredient_required()

        print(f"Is the ingredient required? {self._is_required}") if self.debug else None
        # ----------------------------------- STEP 3 ------------------------------------------
        # ---- Extract first options of quantities and units from the "_reduced_ingredient" ----
        # -------------------------------------------------------------------------------------
        print(f"Attempting to extract quantity and unit") if self.debug else None
        # run the extract_first_quantity_unit method to extract the first unit and quantity from the ingredient string
        self.extract_first_quantity_unit()

        # ----------------------------------- STEP 4 ------------------------------------------
        # ---- Address any parenthesis that were in the ingredient  ----
        # -------------------------------------------------------------------------------------
        # NOTE: Stash the best_quantity and best_units before preceeding (for debugging)

        print(f"""Addressing parenthesis: 
                > Standard ingredient: '{self._standardized_ingredient}'
                > Parenthesis content: '{self._parenthesis_content}'
            """) if self.debug else None

        self._address_parenthesis()

        # ----------------------------------- STEP 5 ------------------------------------------
        # ---- Get the standard names of the units and secondary units ----
        # -------------------------------------------------------------------------------------
        print(f"Adding standard unit names for {self._unit} and {self._secondary_unit}") if self.debug else None

        self._add_standard_units()

        # ----------------------------------- STEP 6 ------------------------------------------
        # ---- Prioritize weight units and always place the weight unit as the primary ingredient if it exists ----
        # -------------------------------------------------------------------------------------
        print(f"Prioritizing weight units") if self.debug else None

        self._prioritize_weight_units()

        # ----------------------------------- STEP 7 ------------------------------------------
        # ---- Extract foods the best we can by removing:
        # > parenthesis content
        # > stop words
        # > units
        # > quantities
        # > prep words
        # > "ly"-words
        # -------------------------------------------------------------------------------------
        print(f"Extracting food words") if self.debug else None
        
        self._food = self._extract_foods(self._standardized_ingredient)

        # ----------------------------------- STEP 8 ------------------------------------------
        # ---- Extract extra, descriptors (prep words, size modifiers, dimension units) ----
        # -------------------------------------------------------------------------------------
        print(f"Extracting prep words, size modifiers") if self.debug else None
        self._prep = self._extract_prep_words(self._staged_ingredient) 
        self._size_modifiers = self._extract_size_modifiers(self._staged_ingredient) 
        
        # ----------------------------------- STEP 9 ------------------------------------------
        # ---- Calculate food density if possible ----
        # -------------------------------------------------------------------------------------
        print(f"Calculating food density") if self.debug else None
        self._add_food_density() 

        # ----------------------------------- STEP 10 ------------------------------------------
        # ---- Calculate gram weights if possible ----
        # -------------------------------------------------------------------------------------
        print(f"Calculating gram weights") if self.debug else None
        self._add_gram_weights() 

        # ----------------------------------- STEP 11 ------------------------------------------
        # ---- Calculate gram weights if possible ----
        # -------------------------------------------------------------------------------------
        print(f"Estimating gram weights for unitless foods") if self.debug else None
        self._add_gram_weights_for_single_item_foods() 

        # ----------------------------------- STEP 12 ------------------------------------------
        # ---- If no units were found ---- 
        # ---- check for food units and set those as the unit / standardized_unit ----
        # -------------------------------------------------------------------------------------
        print(f"Checking for possible 'food units' (i.e. '2 corn tortillas' has a unit of 'tortillas')") if self.debug else None
        self._get_food_units() 
       
        # ----------------------------------- STEP 13 ------------------------------------------
        # ---- If not quantity is found, set quantity to a default of 1 ---- 
        # -------------------------------------------------------------------------------------
        print(f"Set quantity to 1 if not found") if self.debug else None
        self._set_default_quantities()
       
        # ----------------------------------- STEP 14 ------------------------------------------
        # ---- If no gram weight has been found ---- 
        # ---- check for any common 'animal protein units' (i.e. 'breasts', 'drumsticks', etc)
        # ---- and calculate a gram weight for any found units ----
        # -------------------------------------------------------------------------------------
        print(f"Checking for possible 'animal protein units' (i.e. '2 chicken breasts' has a unit of 'breast') and calculating a gram weight for any found units") if self.debug else None
        self._get_animal_protein_gram_weight() 
       
    def standardized_ingredient(self) -> str:
        """
        Return the standardized ingredient string.
        Returns:
            str: The standardized ingredient string.
        """
        return self._standardized_ingredient

    def food(self) -> str:
        """
        Return the food string.
        Returns:
            str: The food string.
        """
        return self._food
    
    def quantity(self) -> str:
        """
        Return the quantity string.
        Returns:
            str: The quantity string.
        """
        return self._quantity
    
    def unit(self) -> str:
        """
        Return the unit string.
        Returns:
            str: The unit string.
        """
        return self._unit
    
    def standardized_unit(self) -> str:
        """
        Return the standardized unit string.
        Returns:
            str: The standardized unit string.
        """
        return self._standardized_unit
    
    def secondary_quantity(self) -> str:
        """
        Return the secondary quantity string.
        Returns:
            str: The secondary quantity string.
        """
        return self._secondary_quantity
    
    def secondary_unit(self) -> str:
        """
        Return the secondary unit string.
        Returns:
            str: The secondary unit string.
        """
        return self._secondary_unit
    
    def standardized_secondary_unit(self) -> str:
        """
        Return the standardized secondary unit string.
        Returns:
            str: The standardized secondary unit string.
        """
        return self._standardized_secondary_unit
    
    def density(self) -> Union[str, float, int, None]:
        """
        Return the density of the given ingredient.
        Returns:
            str: The density of the given ingredient. 
        """

        return self._densities.get("density") if self._densities else None
    
    def gram_weight(self) -> str:
        """
        Return the estimated gram weight of the given ingredient.
        Returns:
            str: The estimated gram weight of the given ingredient.
        """
        return self._gram_weight
    
    def min_gram_weight(self) -> str:
        """
        Return the estimated minimum gram weight of the given ingredient.
        Returns:
            str: The estimated minimum gram weight of the given ingredient.
        """
        return self._min_gram_weight
    
    def max_gram_weight(self) -> str:
        """
        Return the estimated maximum gram weight of the given ingredient.
        Returns:
            str: The estimated maximum gram weight of the given ingredient.
        """
        return self._max_gram_weight
    
    def prep(self) -> list:
        """
        Return the prep list.
        Returns:
            list: The prep list.
        """
        return self._prep
    
    def size_modifiers(self) -> list:
        """
        Return the size modifiers list.
        Returns:
            list: The size modifiers list.
        """
        return self._size_modifiers
    
    def dimensions(self) -> list:
        """
        Return the dimensions list.
        Returns:
            list: The dimensions list.
        """
        return self._dimensions
    
    def is_required(self) -> bool:
        """
        Check if the ingredient is required or optional.
        Returns:
            bool: True if the ingredient is required, False if the ingredient is optional.
        """

        return self._is_required
    
    def parsed_ingredient(self) -> dict:
        """
        Return the parsed ingredient dictionary.
        Returns:
            dict: The parsed ingredient dictionary (duplicate to to_json()) method
        """

        return self._parsed_ingredient
    
    def to_json(self) -> dict:
        """
        Convert the IngredientSlicer object to a dictionary.
        Returns:
            dict: A dictionary containing the IngredientSlicer object's member variables.
        """
        return {
            "ingredient": self.ingredient,                                # "2 1/2 large cups of sugar lightly packed (about 40 tbsp of sugar)"
            "standardized_ingredient": self._standardized_ingredient,          # "2.5 cups of sugar"
        
            "food" : self._food,                                           # "sugar"

            "quantity": self._quantity,                                    # "2.5"
            "unit": self._unit,                                            # "cups"
            "standardized_unit": self._standardized_unit,                      # "cup"

            "secondary_quantity": self._secondary_quantity,                # "40"
            "secondary_unit": self._secondary_unit,                        # "tbsp"
            "standardized_secondary_unit": self._standardized_secondary_unit,  # "tablespoon"
            "density": self._densities.get("density"),                     # 0.95
            # "density": self._densities.get("density") if self._densities else None,                     # 0.95
            "gram_weight": self._gram_weight,                              # "113.4 grams

            "prep": self._prep,                                            # ["lightly", "packed"]
            "size_modifiers": self._size_modifiers,                        # ["large"]
            "dimensions": self._dimensions,                                # ["2 inches"]
            "is_required": self._is_required,                              # True

            # NOTE: drop these at some point
            "parenthesis_content": self._parenthesis_content               # ["(about 40 tbsp of sugar)"]
            # "parenthesis_notes": self._parenthesis_notes,
        }
    
    def __str__(self) -> str:
        """
        Return a string representation of the IngredientSlicer object.
        Returns:
            str: A string representation of the IngredientSlicer object.
        """
        return f"""IngredientSlicer Object:
    \tIngredient: '{self.ingredient}'
    \tStandardized Ingredient: '{self._standardized_ingredient}'
    \tFood: '{self._food}'
    \tQuantity: '{self._quantity}'
    \tUnit: '{self._unit}'
    \tStandardized Unit: '{self._standardized_unit}'
    \tSecondary Quantity: '{self._secondary_quantity}'
    \tSecondary Unit: '{self._secondary_unit}'
    \tStandardized Secondary Unit: '{self._standardized_secondary_unit}'
    \tDensity: '{self._densities.get("density")}'
    \tGram Weight: '{self._gram_weight}'
    \tPrep: '{self._prep}'
    \tSize Modifiers: '{self._size_modifiers}'
    \tDimensions: '{self._dimensions}'
    \tIs Required: '{self._is_required}'
    \tParenthesis Content: '{self._parenthesis_content}'"""
