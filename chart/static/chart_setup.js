function fill_selects() {
    // Populate the devices dropdown
    devices.forEach(function (x) {
        let dropDownOption = document.createElement("option");
        dropDownOption.value = x;
        dropDownOption.text = x;
        document.getElementById("device-select").appendChild(dropDownOption);
    });

    // Populate the time frame dropdown
    timeframes.forEach(function (x) {
        let dropDownOption = document.createElement("option");
        dropDownOption.value = x.value;
        dropDownOption.text = x.name;
        document.getElementById("timeframe-select").appendChild(dropDownOption);
    });
}


function update_chart(labels, temperature, humidity, pressure) {
    const backgrounds = {
        "Temperature": ["#FCB1C3B0", "#FCB1C390"],
        "Humidity": ["#7CE0F9B0", "#7CE0F990"],
        "Pressure": ["#F5F5F5B0", "#F5F5F590"]
    };

    chart.data.labels = labels.map(x => moment(x));

    chart.data.datasets = [{
        label: "Temperature",
        borderColor: backgrounds["Temperature"][0],
        backgroundColor: backgrounds["Temperature"][1],
        data: temperature,
        yAxisID: 'humidity'
    },
    {
        label: "Humidity",
        borderColor: backgrounds["Humidity"][0],
        backgroundColor: backgrounds["Humidity"][1],
        data: humidity,
        yAxisID: 'temperature'
    }];

    if (pressure.some(x => x !== null)) {
        chart.data.datasets.push({
            label: "Pressure",
            borderColor: backgrounds["Pressure"][0],
            backgroundColor: backgrounds["Pressure"][1],
            data: pressure,
            yAxisID: 'pressure'
        });
    }

    chart.update();
}


function setup_chart() {
    let context = document.getElementById("chart").getContext("2d");

    let chartParameters = {
        type: "line",
        options: {
            scales: {
                xAxes: [
                    {type: "time", 
                     time: {parser: timeFormat, tooltipFormat: "ll HH:mm"},
                     scaleLabel: {display: true, labelString: "Date"}
                    }],
                yAxes: [
                    {id: "temperature", type: "linear", position: "left", stacked: true},
                    {id: "humidity", type: "linear", position: "left", stacked: true},
                    {id: "pressure", type: "linear", position: "right", stacked: false}
                ]
            }
        }
    };

    chart = new Chart(context, chartParameters);
}

function request_chart() {
    let timeFrame = document.getElementById("timeframe-select").value;
    let device = document.getElementById("device-select").value;
    let requestURL = "/" + timeFrame + "/" + device;
    console.log(requestURL);

    let request = new Request(requestURL);

    fetch(request).then(response => {
        if (response.status === 200) {
            return response.json();
        } else {
            throw new Error('Something went wrong on api server!');
        }
    }).then(response => {
        update_chart(response.labels, response.Temperature, response.Humidity, response.Pressure);
    }).catch(error => {
        console.error(error);
    });
}