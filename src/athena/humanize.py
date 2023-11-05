def delta(
        value_in_seconds: float | int
        ) -> str:
    
    milliseconds = value_in_seconds * 1000
    seconds = value_in_seconds
    minutes = value_in_seconds / 60
    hours = value_in_seconds / 60 / 60
    days = value_in_seconds / 60 / 60 / 24

    for amount, unit in [
            (days, 'd'),
            (hours, 'h'),
            (minutes, 'm'),
            (seconds, 's'),
            ]:
        if amount >= 1:
            return "{:.3g}".format(amount) + unit
    return "{:.3g}".format(milliseconds) + 'ms'

def bytes(
        value: float | int
        ) -> str:
    value = int(value)

    for prefix in ["", "K", "M", "G", "T"]:
        if value <= 1000:
            return "{:.3g}".format(value) + prefix + "B"
        value /= 1000
    return "{:.3g}".format(value) + "PB"
