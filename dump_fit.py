import argparse
from pprint import pprint

from analyse import read_input_file


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--offset', action='store_true', dest='show_time_offset',
                        help="Show times as offset from start")
    parser.add_argument('input', help='Input .fit file')
    parser.set_defaults(show_time_offset=False)
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    rows = read_input_file(args.input)
    for row in rows:
        if args.show_time_offset:
            timeval = row['timestamp'][0] - rows[0]['timestamp'][0]
        else:
            timeval = row['timestamp'][0]
        print('%s  %5u' % (timeval, row['power'][0]))

if __name__ == '__main__':
    main()
