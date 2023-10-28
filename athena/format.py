import traceback

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

def short_format_error(err: Exception):
    return f"{err.__class__.__name__}: {str(err)}"

def long_format_error(err: Exception, truncate_trace: bool=True):
    frames = traceback.extract_tb(err.__traceback__)
    if truncate_trace:
        frames = [frames[-1]]
    message = "\n".join([_long_format_frame(f) for f in frames])
    message += f"\n{err.__class__.__name__}: {str(err)}"
    return message
def _long_format_frame(frame):
    underline = [" "]*frame.colno
    if frame.lineno == frame.end_lineno: 
        underline += ["^"]*(frame.end_colno - frame.colno)
    else:
        underline += ["^"]*(len(frame._line.rstrip()) - len(underline))
    underline = ''.join(underline)
    s = f"File \"{frame.filename}\", line {frame.lineno}, in {frame.name}\n{frame._line.rstrip()}\n{underline}"
    return s

def pretty_format_error(err: Exception, truncate_trace: bool=True):
    frames = traceback.extract_tb(err.__traceback__)
    if truncate_trace:
        frames = [frames[-1]]
    message = "\n".join([_pretty_format_frame(f) for f in frames])
    message += f"\n{color(err.__class__.__name__ + ':', colors.red)} {str(err)}"
    return message
def _pretty_format_frame(frame):
    captured_lines = []
    with open(frame.filename, "r") as f:
        i = 1
        for line in f:
            if i >= frame.lineno:
                captured_lines.append(line)
            i += 1
            if i > frame.end_lineno:
                break

    head = captured_lines[0][:frame.colno]
    body = ""
    tail = ""
    if len(captured_lines) == 1:
        body = captured_lines[0][frame.colno:frame.end_colno]
        tail = captured_lines[0][frame.end_colno:]
    else:
        body = captured_lines[0][frame.colno:]
        for line in captured_lines[1:-1]:
            body += line
        body += captured_lines[-1][:frame.end_colno]
        tail = captured_lines[-1][frame.end_colno:]
    colored_body = "\n".join([color(i, colors.bold, colors.brightred) for i in body.split("\n")])

    s = f"File \"{color(frame.filename, colors.italic)}\", line {frame.lineno}, in {color(frame.name, colors.bold)}"
    s += f"\n{head + colored_body + tail}"
    return s
