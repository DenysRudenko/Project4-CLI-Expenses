// jshint esversion: 6
const renderChart = (data, labels) => {
var ctx = document.getElementById('incomeChart').getContext("2d");

// Chart properties
var incomeChart = new Chart(ctx, {
    type: 'bar',
    data: {
        labels: labels,
        datasets: [{
            label: 'Last 6 months incomes',
            data: data,
            backgroundColor: [
                'rgba(255, 99, 132, 0.2)',
                'rgba(54, 162, 235, 0.2)',
                'rgba(255, 206, 86, 0.2)',
                'rgba(75, 192, 192, 0.2)',
                'rgba(153, 102, 255, 0.2)',
                'rgba(255, 159, 64, 0.2)'
            ],
            borderColor: [
                'rgba(255,99,132,1)',
                'rgba(54, 162, 235, 1)',
                'rgba(255, 206, 86, 1)',
                'rgba(75, 192, 192, 1)',
                'rgba(153, 102, 255, 1)',
                'rgba(255, 159, 64, 1)'
            ],
            borderWidth: 1
        }]
    },
    options: {
    scales: {
        yAxes: [{
            ticks: {
                beginAtZero:true
            }
        }]
        }
    }
    });
};

// This is a function that retrieves expense category data from the server
// and renders it in a chart using the Chart.js library.
const getIncomeChartData = () => {
    console.log("Test?");
    fetch('/income/income_source_summary')
        .then(res => res.json())
        .then(results => {
            const source_data = results.income_source_data;
            const [labels, data] = [
                Object.keys(source_data),
                Object.values(source_data)
            ];

        renderChart(data, labels);
        });
};

document.onload = getIncomeChartData();