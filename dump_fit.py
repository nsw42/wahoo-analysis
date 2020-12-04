import argparse
from pprint import pprint

from analyse import read_input_file


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='Input .fit file')
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    rows = read_input_file(args.input)
    for row in rows:
        time_offset = row['timestamp'][0] - rows[0]['timestamp'][0]
        print('%s  %5u' % (time_offset, row['power'][0]))

if __name__ == '__main__':
    main()
