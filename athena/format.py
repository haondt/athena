class colors:
    _reset = "\x1B[0m"
    bold = "1"
    italic = "3"
    underline = "4"
    strikethrough = "9"

    red = "31"
    green = "32"
    yellow = "33"
    blue = "34"
    magenta = "35"
    cyan = "36"
    white = "37"

    brightred = "91"
    brightgreen = "92"
    brightyellow = "93"
    brightblue = "94"
    brightmagenta = "95"
    brightcyan = "96"
    brightwhite = "97"

def color(text, *effects):
    if len(effects) == 0:
        return text
    codes = ";".join(effects)
    return f"\x1B[{codes}m{text}{colors._reset}"

def indent(text, level, indentation=None, indent_empty_lines=False):
    if level == 0:
        return text

    new = []
    indentation = indentation or "    "
    indentation = "".join([indentation]*level)
    for line in text.split("\n"):
        if indent_empty_lines or len(line.strip()) > 0:
            new.append(f"{indentation}{line}")
        else:
            new.append(line)
    return "\n".join(new)
