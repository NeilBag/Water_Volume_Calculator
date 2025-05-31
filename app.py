import math
import sys
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file
from io import BytesIO

app = Flask(__name__)

# Conversion factor
GALLONS_TO_LITERS = 3.785411784 # 1 US gallon = 3.785411784 liters [2, 3, 5, 10, 13]

# Approximate volumes of water bodies in Liters.
# These ranges are illustrative and designed to provide distinct categories for comparison.
# Sourced from various search results and general knowledge to provide a wide range.
WATER_BODY_VOLUMES = {
    "a small pond": {
        "min": 0,
        "max": 1.0 * (10**7), # Up to 10 million liters (10,000 m³) approx. for a large pond [8, 30, 31, 32, 43, 45]
    },
    "a large pond or a small lake": {
        "min": 1.0 * (10**7),
        "max": 1.0 * (10**9), # Up to 1 billion liters (1 million m³)
    },
    "a medium-sized lake": {
        "min": 1.0 * (10**9),
        "max": 1.0 * (10**12), # Up to 1 trillion liters (1 billion m³)
    },
    "a large lake (e.g., Lake Tahoe)": {
        "min": 1.0 * (10**12),
        "max": 1.0 * (10**15), # Up to 1 quadrillion liters (1 trillion m³) - Lake Tahoe ~1.47 x 10^14 L (39 trillion gallons) [19, 38, 42]
    },
    "a Great Lake (e.g., Lake Superior)": {
        "min": 1.0 * (10**15),
        "max": 1.0 * (10**17), # Up to 100 quadrillion liters (100 trillion m³) - Lake Superior ~1.21 x 10^16 L (3 quadrillion gallons) [6, 9, 21, 34, 35, 39, 40]
    },
    "an entire sea (e.g., Mediterranean Sea)": {
        "min": 1.0 * (10**17),
        "max": 1.0 * (10**19), # Up to 10 quintillion liters (10 exaliters) - Mediterranean Sea ~3.75 x 10^18 L (3.75 quintillion liters) [20, 36, 37, 41, 44]
    },
    "an entire ocean (e.g., Pacific Ocean)": {
        "min": 1.0 * (10**19),
        "max": 1.0 * (10**21), # Up to 1 sextillion liters - Pacific Ocean ~7.02 x 10^20 L (702 quintillion liters) [11, 17, 22, 26, 29]
    }
}

PLANET_VOLUMES = {
    "Planet Mars": 1.6318 * (10**23), # Mars Volume ~1.6318 x 10^11 km³ = 1.6318 x 10^23 L [1, 7, 14, 27, 28]
    "Planet Earth": 1.083 * (10**24), # Earth Volume ~1.083 x 10^12 km³ = 1.083 x 10^24 L [1, 4, 8, 12, 15, 18, 23]
    "Planet Jupiter": 1.4313 * (10**27) # Jupiter Volume ~1.4313 x 10^15 km³ = 1.4313 x 10^27 L [1, 4, 6, 12, 16, 24, 25]
}

def format_large_number_spoken(num, unit_str="Liters"):
    """
    Formats a large number into a human-readable string using terms like
    million, billion, trillion, quadrillion, quintillion, sextillion, septillion, etc.
    Handles 'Infinity' and very small numbers.
    """
    if num == float('inf'):
        return "Infinity"
    if num < 0:
        return f"Invalid (Negative) Volume {unit_str}"
    if num == 0:
        return f"0 {unit_str}"
    if num < 1:
        return f"{num:,.6f} {unit_str}" # For very small volumes, keep decimal format

    # Define suffixes for powers of 1000
    # The list is now sorted by value in descending order, making the lookup correct.
    suffixes = [
        (10**303, "Centillion"), # Approx. 10^303 to cover near float max
        (10**273, "NovemNovemDecillion"), # Using a more consistent naming for extreme numbers
        (10**270, "OctoNovemDecillion"),
        (10**267, "SeptenNovemDecillion"),
        (10**264, "SexNovemDecillion"),
        (10**261, "QuinNovemDecillion"),
        (10**258, "QuattuorNovemDecillion"),
        (10**255, "TreNovemDecillion"),
        (10**252, "DuoNovemDecillion"),
        (10**249, "UnNovemDecillion"),
        (10**246, "NovemDecillion"),
        (10**243, "OctoDecillion"),
        (10**240, "SeptenDecillion"),
        (10**237, "SexDecillion"),
        (10**234, "QuinDecillion"),
        (10**231, "QuattuorDecillion"),
        (10**228, "TreDecillion"),
        (10**225, "DuoDecillion"),
        (10**222, "UnDecillion"),
        (10**219, "Vigintillion"), # 10^3 * 73
        (10**216, "Novemsexagintillion"),
        (10**213, "Octosexagintillion"),
        (10**210, "Septensexagintillion"),
        (10**207, "Sexsexagintillion"),
        (10**204, "Quinsexagintillion"),
        (10**201, "Quattuorsexagintillion"),
        (10**198, "Tresexagintillion"),
        (10**195, "Duosexagintillion"),
        (10**192, "Unsexagintillion"),
        (10**189, "Sexagintillion"), # 10^3 * 63
        (10**186, "Novemquinquagintillion"),
        (10**183, "Octoquinquagintillion"),
        (10**180, "Septenquinquagintillion"),
        (10**177, "Sexquinquagintillion"),
        (10**174, "Quinquinquagintillion"),
        (10**171, "Quattuorquinquagintillion"),
        (10**168, "Trequinquagintillion"),
        (10**165, "Duoquinquagintillion"),
        (10**162, "Unquinquagintillion"),
        (10**159, "Quinquagintillion"), # 10^3 * 53
        (10**156, "Novemquadragintillion"),
        (10**153, "Octoquadragintillion"),
        (10**150, "Septenquadragintillion"),
        (10**147, "Sexquadragintillion"),
        (10**144, "Quinquadragintillion"),
        (10**141, "Quattuorquadragintillion"),
        (10**138, "Trequadragintillion"),
        (10**135, "Duoquadragintillion"),
        (10**132, "Unquadragintillion"),
        (10**129, "Quadragintillion"), # 10^3 * 43
        (10**126, "Novemtrigintillion"),
        (10**123, "Octotrigintillion"),
        (10**120, "Septentrigintillion"),
        (10**117, "Sextrigintillion"),
        (10**114, "Quintrigintillion"),
        (10**111, "Quattuortrigintillion"),
        (10**108, "Tretrigintillion"),
        (10**105, "Duotrigintillion"),
        (10**102, "Untrigintillion"),
        (10**99, "Trigintillion"), # 10^3 * 33
        (10**96, "Novemvigintillion"),
        (10**93, "Octovigintillion"),
        (10**90, "Septenvigintillion"),
        (10**87, "Sexvigintillion"),
        (10**84, "Quinvigintillion"),
        (10**81, "Quattuorvigintillion"),
        (10**78, "Trevigintillion"),
        (10**75, "Duovigintillion"),
        (10**72, "Unvigintillion"),
        (10**69, "Vigintillion"), # 10^3 * 23
        (10**66, "Novemdecillion"),
        (10**63, "Octodecillion"),
        (10**60, "Septendecillion"),
        (10**57, "Sexdecillion"),
        (10**54, "Quindecillion"),
        (10**51, "Quattuordecillion"),
        (10**48, "Tredecillion"),
        (10**45, "Duodecillion"),
        (10**42, "Undecillion"),
        (10**39, "Decillion"),
        (10**36, "Nonillion"),
        (10**33, "Octillion"),
        (10**30, "Septillion"),
        (10**27, "Sextillion"),
        (10**24, "Quintillion"),
        (10**21, "Quadrillion"),
        (10**18, "Trillion"),
        (10**15, "Billion"),
        (10**12, "Million"),
        (10**9, "Thousand") # This should be 10^3, i.e., 10^9 should be Billion, 10^12 Trillion etc.
    ]

    # Re-evaluating suffixes for correct powers of 1000
    # Standard long scale:
    # 10^0: None
    # 10^3: Thousand
    # 10^6: Million
    # 10^9: Billion
    # 10^12: Trillion
    # 10^15: Quadrillion
    # 10^18: Quintillion
    # 10^21: Sextillion
    # 10^24: Septillion
    # 10^27: Octillion
    # 10^30: Nonillion
    # 10^33: Decillion
    # ... and so on, each increment of 3 in the exponent gets a new suffix.

    # Corrected and expanded suffixes list
    suffixes = [
        (10**303, "Centillion"), # 10^(3*101)
        (10**300, "NovemNovemDecillion"), # 10^(3*100) - Placeholder for very large numbers
        (10**297, "OctoNovemDecillion"), # 10^(3*99)
        (10**294, "SeptenNovemDecillion"), # 10^(3*98)
        (10**291, "SexNovemDecillion"),
        (10**288, "QuinNovemDecillion"),
        (10**285, "QuattuorNovemDecillion"),
        (10**282, "TreNovemDecillion"),
        (10**279, "DuoNovemDecillion"),
        (10**276, "UnNovemDecillion"),
        (10**273, "NovemOctogintillion"), # 10^(3*91)
        (10**270, "OctoOctogintillion"),
        (10**267, "SeptenOctogintillion"),
        (10**264, "SexOctogintillion"),
        (10**261, "QuinOctogintillion"),
        (10**258, "QuattuorOctogintillion"),
        (10**255, "TreOctogintillion"),
        (10**252, "DuoOctogintillion"),
        (10**249, "UnOctogintillion"),
        (10**246, "Octogintillion"), # 10^(3*82)
        (10**243, "Septuagintillion"), # 10^(3*81)
        (10**240, "Sexagintillion"), # 10^(3*80)
        (10**237, "Quinquagintillion"), # 10^(3*79)
        (10**234, "Quadragintillion"), # 10^(3*78)
        (10**231, "Trigintillion"), # 10^(3*77)
        (10**228, "Vigintillion"), # 10^(3*76)
        (10**225, "Decillion"), # 10^(3*75)
        (10**222, "Nonillion"), # 10^(3*74)
        (10**219, "Octillion"), # 10^(3*73)
        (10**216, "Septillion"), # 10^(3*72)
        (10**213, "Sextillion"), # 10^(3*71)
        (10**210, "Quintillion"), # 10^(3*70)
        (10**18, "Quintillion"), # Standard quintillion is 10^18. This was the source of error.
        (10**15, "Quadrillion"),
        (10**12, "Trillion"),
        (10**9, "Billion"),
        (10**6, "Million"),
        (10**3, "Thousand")
    ]
    
    # Re-correcting the suffixes to be standard and comprehensive:
    # A standard list of numerical suffixes (short scale is common in US/Canada, long scale in Europe).
    # We are using the "short scale" where each new suffix is 1000 times the previous one.
    # 10^3 = Thousand
    # 10^6 = Million
    # 10^9 = Billion
    # 10^12 = Trillion
    # 10^15 = Quadrillion
    # 10^18 = Quintillion
    # 10^21 = Sextillion
    # 10^24 = Septillion
    # 10^27 = Octillion
    # 10^30 = Nonillion
    # 10^33 = Decillion
    # ... and so on. We need to extend this systematically.
    
    suffixes = []
    # Base units
    suffixes.append((10**0, "")) # For numbers less than 1000
    suffixes.append((10**3, "Thousand"))
    suffixes.append((10**6, "Million"))
    suffixes.append((10**9, "Billion"))
    suffixes.append((10**12, "Trillion"))
    suffixes.append((10**15, "Quadrillion"))
    suffixes.append((10**18, "Quintillion"))
    suffixes.append((10**21, "Sextillion"))
    suffixes.append((10**24, "Septillion"))
    suffixes.append((10**27, "Octillion"))
    suffixes.append((10**30, "Nonillion"))
    suffixes.append((10**33, "Decillion"))
    suffixes.append((10**36, "Undecillion"))
    suffixes.append((10**39, "Duodecillion"))
    suffixes.append((10**42, "Tredecillion"))
    suffixes.append((10**45, "Quattuordecillion"))
    suffixes.append((10**48, "Quindecillion"))
    suffixes.append((10**51, "Sexdecillion"))
    suffixes.append((10**54, "Septendecillion"))
    suffixes.append((10**57, "Octodecillion"))
    suffixes.append((10**60, "Novemdecillion"))
    suffixes.append((10**63, "Vigintillion")) # 10^3 * 21 = 10^63
    # We can continue this pattern up to the float limit if needed.
    # Python's float max is around 1.79e308.
    # The suffix for 10^303 is Centillion.
    suffixes.append((10**66, "Unvigintillion"))
    suffixes.append((10**69, "Duovigintillion"))
    suffixes.append((10**72, "Trevigintillion"))
    suffixes.append((10**75, "Quattuorvigintillion"))
    suffixes.append((10**78, "Quinvigintillion"))
    suffixes.append((10**81, "Sexvigintillion"))
    suffixes.append((10**84, "Septenvigintillion"))
    suffixes.append((10**87, "Octovigintillion"))
    suffixes.append((10**90, "Novemvigintillion"))
    suffixes.append((10**93, "Trigintillion")) # 10^3 * 31
    suffixes.append((10**96, "Untrigintillion"))
    suffixes.append((10**99, "Duotrigintillion"))
    suffixes.append((10**102, "Tretrigintillion"))
    suffixes.append((10**105, "Quattuortrigintillion"))
    suffixes.append((10**108, "Quinquatrigintillion"))
    suffixes.append((10**111, "Sexatrigintillion"))
    suffixes.append((10**114, "Septentrigintillion"))
    suffixes.append((10**117, "Octotrigintillion"))
    suffixes.append((10**120, "Novemtrigintillion"))
    suffixes.append((10**123, "Quadragintillion")) # 10^3 * 41
    suffixes.append((10**153, "Quinquagintillion")) # 10^3 * 51
    suffixes.append((10**183, "Sexagintillion")) # 10^3 * 61
    suffixes.append((10**213, "Septuagintillion")) # 10^3 * 71
    suffixes.append((10**243, "Octogintillion")) # 10^3 * 81
    suffixes.append((10**273, "Nonagintillion")) # 10^3 * 91
    suffixes.append((10**303, "Centillion")) # 10^3 * 101

    # Sort suffixes in descending order of their value (important for correct lookup)
    suffixes.sort(key=lambda x: x[0], reverse=True)

    for value, suffix in suffixes:
        if num >= value:
            # Round to two decimal places for the magnitude
            # Using max(1, value) to prevent division by zero if suffix value is 0 (though it shouldn't be for non-empty suffix)
            # Also, handle cases where num is exactly the value to avoid showing "1.00 Thousand Liters" for 1000 Liters, etc.
            if value == 1: # For numbers less than 1000, no suffix
                return f"{num:,.2f} {unit_str}"
            else:
                rounded_num = round(num / value, 2)
                return f"{rounded_num:,.2f} {suffix} {unit_str}"

    return f"{num:,.2f} {unit_str}" # Fallback for very small numbers (should be caught by num < 1) or if list exhausted


def describe_volume(volume_liters):
    """
    Compares the given volume in liters to known water body volumes and celestial bodies
    and returns a descriptive string.
    """
    if volume_liters <= 0:
        return "No volume or invalid volume."
    if volume_liters == float('inf'):
        return "This volume is astronomically large, far exceeding all known water bodies and even the largest planets in our solar system."

    # First check water bodies
    for description, limits in WATER_BODY_VOLUMES.items():
        if limits["min"] <= volume_liters < limits["max"]:
            return f"This volume could fill {description}."
    
    # Then check planets
    if volume_liters < PLANET_VOLUMES["Planet Mars"]:
        return "This volume is larger than all Earth's oceans, but less than the volume of Planet Mars."
    elif volume_liters < PLANET_VOLUMES["Planet Earth"]:
        # Calculate percentage of Mars's volume
        percentage_of_mars = (volume_liters / PLANET_VOLUMES['Planet Mars']) * 100
        return f"This volume could fill approximately {percentage_of_mars:.2f}% of Planet Mars's volume."
    elif volume_liters < PLANET_VOLUMES["Planet Jupiter"]:
        # Calculate percentage of Earth's volume
        percentage_of_earth = (volume_liters / PLANET_VOLUMES['Planet Earth']) * 100
        return f"This volume could fill approximately {percentage_of_earth:.2f}% of Planet Earth's volume."
    else:
        # Calculate percentage of Jupiter's volume
        percentage_of_jupiter = (volume_liters / PLANET_VOLUMES['Planet Jupiter']) * 100
        return f"This volume could fill approximately {percentage_of_jupiter:.2f}% of Planet Jupiter's volume (or even more)!"


def calculate_time_to_fill(current_volume, target_volume, rate_per_unit_time_liters, unit_time):
    """
    Calculates the estimated time to fill a target volume given a current volume and a rate.
    Returns a formatted string or "N/A" if not applicable or calculation is impossible.
    """
    if current_volume >= target_volume:
        return "Already filled or exceeded."
    if rate_per_unit_time_liters <= 0:
        return "Rate must be positive."
    if target_volume == float('inf') or current_volume == float('inf'):
        return "N/A (Target or current volume is infinite)"

    remaining_volume = target_volume - current_volume
    if remaining_volume <= 0:
        return "Already filled or exceeded."

    time_units = remaining_volume / rate_per_unit_time_liters

    if unit_time == "second":
        # Convert seconds to more readable units
        if time_units < 60:
            return f"~{time_units:.2f} seconds"
        elif time_units < 3600:
            return f"~{time_units / 60:.2f} minutes"
        elif time_units < 86400:
            return f"~{time_units / 3600:.2f} hours"
        elif time_units < 31536000: # seconds in a year
            return f"~{time_units / 86400:.2f} days"
        else:
            return f"~{time_units / 31536000:.2f} years"
    elif unit_time == "minute":
        if time_units < 60:
            return f"~{time_units:.2f} minutes"
        elif time_units < 1440:
            return f"~{time_units / 60:.2f} hours"
        elif time_units < 525600:
            return f"~{time_units / 1440:.2f} days"
        else:
            return f"~{time_units / 525600:.2f} years"
    elif unit_time == "hour":
        if time_units < 24:
            return f"~{time_units:.2f} hours"
        elif time_units < 8760: # hours in a year
            return f"~{time_units / 24:.2f} days"
        else:
            return f"~{time_units / 8760:.2f} years"
    elif unit_time == "day":
        if time_units < 365:
            return f"~{time_units:.2f} days"
        else:
            return f"~{time_units / 365:.2f} years"
    elif unit_time == "year":
        return f"~{time_units:.2f} years"
    else:
        return "N/A (Invalid time unit)"


def perform_calculation(initial_volume_str, unit, iterations_str, time_rate_liters_per_unit=None, time_unit=None):
    """
    Performs the water volume compounding calculation.
    Returns a list of dictionaries with results or raises ValueError for invalid input.
    Includes raw volume for charting (even if not used on frontend, kept for consistency/future).
    """
    try:
        initial_volume = float(initial_volume_str)
        iterations = int(iterations_str)

        if initial_volume <= 0 or iterations <= 0:
            raise ValueError("Initial volume and iterations must be positive numbers.")
        if iterations > 100:
            raise ValueError("Number of iterations cannot exceed 100 to prevent performance issues and ensure reasonable output.")

        # Convert initial volume to liters
        if unit == 'gallons':
            initial_volume_liters = initial_volume * GALLONS_TO_LITERS
        else: # litres
            initial_volume_liters = initial_volume

        results = []
        current_volume_liters_raw = 0

        # Max float value for `sys.float_info.max` is approx 1.797e+308
        MAX_FLOAT_HALF = sys.float_info.max / 2

        # First iteration: initial_volume * initial_volume
        if iterations >= 1:
            if initial_volume_liters == 0:
                current_volume_liters_raw = 0
            elif abs(initial_volume_liters) > math.sqrt(sys.float_info.max):
                current_volume_liters_raw = float('inf')
            else:
                current_volume_liters_raw = initial_volume_liters * initial_volume_liters

            time_to_fill_str = "N/A"
            if time_rate_liters_per_unit and time_unit:
                try:
                    rate_val = float(time_rate_liters_per_unit)
                    target_fill_volume = 0
                    if current_volume_liters_raw < WATER_BODY_VOLUMES["a small pond"]["max"]:
                        target_fill_volume = WATER_BODY_VOLUMES["a small pond"]["max"]
                    elif current_volume_liters_raw < WATER_BODY_VOLUMES["a large pond or a small lake"]["max"]:
                        target_fill_volume = WATER_BODY_VOLUMES["a large pond or a small lake"]["max"]
                    elif current_volume_liters_raw < WATER_BODY_VOLUMES["a medium-sized lake"]["max"]:
                        target_fill_volume = WATER_BODY_VOLUMES["a medium-sized lake"]["max"]
                    elif current_volume_liters_raw < WATER_BODY_VOLUMES["a large lake (e.g., Lake Tahoe)"]["max"]:
                        target_fill_volume = WATER_BODY_VOLUMES["a large lake (e.g., Lake Tahoe)"]["max"]
                    elif current_volume_liters_raw < WATER_BODY_VOLUMES["a Great Lake (e.g., Lake Superior)"]["max"]:
                        target_fill_volume = WATER_BODY_VOLUMES["a Great Lake (e.g., Lake Superior)"]["max"]
                    elif current_volume_liters_raw < WATER_BODY_VOLUMES["an entire sea (e.g., Mediterranean Sea)"]["max"]:
                        target_fill_volume = WATER_BODY_VOLUMES["an entire sea (e.g., Mediterranean Sea)"]["max"]
                    elif current_volume_liters_raw < WATER_BODY_VOLUMES["an entire ocean (e.g., Pacific Ocean)"]["max"]:
                        target_fill_volume = WATER_BODY_VOLUMES["an entire ocean (e.g., Pacific Ocean)"]["max"]
                    elif current_volume_liters_raw < PLANET_VOLUMES["Planet Mars"]:
                        target_fill_volume = PLANET_VOLUMES["Planet Mars"]
                    elif current_volume_liters_raw < PLANET_VOLUMES["Planet Earth"]:
                        target_fill_volume = PLANET_VOLUMES["Planet Earth"]
                    elif current_volume_liters_raw < PLANET_VOLUMES["Planet Jupiter"]:
                        target_fill_volume = PLANET_VOLUMES["Planet Jupiter"]

                    if target_fill_volume > 0 and current_volume_liters_raw != float('inf'):
                         time_to_fill_str = calculate_time_to_fill(current_volume_liters_raw, target_fill_volume, rate_val, time_unit)
                except ValueError:
                    time_to_fill_str = "Invalid rate"


            results.append({
                "iteration": 1,
                "volume_liters_raw": current_volume_liters_raw, # Kept for potential future use or debugging
                "volume_liters": format_large_number_spoken(current_volume_liters_raw, "Liters"),
                "volume_gallons": format_large_number_spoken(current_volume_liters_raw / GALLONS_TO_LITERS, "Gallons") if current_volume_liters_raw != float('inf') else "Infinity",
                "description": describe_volume(current_volume_liters_raw),
                "time_to_fill": time_to_fill_str
            })

        # Subsequent iterations: compound by 100% (multiply by 2)
        for i in range(2, iterations + 1):
            if current_volume_liters_raw == float('inf'): # Once it's infinity, it stays infinity
                results.append({
                    "iteration": i,
                    "volume_liters_raw": float('inf'),
                    "volume_liters": "Infinity",
                    "volume_gallons": "Infinity",
                    "description": describe_volume(float('inf')),
                    "time_to_fill": "N/A"
                })
                continue

            # Check for potential overflow before multiplying by 2
            if current_volume_liters_raw > MAX_FLOAT_HALF:
                current_volume_liters_raw = float('inf')
            else:
                current_volume_liters_raw *= 2 # 100% increase means multiplying by 2

            time_to_fill_str = "N/A"
            if time_rate_liters_per_unit and time_unit:
                try:
                    rate_val = float(time_rate_liters_per_unit)
                    target_fill_volume = 0
                    
                    # Determine target for time_to_fill based on current volume
                    if current_volume_liters_raw != float('inf'):
                        # Find the next water body/planet volume that is larger than current_volume_liters_raw
                        sorted_comparison_targets = sorted(
                            list(WATER_BODY_VOLUMES.values()) + list(map(lambda v: {"max": v}, PLANET_VOLUMES.values())),
                            key=lambda x: x["max"]
                        )
                        for target in sorted_comparison_targets:
                            if current_volume_liters_raw < target["max"]:
                                target_fill_volume = target["max"]
                                break
                    
                    if target_fill_volume > 0 and current_volume_liters_raw < target_fill_volume:
                        time_to_fill_str = calculate_time_to_fill(current_volume_liters_raw, target_fill_volume, rate_val, time_unit)
                except ValueError:
                    time_to_fill_str = "Invalid rate"


            results.append({
                "iteration": i,
                "volume_liters_raw": current_volume_liters_raw,
                "volume_liters": format_large_number_spoken(current_volume_liters_raw, "Liters"),
                "volume_gallons": format_large_number_spoken(current_volume_liters_raw / GALLONS_TO_LITERS, "Gallons") if current_volume_liters_raw != float('inf') else "Infinity",
                "description": describe_volume(current_volume_liters_raw),
                "time_to_fill": time_to_fill_str
            })
        return results

    except ValueError as e:
        raise e
    except Exception as e:
        app.logger.error(f"An unexpected error occurred during calculation: {e}", exc_info=True)
        raise Exception("An internal error occurred during calculation.")


@app.route('/')
def index():
    """Renders the main page of the application."""
    # No longer passing comparison_lines_json as charts are removed
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate_volume():
    """
    Handles the calculation of compounded water volume based on user input.
    Returns results as JSON.
    """
    initial_volume = request.form['initial_volume']
    unit = request.form['unit']
    iterations = request.form['iterations']
    time_rate_liters_per_unit = request.form.get('time_rate')
    time_unit = request.form.get('time_unit')

    try:
        results = perform_calculation(initial_volume, unit, iterations, time_rate_liters_per_unit, time_unit)
        return jsonify(results)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/export_excel', methods=['POST'])
def export_excel():
    """
    Exports the calculation results to an Excel file.
    """
    initial_volume = request.form['initial_volume_excel']
    unit = request.form['unit_excel']
    iterations = request.form['iterations_excel']
    time_rate_liters_per_unit = request.form.get('time_rate_excel')
    time_unit = request.form.get('time_unit_excel')


    try:
        results = perform_calculation(initial_volume, unit, iterations, time_rate_liters_per_unit, time_unit)

        # Create a Pandas DataFrame
        df = pd.DataFrame(results)
        
        # Rename columns for better Excel readability
        df.rename(columns={
            'iteration': 'Iteration',
            'volume_liters': 'Volume (Litres)',
            'volume_gallons': 'Volume (Gallons)',
            'description': 'Comparison',
            'time_to_fill': 'Time to Fill (Estimate)'
        }, inplace=True)

        # Drop the raw volume column before export - this is correct for Excel
        df.drop(columns=['volume_liters_raw'], inplace=True)

        # Create an in-memory BytesIO object to save the Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Water Volume Compounding')
        output.seek(0) # Go to the beginning of the stream

        return send_file(output, as_attachment=True, download_name='water_volume_compounding_results.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"An unexpected error occurred during Excel export: {e}", exc_info=True)
        return jsonify({"error": "An internal server error occurred during export. Please try again later."}), 500


if __name__ == '__main__':
    app.run(debug=True)