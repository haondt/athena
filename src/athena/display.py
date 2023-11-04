from .run import ExecutionTrace
from .format import short_format_error


def responses(trace: ExecutionTrace):
    output = ""
    output_max_width = 60

    output += f"environment: {trace.environment}\n"

    if not trace.success:
        if trace.error is not None:
            output += f"Warning: execution failed to complete successfully, with error {short_format_error(trace.error)}\n"
        else:
            output += "Warning: execution failed to complete successfully\n"
    elif trace.error is not None:
        output += f"Warning: execution completed with, with error {short_format_error(trace.error)}\n"

    output += f"{trace.module_key}\n"
    if len(trace.athena_traces) > 0:
        output += f"{_create_duration_view(trace, output_max_width)}\n"

    return output

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
    max_duration = max([i[2]-i[1] for i in time_data])
    unit = ""
    format = lambda x: x
    if max_duration > 1:
        unit = "s"
        format = lambda t: "{:.3g}".format(t, 3)
    else:
        unit = "ms"
        format = lambda t: "{:.3g}".format(t*1000, 3)
    max_line_len = output_max_width - len(seperator) - name_len - len(unit) - 4
    if max_line_len < 1:
        return ""
    
    output = []
    for name, trace_start, trace_end in time_data:
        line = " "*max_line_len
        start_position = int(round(((trace_start-start) / duration)*max_line_len))
        end_position = int(round(((trace_end-start) / duration)*max_line_len))
        line = line[:start_position] + "·"*(end_position - start_position + 1) + " "
        output.append(f"{name}{seperator}{line}{format(trace_end-trace_start)}{unit}")

    return "\n".join(output)
