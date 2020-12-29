# wahoo-analysis

Python script to analyse Wahoo .fit session files

## Usage

Using the Wahoo analysis script requires (at least) two sets of information: the definition of the intervals in the workout, and the .fit file(s) to read.

### Specifying intervals

There are two different ways of specifying intervals.

#### Intervals specified by command-line arguments

The script can attempt to automatically find the work intervals based on command-line arguments that define how it should recognise the interesting intervals.

This works by searching through the data to identify a plausible work interval, and then searching around that point to find the best interval of the required duration. This approach allows for work intervals that start a few seconds later than intended, and gives credit if the effort was maintained for a little bit beyond the expected end point.

Use `-r` / `--reps` to specify the repetitions that constitute the session. Repetitions are expressed as `NxD`, where `N` is an integer, `x` is the literal character and `D` is a duration such as `30s`, `2m`, or `1m30s`. Hence a sprint-based workout might have its reps specified with `--reps 8x30s`.

There are other command line arguments to further refine the search for effort intervals: 

* `--longest-recovery N` specifies the maximum number of seconds that will be skipped when looking for effort intervals, i.e. the maximum separation between work intervals. This defaults to just over 5 minutes.

* `--recovery-duration N` specifies the number of seconds beyond the likely end of an effort interval that should be searched when trying to identify where the work interval starts.

* `--interval-power N` specifies the minimum power threshold (in watts) work effort intervals are required to exceed in order for the interval to be recognised as a work effort.

* `--interval-duration N` specifies the number of seconds that must exceed the interval-power threshold in order to recognise a point in the work interval. This does not need to be the entire duration: `10` might be an appropriate value for a 30s sprint effort, as it allows a higher interval power threshold to be specified, reducing the likelihood of incorrectly recognising a recovery interval as a work interval.


#### Intervals specified by a Picave interval definition file

If the workout followed one of those in the [PiCave](https://github.com/nsw42/picave) index, the interval definitions can be read from the corresponding file in the PiCave index.

Either:

* Use `-p` / `--picave-definition FILENAME` to specify the definition file as a command-line argument

or:

* Use `-P` / `--picave-definition-from-filelist` in conjunction with `-I` / `--input-list` to name the PiCave interval definition file in the first line of the file list.

If reading a PiCave interval definition file, the `--effort-threshold PCT` command-line argument allows you to select which intervals to keep. Any interval at or above `PCT` % of FTP will be treated as a work interval. This defaults to 70 (i.e. 70% of FTP).

### Specifying input fit files

Input files can be specified as command-line arguments, using `-i` / `--input`, as many times as required.

Alternatively, you can build a text file that lists the fit filenames, and pass that text file to `-I` / `--input-list`.  Lines starting with `#` are treated as comments and ignored. If `-P` / `--picave-definition-from-filelist` is specified, the first line must contain a comment that names the definition file.

Example:

```
# ~/sw/picave/feed/yt_ZiGE3-L4vyg.json

~/Dropbox/Apps/WahooFitness/2020-11-07-192339-FITNESS 9E42-425-0.fit
~/Dropbox/Apps/WahooFitness/2020-11-13-182529-FITNESS 9E42-431-0.fit
~/Dropbox/Apps/WahooFitness/2020-11-24-185355-FITNESS 9E42-441-0.fit
```

## Controlling output

### Output file format

Default output is a plain text format. Use `--csv` or `--tsv` to select a different file format for importing into a spreadsheet.

### Selecting what to print

By default, the script will print the *maximum* power observed in each power interval (as well as a row showing the maximum power observed in the entire workout session); another table containing the *average* power observed in each power interval (as well as a row showing the average power for the entire work intervals (i.e. ignoring all recovery intervals)); and a third table that contains the identified individual power readings, which is mostly useful for confirming that the automatic interval detection has worked correctly.

Each of these three tables can be enabled with `-m` / `--report-interval-max-power`, `-a` / `--report-interval-avg-power`, `-w` / `--report-interval-power-readings` or disabled with the corresponding `-M`/`-A`/`-W`/`--no-report-(etc)` arguments.

### Other arguments

`--debug` might help you figure out why the automatic interval detection isn't working.
