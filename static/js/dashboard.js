(function () {
  "use strict";
  if (typeof Chart === "undefined") return;
  const read = (id) => JSON.parse(document.getElementById(id).textContent);
  const daily = read("daily-chart-data");
  const status = read("status-chart-data");
  const agency = read("agency-chart-data");
  const severity = read("severity-chart-data");
  const gridColor = "rgba(16, 39, 70, .08)";
  Chart.defaults.font.family = "Inter, system-ui, -apple-system, sans-serif";
  Chart.defaults.color = "#667085";
  new Chart(document.getElementById("dailyShipmentsChart"), {type:"line",data:{labels:daily.labels,datasets:[{data:daily.values,borderColor:"#ff7417",backgroundColor:"rgba(255,116,23,.12)",fill:true,tension:.35,borderWidth:3,pointRadius:daily.labels.length>45?0:3,pointHoverRadius:5}]},options:{maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{display:false},ticks:{maxTicksLimit:12}},y:{beginAtZero:true,ticks:{precision:0},grid:{color:gridColor}}}}});
  new Chart(document.getElementById("statusChart"), {type:"doughnut",data:{labels:status.labels,datasets:[{data:status.values,backgroundColor:status.colors,borderWidth:0,hoverOffset:5}]},options:{maintainAspectRatio:false,cutout:"68%",plugins:{legend:{position:"bottom",labels:{boxWidth:10,usePointStyle:true,padding:14}}}}});
  new Chart(document.getElementById("agencyChart"), {type:"bar",data:{labels:agency.labels,datasets:[{data:agency.values,backgroundColor:"#1f6feb",borderRadius:7,maxBarThickness:42}]},options:{maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{display:false}},y:{beginAtZero:true,ticks:{precision:0},grid:{color:gridColor}}}}});
  new Chart(document.getElementById("severityChart"), {type:"bar",data:{labels:severity.labels,datasets:[{data:severity.values,backgroundColor:["#22a06b","#f5a524","#ed6a5a","#c93756"],borderRadius:7,maxBarThickness:48}]},options:{maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{display:false}},y:{beginAtZero:true,ticks:{precision:0},grid:{color:gridColor}}}}});
})();
