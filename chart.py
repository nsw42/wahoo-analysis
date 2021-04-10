import json
from textwrap import dedent


def generate_chart(output_path, power_readings_table):
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
