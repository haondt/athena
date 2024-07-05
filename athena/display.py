from athena.athena_json import jsonify
from .run import ExecutionTrace
from .format import short_format_error, color, colors, indent, rtruncate
from . import humanize
import random
import re
import json
import xml.etree.ElementTree as xmlET
from pygments import highlight
from pygments.formatters import TerminalFormatter
from urllib.parse import parse_qsl

_color_list = [
    colors.red,
    colors.green,
    colors.yellow,
    colors.blue,
    colors.magenta,
    colors.cyan,
    colors.white,
    colors.brightred,
    colors.brightgreen,
    colors.brightyellow,
    colors.brightblue,
    colors.brightmagenta,
    colors.brightcyan,
    colors.brightwhite,
]

def _is_json(content_type: str) -> bool:
    json_re = re.compile(r"^application/(?:[\w.+-]+?\+)?json")
    return json_re.match(content_type) is not None

def _try_prettify_json(text: str) -> str | None:
    try:
        text = json.dumps(json.loads(text), indent=2)
    except:
        pass
    try:
        from pygments.lexers.data import JsonLexer
        lexer = JsonLexer()
        return highlight(text, lexer, formatter)
    except:
        return None

def _is_html(content_type: str) -> bool:
    return content_type == "text/html"

def _try_prettify_html(text: str) -> str | None:
    try:
        root = xmlET.fromstring(text)
        text = xmlET.tostring(root, encoding='unicode', method='xml')
    except:
        pass
    try:
        from pygments.lexers import html
        lexer = html.HtmlLexer()
        return highlight(text, lexer, formatter)
    except:
        return None

def _is_xml(content_type: str) -> bool:
    return content_type == "text/xml"

def _try_prettify_xml(text: str) -> str | None:
    try:
        root = xmlET.fromstring(text)
        text = xmlET.tostring(root, encoding='unicode', method='xml')
    except:
        pass
    try:
        from pygments.lexers import html
        lexer = html.XmlLexer()
        return highlight(text, lexer, formatter)
    except:
        return None

def _is_url_encoded_form(content_type: str) -> bool:
    return content_type == "application/x-www-form-urlencoded"

def _try_prettify_url_encoded_form(text: str) -> str | None:
    try:
        data = parse_qsl(text)
        lines = []
        for k, v in data:
            lines.append(f'{k}{color("=", colors.brightred)}{v}')
        return '\n'.join(lines) + '\n'
    except:
        return None

formatter = TerminalFormatter()

def trace_plain(trace: ExecutionTrace, include_requests: bool, include_responses: bool) -> str:
    jsonified = jsonify(trace.as_serializable())
    if include_requests and include_responses:
        return jsonified
    copy = json.loads(jsonified)
    for athena_trace in copy['athena_traces']:
        if not include_requests:
            del athena_trace['request']
        if not include_responses:
            del athena_trace['response']
    return json.dumps(copy)

def trace(trace: ExecutionTrace, include_requests: bool, include_responses: bool):
    output = []
    #min_width = 40
    #max_width = 165
    output_width = 60

    def main_header() -> str:
        section_output = ""
        success_color = colors.green if trace.success else colors.red
        section_output += f"{color(trace.module_name, colors.underline, colors.bold)} {color('•', success_color)}"
        return section_output

    def sub_header() -> str:
        section_output = ""
        section_output += f"environment: {trace.environment}"
        if not trace.success:
            if trace.error is not None:
                section_output += f"\n{color('Warning:', colors.yellow)} execution failed to complete successfully\n{color(short_format_error(trace.error), colors.brightred)}"
            else:
                section_output += f"\n{color('Warning:', colors.yellow)} execution failed to complete successfully"
        elif trace.error is not None:
            section_output += f"\n{color('Warning:', colors.yellow)} execution completed with errors\n{color(short_format_error(trace.error), colors.brightyellow)}"
        return section_output

    def duration_view():
        assert len(trace.athena_traces) > 0
        return f"{_create_duration_view(trace, output_width)}"
    def trace_digests(include_requests: bool, include_responses: bool):
        assert len(trace.athena_traces) > 0
        digests = []
        for athena_trace in trace.athena_traces:
            entry = []
            meta_info =  "\n".join([
                f"{color(athena_trace.request.method, colors.bold)} {athena_trace.request.url}",
                f"{color(athena_trace.response.status_code, colors.brightgreen)} {color(athena_trace.response.reason, colors.green)} {humanize.delta(athena_trace.end-athena_trace.start)}"
                ])
            entry.append(("", [meta_info]))

            if len(athena_trace.warnings) > 0:
                entry.append((color("warnings", colors.underline, colors.yellow, colors.bold), athena_trace.warnings))

            max_header_key_len = min(max([len(i) for i in athena_trace.response.headers.keys()]), output_width // 2 - 3)
            max_header_value_len =  output_width - max_header_key_len

            def request_digest():
                request_entry = []
                header_info = []
                for key, value in athena_trace.request.headers.items():
                    if len(key) > max_header_key_len:
                        key = rtruncate(key, max_header_key_len)
                    if len(key) < max_header_key_len:
                        key = key.ljust(max_header_key_len)
                    if len(value) > max_header_value_len:
                        value = rtruncate(value, max_header_value_len)
                    header_info.append(f"{color(key, colors.brightwhite)} | {value}")
                header_info = "\n".join(header_info)
                request_entry.append((color("headers", colors.underline), [header_info]))

                body_info = []
                line_numbers = True
                
                body_text = athena_trace.request.text
                render_method = "text"
                if athena_trace.request.content_type is not None:
                    for check, func, rm in [
                            (_is_json, _try_prettify_json, "json", ),
                            (_is_html, _try_prettify_html, "html"),
                            (_is_xml, _try_prettify_xml, "xml"),
                            (_is_url_encoded_form, _try_prettify_url_encoded_form, "form")
                            ]:
                        if check(athena_trace.request.content_type):
                            result = func(body_text)
                            if result is not None:
                                body_text = result
                                render_method = rm
                                break
                if line_numbers:
                    numbered_text = []
                    for i, line in enumerate(body_text.split("\n")[:-1]):
                        numbered_text.append(color(f"{i+1}", colors.brightwhite) + " " + line)
                    body_text = "\n".join(numbered_text) + "\n"
                    
                body_metadata = f"{athena_trace.request.content_type} [{render_method}] {humanize.bytes(len(athena_trace.request.text))}"
                body_info.append(f"{body_text}")

                body_info = "\n".join(body_info)

                if athena_trace.request.content_type is not None or len(athena_trace.request.text) > 0:
                    request_entry.append((f"{color('body', colors.underline)} | {body_metadata}", [body_info]))

                request_entry.append((f'url', [athena_trace.request.url]))
                return request_entry

            def response_digest():
                response_entry = []
                header_info = []
                for key, value in athena_trace.response.headers.items():
                    if len(key) > max_header_key_len:
                        key = rtruncate(key, max_header_key_len)
                    if len(key) < max_header_key_len:
                        key = key.ljust(max_header_key_len)
                    if len(value) > max_header_value_len:
                        value = rtruncate(value, max_header_value_len)
                    header_info.append(f"{color(key, colors.brightwhite)} | {value}")
                header_info = "\n".join(header_info)
                response_entry.append((color("headers", colors.underline), [header_info]))

                body_info = []
                line_numbers = True
                body_text = athena_trace.response.text
                render_method = "text"
                if athena_trace.response.content_type is not None:
                    for check, func, rm in [
                            (_is_json, _try_prettify_json, "json", ),
                            (_is_html, _try_prettify_html, "html"),
                            (_is_xml, _try_prettify_xml, "xml"),
                            (_is_url_encoded_form, _try_prettify_url_encoded_form, "form")
                            ]:
                        if check(athena_trace.response.content_type):
                            result = func(body_text)
                            if result is not None:
                                body_text = result
                                render_method = rm
                                break
                if line_numbers:
                    numbered_text = []
                    for i, line in enumerate(body_text.split("\n")[:-1]):
                        numbered_text.append(color(f"{i+1}", colors.brightwhite) + " " + line)
                    body_text = "\n".join(numbered_text) + "\n"
                    
                body_metadata = f"{athena_trace.response.content_type} [{render_method}] {humanize.bytes(len(athena_trace.response.text))}"
                body_info.append(f"{body_text}")

                body_info = "\n".join(body_info)
                response_entry.append((f"{color('body', colors.underline)} | {body_metadata}", [body_info]))
                return response_entry

            if include_requests:
                entry.append((f"{color('request', colors.bold)}", request_digest()))
            if include_responses:
                entry.append((f"{color('response', colors.bold)}", response_digest()))
            digests.append((athena_trace.name, entry))
        return digests

    main_header_output = []
    output.append((main_header(), main_header_output))
    main_header_output.append((color("execution", colors.underline), [sub_header()]))

    if len(trace.athena_traces) > 0:
        main_header_output.append((color("timings", colors.underline), [duration_view()]))
        digests_output = []
        main_header_output.append((color("traces", colors.underline), digests_output))
        for name, value in trace_digests(include_requests, include_responses):
            digests_output.append((color(name, colors.underline, colors.bold, colors.blue), value))
    return _compute_indented_output(output)

def _create_duration_view(trace: ExecutionTrace, output_max_width: int):
    time_data = []
    start = 0
    end = 0
    max_name_len = 25
    name_len = min(max([len(t.name) for t in trace.athena_traces]), max_name_len)
    for athena_trace in trace.athena_traces:
        name = athena_trace.name
        if len(name) > name_len:
            if name_len < 5:
                name = "..." + name[-(name_len-3):]
            else:
                name = name[:(name_len-3)//2] + "..." + name[-(name_len-3-((name_len-3)//2)):]
        elif len(name) < name_len:
            name = name.center(name_len)
        if start == 0:
            start = athena_trace.start
        end = athena_trace.end
        time_data.append((name, athena_trace.start, athena_trace.end))

    seperator = "    "
    duration = end-start
    expected_duration_len = 6
    max_line_len = output_max_width - len(seperator) - name_len - expected_duration_len - 2
    if max_line_len < 1:
        return ""
    
    output = []
    for name, trace_start, trace_end in time_data:
        line = " "*max_line_len
        start_position = int(round(((trace_start-start) / duration)*max_line_len))
        end_position = int(round(((trace_end-start) / duration)*max_line_len))
        line = line[:start_position] + "·"*(end_position - start_position + 1) + " "
        line_color = random.choice(_color_list)
        line = color(line, line_color)
        output.append(f"{name}{seperator}{line}{humanize.delta(trace_end-trace_start)}")

    return "\n".join(output)

def _compute_indented_output(value) -> str:
    stringified_values = []
    for item in value:
        if isinstance(item, tuple):
            stringified_value = ""
            if len(item[0]) > 0:
                stringified_value += f"{str(item[0])}\n"
            stringified_value += indent(_compute_indented_output(item[1]), 1, '│ ', indent_empty_lines=True)
            stringified_value += "\n"
            stringified_values.append(stringified_value)
        else:
            stringified_values.append(str(item))
    return "\n".join(stringified_values)
