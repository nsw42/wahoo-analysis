import argparse
import fitdecode
import logging


# logging.basicConfig(level=logging.DEBUG)

get_row_power = lambda data, i: data[i].get('power', (0, None))[0]

def find_max_power(data, interval_power, interval_duration, search_range):
    start_of_interval = 0
    while start_of_interval < len(data):
        for i in range(start_of_interval, min(len(data), start_of_interval + interval_duration)):
            if get_row_power(data, i) < interval_power:
                break
        else:
            break

        start_of_interval += 1

    max_power = 0
    index = None
    for i in range(start_of_interval, min(len(data), start_of_interval + search_range)):
        power = get_row_power(data, i)
        if power > max_power:
            index, max_power = i, power
    logging.debug("start_of_interval = %u, peak index = %u, max_power = %u", start_of_interval, index, max_power)
    return index


def sum_power_range(data, start, durn):
    total = 0
    row = start
    for row in data[start:start+durn]:
        total += row['power'][0]
    return total


def find_max_power_range(data, peak_power_index, durn):
    start = max(0, peak_power_index - durn + 1)
    max_total_power = 0
    start_of_best_range = None
    while start <= peak_power_index:
        total_power_from_start = sum_power_range(data, start, durn)
        if total_power_from_start > max_total_power:
            start_of_best_range, max_total_power = start, total_power_from_start
        start += 1
    return start_of_best_range, start_of_best_range + durn, max_total_power


def find_intervals(data, reps, warmup_time, recovery_power, recovery_duration, interval_power, interval_duration):
    intervals = []
    del data[:max(0, warmup_time - recovery_duration)]
    while reps:
        rep_durn = reps.pop(0)
        max_power_i = find_max_power(data, interval_power, interval_duration, rep_durn + 2 * recovery_duration)
        # we have a local maximum - now find the range around it
        # that maximises the total power output
        begin, end, total_power = find_max_power_range(data, max_power_i, rep_durn)
        average_power = total_power / rep_durn
        row = (data[begin]['timestamp'][0], data[end-1]['timestamp'][0], get_row_power(data, max_power_i), average_power)
        intervals.append(row)
        del data[:end]
    return intervals



def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--warmup-time', type=int,
                        help="Amount of the recording to skip (seconds)")
    parser.add_argument('--recovery-power', type=int,
                        help="Maximum power in a recovery interval (watts)")
    parser.add_argument('--recovery-duration', type=int,
                        help="Contiguous duration no greater than recovery-power to identify a recovery interval (seconds)")
    parser.add_argument('--interval-power', type=int,
                        help="Minimum power to find when looking for an interval (watts)")
    parser.add_argument('--interval-duration', type=int,
                        help="Contiguous duration no lower than interval-power to identify a workout interval (seconds)")
    parser.add_argument('fit', help='Input .fit file')
    parser.add_argument('reps', help='Specification of repetitions to detect', nargs='+')
    parser.set_defaults(warmup_time=0,
                        recovery_power=150,
                        recovery_duration=10,
                        interval_power=250,
                        interval_duration=10)
    args = parser.parse_args()
    return args


def parse_durn(durn):
    """
    >>> parse_durn('30s')
    30
    >>> parse_durn('1m')
    60
    >>> parse_durn('1m30s')
    90
    >>> parse_durn('1')
    >>> parse_durn('5m3')
    """
    durn_value = 0
    while durn:
        if not durn[0].isdigit():
            return None
        i = 0
        while (i < len(durn)) and (durn[i].isdigit()):
            i += 1
        if i >= len(durn):
            return None
        chunk = int(durn[:i])
        unit = durn[i]
        durn = durn[i+1:]
        if unit == 'm':
            unit = 60
        elif unit == 's':
            unit = 1
        else:
            return None
        durn_value += chunk * unit
    return durn_value


def parse_reps(reps_list):
    rtn_reps = []
    for reps in reps_list:
        if 'x' not in reps:
            raise Exception("Invalid reps")
        n, durn = reps.split('x', 1)
        if not n.isdigit():
            raise Exception("invalid reps")
        n = int(n)
        durn = parse_durn(durn)
        reps = n * [durn]
        rtn_reps.extend(reps)
    return rtn_reps


def read_input_file(filename):
    rows = []
    with fitdecode.FitReader(filename) as fit:
        for frame in fit:
            if isinstance(frame, fitdecode.FitDataMessage):
                if frame.name != 'record':
                    continue
                timestamp = None
                row = {}
                for field in frame.fields:
                    if field.name in ('vertical_oscillation', 'stance_time'):
                        continue
                    if field.name == 'timestamp':
                        if 'power' in row:
                            rows.append(row)
                        indent = ''
                        row = {}
                    else:
                        indent = '   '
                    row[field.name] = (field.value, field.units)
                if 'power' in row:
                    rows.append(row)
    return rows


def main():
    args = parse_args()
    reps = parse_reps(args.reps)
    data = read_input_file(args.fit)
    intervals = find_intervals(data, reps, args.warmup_time, args.recovery_power, args.recovery_duration, args.interval_power, args.interval_duration)
    for row in intervals:
        start, end, max_power, avg_power = row
        print(start, end, max_power, avg_power)


if __name__ == '__main__':
    main()
