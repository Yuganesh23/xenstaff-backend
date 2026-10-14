from decimal import Decimal, ROUND_HALF_UP

def round_currency(value, decimal_places=2):
    """
    Rounds a Decimal or numeric value using ROUND_HALF_UP.
    """
    if value is None:
        return Decimal('0.00')
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    
    if decimal_places == 0:
        return value.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    
    exponent = Decimal('10') ** -decimal_places
    return value.quantize(exponent, rounding=ROUND_HALF_UP)

def format_inr(number):
    """
    Formats a number into Indian Lakhs/Crores currency format.
    Example: 1234567.89 -> 12,34,567.89
    """
    if number is None:
        return "₹0.00"
    
    dec = round_currency(number, 2)
    s = f"{dec:.2f}"
    parts = s.split('.')
    integer_part = parts[0]
    decimal_part = parts[1]

    is_negative = integer_part.startswith('-')
    if is_negative:
        integer_part = integer_part[1:]

    if len(integer_part) <= 3:
        formatted = integer_part
    else:
        last_three = integer_part[-3:]
        remaining = integer_part[:-3]
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        groups.append(last_three)
        formatted = ','.join(groups)

    result = f"₹{'-' if is_negative else ''}{formatted}.{decimal_part}"
    return result
