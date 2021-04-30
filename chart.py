import json
from textwrap import dedent


def generate_max_or_avg_power_chart(output_path, power_table, title):
    # power_table input
    # [
    #   [ "",               "YYYY-MM-DD",  "YYYY-MM-DD",  "YYYY-MM-DD"],
    #   [ "Interval name",    reading,       reading,        reading  ],
    #   [ "Interval name",    reading,       reading,        reading  ],
    #   [ "-----",            "-----",       "-----",        "-----"  ],
    #   [ "Average",          reading,       reading,        reading  ]
    # ]
    data_array = [power_table[0]]
    for row in power_table[1:-2]:
        out_row = [row[0]]
        out_row.extend([float(value) for value in row[1:]])
        data_array.append(out_row)
    data_array = json.dumps(data_array, indent=4)

    colors = []
    # need one colour per column; going from light grey (oldest) to black (most recent)
    nr_colors = len(power_table[0]) - 1
    for column in range(nr_colors):
        color = 0 if (column == nr_colors - 1) else 192  # int(192 - 192 * column / nr_colors)
        color = '#%02x%02x%02x' % (color, color, color)
        colors.append(color)
    with open(output_path, 'w') as handle:
        print(dedent("""\
            <html>
            <head>
                <script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
                <script type="text/javascript">
                    google.charts.load('current', {'packages':['corechart']});
                    google.charts.setOnLoadCallback(drawChart);

                    function drawChart() {
                        var data = google.visualization.arrayToDataTable(
            %s
            );

                        var options = {
                            title: '%s',
                            legend: { position: 'bottom' },
                            colors: %s
                        };

                        var chart = new google.visualization.LineChart(document.getElementById('chart'));

                        chart.draw(data, options);
                    }
                </script>
            </head>
            <body>
                <div id="chart" style="width: 1800px; height: 1000px"></div>
            </body>
            </html>
        """) % (data_array, title, colors), file=handle)


def generate_power_readings_chart(output_path, power_readings_table):
    data_array = []
    heading_row = power_readings_table[0]
    col_idx = 1
    output_row = ['Timestamp']
    while col_idx < len(heading_row):
        heading = heading_row[col_idx]
        if heading.endswith(' offset'):
            heading = heading[:-7]
        output_row.append(heading)
        col_idx += 2
    data_array.append(output_row)

    t = 0
    for row in power_readings_table[1:]:
        col_idx = 1
        output_row = [t]
        t += 1
        while col_idx < len(row):
            reading = row[col_idx + 1]
            output_row.append(reading)
            col_idx += 2
        data_array.append(output_row)

    with open(output_path, 'w') as handle:
        print(dedent('''\
            <html>
            <head>
                <script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
                <script type="text/javascript">
                    google.charts.load('current', {'packages':['corechart']});
                    google.charts.setOnLoadCallback(drawChart);

                    function drawChart() {
                        var data = google.visualization.arrayToDataTable(%s);

                        var options = {
                            title: 'TBD',
                            curveType: 'function',
                            legend: { position: 'bottom' }
                        };

                        var chart = new google.visualization.LineChart(document.getElementById('chart'));

                        chart.draw(data, options);
                    }
                </script>
            </head>
            <body>
                <div id="chart" style="width: 1800px; height: 1000px"></div>
            </body>
        </html>
    ''') % json.dumps(data_array), file=handle)
