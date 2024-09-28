from decimal import Decimal

# function to round off trade volume to the same decimal places as min volume
def round_to_ref(number_to_round: float, reference_number: float):
    # Get the number of decimal places in the reference_number
    decimal_places = abs(Decimal(str(reference_number)).as_tuple().exponent)

    # Round the number_to_round to the same decimal places
    rounded_number = round(number_to_round, decimal_places)

    return rounded_number