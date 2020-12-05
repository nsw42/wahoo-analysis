import argparse
from collections import namedtuple
import csv
from enum import Enum
import json
import logging
import pathlib
import sys

import fitdecode
import tabulate


PowerReading = namedtuple('PowerReading', ['time', 'power'])
Interval = namedtuple('Interval', ['start', 'end', 'max_power', 'avg_power', 'power_readings'])
FileData = namedtuple('FileData', ['start_time', 'intervals'])
IntervalType = Enum('IntervalType', 'Effort, Recovery')
IntervalDefinition = namedtuple('IntervalDefinition', 'duration, interval_type, name')


class SessionDefinition:
    def __init__(self):
        self.intervals = []  # list of IntervalDefinition

    def add_interval(self, duration: int, interval_type: IntervalType, interval_name: str):
        if self.last_interval_type == interval_type:
            # Add this new interval to the existing one
            new_duration = self.intervals[-1].duration + duration
            new_name = self.intervals[-1].name + '/' + interval_name
            self.intervals[-1] = IntervalDefinition(new_duration, interval_type, new_name)
        else:
            self.intervals.append(IntervalDefinition(duration, interval_type, interval_name))

    @property
    def last_interval_type(self):
        return self.intervals[-1][1] if self.intervals else None


get_row_power = lambda data, i: data[i].get('power', (0, None))[0]

get_row_timestamp = lambda data, i: data[i].get('timestamp', (0, None))[0]


def find_effort_interval(data, interval_power, interval_duration, longest_recovery_duration):
    for start_i in range(min(len(data), longest_recovery_duration)):
        end_i = min(len(data), start_i + interval_duration)
        if all(get_row_power(data, i) >= interval_power for i in range(start_i, end_i)):
            return start_i
    assert False, "Failed to find an effort interval"
    return None


def find_max_power(data, interval_power, interval_duration, search_range):
    """
    Find a local maximum power output
    """
    max_power = 0
    index = None
    for i in range(min(len(data), search_range)):
        power = get_row_power(data, i)
        if power > max_power:
            index, max_power = i, power
    logging.debug("peak index = %u, max_power = %u", index, max_power)
    return index


def sum_power_range(data, start, durn):
    total = 0
    for row in data[start:start + durn]:
        total += row['power'][0]
    return total


def find_max_power_range(data, interval_durn, search_range):
    max_total_power = 0
    start_of_best_range = None
    for start in range(search_range):
        total_power_from_start = sum_power_range(data, start, interval_durn)
        if total_power_from_start > max_total_power:
            start_of_best_range, max_total_power = start, total_power_from_start
    return start_of_best_range, start_of_best_range + interval_durn, max_total_power


def find_intervals(data, session_defn, recovery_duration, interval_power, interval_duration, longest_recovery_duration):
    # TODO: Rename interval_duration to something less confusing
    start_time = get_row_timestamp(data, 0)
    intervals = []
    for interval in session_defn.intervals:
        logging.debug("Looking for interval type %s; search starts at data time %s; duration %s",
                      interval.interval_type,
                      get_row_timestamp(data, 0),
                      interval.duration)
        if interval.interval_type == IntervalType.Recovery:
            if -1 == interval.duration:
                # Use some heuristics to figure out where the next interval starts
                next_interval_start = find_effort_interval(data,
                                                           interval_power,
                                                           interval_duration,
                                                           longest_recovery_duration)
            else:
                next_interval_start = interval.duration - interval_duration
            del data[:next_interval_start]

        else:
            # We know that the previous block was a recovery block, which has been removed from the input data,
            # taking us close to the effort interval.  Now search from here to find the best (=highest effort)
            # range
            start, end, total_power = find_max_power_range(data,
                                                           interval.duration,
                                                           interval_duration + recovery_duration)
            max_power = max(get_row_power(data, i) for i in range(start, end))
            average_power = total_power / interval.duration
            power_readings = [PowerReading(get_row_timestamp(data, i), get_row_power(data, i)) for i in range(start, end)]
            interval = Interval(get_row_timestamp(data, start),
                                get_row_timestamp(data, end - 1),
                                max_power,
                                average_power,
                                power_readings)
            logging.debug(interval)
            intervals.append(interval)
            del data[:end]
    return FileData(start_time, intervals)


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('--debug', action='store_true',
                        help="Enable debugging output")

    input_defn_group = parser.add_argument_group('Input definition arguments',
                                                 description="Note that if files are specified on the command line and "
                                                             "an input list is also specified, the files named in the "
                                                             "input list will be processed after those specified via "
                                                             "command-line arguments")
    input_defn_group.add_argument('-I', '--input-list', metavar='FILE',
                                  help="Read a list of .fit files from FILE, one filename per line")
    input_defn_group.add_argument('-i', '--input', metavar='FILE', action='extend', dest='input_files', nargs='+',
                                  help='Input .fit file(s).  May be specified multiple times.')

    output_defn_group = parser.add_argument_group('Output definition arguments')
    output_defn_group = output_defn_group.add_mutually_exclusive_group()
    output_defn_group.add_argument('--csv', action='store_true',
                                   help="Write output as CSV. Default is plain text")
    output_defn_group.add_argument('--tsv', action='store_true',
                                   help="Write output as TSV. Default is plain text")

    session_defn_group = parser.add_argument_group('Session definition arguments')
    session_defn_group = session_defn_group.add_mutually_exclusive_group(required=True)
    session_defn_group.add_argument('-p', '--picave-definition', metavar='FILE', type=pathlib.Path,
                                    help='Specify session via a PiCave session definition file')
    session_defn_group.add_argument('-P', '--picave-definition-from-filelist', action='store_true',
                                    help='Specify session via a PiCave session definition file, '
                                         'which is named in the first line of the input file list')
    session_defn_group.add_argument('-r', '--reps', metavar='REP', type=str,
                                    help='Specification of repetitions to detect', nargs='+')

    picave_session_defn_group = parser.add_argument_group('PiCave-session definition arguments',
                                                          description="Arguments related to processing sessions "
                                                                      "defined via a PiCave session definition file")
    picave_session_defn_group.add_argument('--effort-threshold', type=int, metavar='PCT',
                                           help='Define effort intervals to be those with effort levels >= PCT%% FTP')

    auto_detect_interval_group = parser.add_argument_group('Automatic interval detection arguments',
                                                           description="Arguments related to the automatic detection "
                                                                       "of intervals")
    auto_detect_interval_group.add_argument('--longest-recovery', type=int,
                                            help="Maximum duration to skip when searching for an effort interval")
    auto_detect_interval_group.add_argument('--recovery-duration', type=int,
                                            help="Contiguous duration no greater than recovery-power to identify a "
                                                 "recovery interval (seconds)")
    auto_detect_interval_group.add_argument('--interval-power', type=int,
                                            help="Minimum power to find when looking for an interval (watts)")
    auto_detect_interval_group.add_argument('--interval-duration', type=int,
                                            help="Contiguous duration no lower than interval-power to identify a "
                                                 "workout interval (sec)")

    parser.set_defaults(recovery_duration=10,
                        longest_recovery=305,
                        interval_power=250,
                        interval_duration=10,
                        effort_threshold=70,
                        input_files=[])
    args = parser.parse_args()
    if args.picave_definition_from_filelist:
        if not args.input_list:
            parser.error("--input-list must be specified if --picave-definition-from-filelist is given")
        with open(args.input_list) as handle:
            first_line = handle.readline().strip()
            if not first_line or first_line[0] != '#':
                parser.error("input file list does not start with a comment line")
            args.picave_definition = first_line[1:].strip()
            if not args.picave_definition:
                parser.error("input file list does not start with a picave definition file")
            args.picave_definition = pathlib.Path(args.picave_definition)
            if args.picave_definition.parts[0] == '~':
                args.picave_definition = args.picave_definition.expanduser()

    if args.input_list:
        files_list = open(args.input_list).read().splitlines()
        files_list = [filename.strip() for filename in files_list]
        files_list = [filename for filename in files_list if filename and filename[0] != '#']
        args.input_files.extend(files_list)
    if not args.input_files:
        parser.error("One or more input files required")
    return args


def parse_durn(durn):
    """
    >>> parse_durn('30s')
    30
    >>> parse_durn('1m')
    60
    >>> parse_durn('1m30s')
    90
    >>> parse_durn('  2m 30s  ')
    150
    >>> parse_durn('  ')
    >>> parse_durn('1')
    >>> parse_durn('5m3')
    """
    durn_value = 0
    while durn:
        durn = durn.strip()
        if not durn or not durn[0].isdigit():
            return None
        i = 0
        while (i < len(durn)) and (durn[i].isdigit()):
            i += 1
        if i >= len(durn):
            return None
        chunk = int(durn[:i])
        unit = durn[i]
        durn = durn[i + 1:]
        if unit == 'm':
            unit = 60
        elif unit == 's':
            unit = 1
        else:
            return None
        durn_value += chunk * unit
    return durn_value


def parse_reps(reps_list) -> SessionDefinition:
    session_defn = SessionDefinition()
    interval_number = 1
    for reps in reps_list:
        if reps[0] == '-':
            reps = reps[1:]
            interval_type = IntervalType.Recovery
        else:
            interval_type = IntervalType.Effort
        if 'x' in reps:
            n, durn = reps.split('x', 1)
            if not n.isdigit():
                raise Exception("invalid reps")
            n = int(n)
        else:
            n, durn = 1, reps
        durn = parse_durn(durn)
        for rep in range(n):
            if session_defn.last_interval_type != IntervalType.Recovery:
                session_defn.add_interval(-1, IntervalType.Recovery, 'Recovery')
            if interval_type == IntervalType.Recovery:
                interval_name = 'Recovery'
            else:
                interval_name = 'Interval %u' % interval_number
                interval_number += 1
            session_defn.add_interval(durn, interval_type, interval_name)
    return session_defn


def read_input_file(filename):
    rows = []
    with fitdecode.FitReader(filename) as fit:
        for frame in fit:
            if isinstance(frame, fitdecode.FitDataMessage):
                if frame.name != 'record':
                    continue
                row = {}
                for field in frame.fields:
                    if field.name in ('vertical_oscillation', 'stance_time'):
                        continue
                    if field.name == 'timestamp':
                        if 'power' in row:
                            rows.append(row)
                        row = {}
                    row[field.name] = (field.value, field.units)
                if 'power' in row:
                    rows.append(row)
                logging.debug(row)
    return rows


def parse_picave_session_definition(filepath, effort_threshold) -> SessionDefinition:
    with open(filepath) as handle:
        session = json.load(handle)

    session_defn = SessionDefinition()
    for interval_defn in session:
        if interval_defn['type'] == 'MAX':
            interval_type = IntervalType.Effort
        else:
            assert interval_defn['type'] == '%FTP'
            effort = interval_defn['effort']
            assert effort[-1] == '%'
            effort = effort[:-1]
            effort = int(effort)
            interval_type = IntervalType.Effort if (effort >= effort_threshold) else IntervalType.Recovery
        durn = parse_durn(interval_defn['duration'])
        assert durn
        session_defn.add_interval(durn, interval_type, interval_defn['name'])

    return session_defn


def main():
    args = parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    if args.reps:
        session_defn = parse_reps(args.reps)
    elif args.picave_definition:
        session_defn = parse_picave_session_definition(args.picave_definition, args.effort_threshold)
    else:
        assert False

    input_file_data = []  # list of FileData
    for fit in args.input_files:
        data = read_input_file(fit)
        file_data = find_intervals(data,
                                   session_defn,
                                   args.recovery_duration,
                                   args.interval_power,
                                   args.interval_duration,
                                   args.longest_recovery)
        if file_data:
            input_file_data.append(file_data)
        else:
            logging.error("Unable to read %s", fit)

    if not input_file_data:
        logging.critical("Unable to read any input files. Aborting")
        sys.exit()

    # construct the summary (max power and average power) tables
    file_data = input_file_data[0]
    y_dim = len(file_data.intervals) + 1  # all files have the same number of intervals
    x_dim = len(args.input_files) + 1
    max_power_table = [[''] * x_dim for y in range(y_dim)]
    avg_power_table = [[''] * x_dim for y in range(y_dim)]
    y = 1
    for interval_defn in session_defn.intervals:
        if interval_defn.interval_type == IntervalType.Effort:
            max_power_table[y][0] = avg_power_table[y][0] = interval_defn.name
            y += 1
    for x, file_data in enumerate(input_file_data, start=1):
        max_power_table[0][x] = avg_power_table[0][x] = file_data.start_time.strftime('%Y-%m-%d')
        for y, interval in enumerate(file_data.intervals, start=1):
            max_power_table[y][x] = interval.max_power
            avg_power_table[y][x] = '%.1f' % interval.avg_power

    # now construct the detailed power readings table
    y_dim = sum(len(interval.power_readings) for interval in file_data.intervals) + len(file_data.intervals) + 1
    x_dim = len(args.input_files) * 2 + 1
    power_readings = [[''] * x_dim for y in range(y_dim)]
    for ix, file_data in enumerate(input_file_data):
        x0 = ix * 2 + 1
        x1 = x0 + 1
        power_readings[0][x0] = file_data.start_time.strftime('%Y-%m-%d offset')
        power_readings[0][x1] = file_data.start_time.strftime('%Y-%m-%d reading')
        y_power = 1
        for interval in file_data.intervals:
            for interval_y, (time, power) in enumerate(interval.power_readings, start=1):
                power_readings[y_power][0] = interval_y
                power_readings[y_power][x0] = time - file_data.start_time
                power_readings[y_power][x1] = power
                y_power += 1
            if not(args.csv) and not (args.tsv):
                power_readings[y_power][x0] = power_readings[y_power][x1] = '---'
                y_power += 1

    if args.csv or args.tsv:
        writer = csv.writer(sys.stdout,
                            delimiter='\t' if args.tsv else ',')

        def output(table):
            writer.writerows(table)
    else:
        def output(table):
            print(tabulate.tabulate(table))

    print("Maximum power")
    output(max_power_table)
    print()
    print()
    print("Average power")
    output(avg_power_table)
    print()
    print()
    print("Power readings")
    output(power_readings)


if __name__ == '__main__':
    main()
