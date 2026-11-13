
$(document).ready(function() {
    
        
    setInterval(function () {
        fetch(window.location.href)
        .then(function (response) {
            return response.text();
            })
            .then(function (html) {
                const tempDiv = document.createElement("div");
                tempDiv.innerHTML = html;
                
                const newDecoded = tempDiv.querySelector("#decoded");
                const currentDecoded = document.querySelector("#decoded");
                
                if (newDecoded && currentDecoded) {
                    currentDecoded.innerHTML = newDecoded.innerHTML;
                }
            })
            .catch(function (error) {
                console.error("Fehler beim Aktualisieren von #decoded:", error);
            });
    }, 500);

    setInterval(function () {
        fetch(window.location.href)
        .then(function (response) {
            return response.text();
            })
            .then(function (html) {
                const tempDiv = document.createElement("div");
                tempDiv.innerHTML = html;
                
                const newDecoded = tempDiv.querySelector("#files");
                const currentDecoded = document.querySelector("#files");
                
                if (newDecoded && currentDecoded) {
                    currentDecoded.innerHTML = newDecoded.innerHTML;
                }
            })
            .catch(function (error) {
                console.error("Fehler beim Aktualisieren von #files:", error);
            });
    }, 3000);
        
    setInterval(function(){
        $("#status").load(window.location.href + " #status" );
    }, 500);
    setInterval(function(){
        $("#sysinfo").load(window.location.href + " #sysinfo" );
    }, 2000);
    setInterval(function(){
            $("#cancel").load(window.location.href + " #cancel" );
    }, 2000);

    // Toggle-Funktion f�r #canData
    $("#canData").hide(); // initial verstecken
    $("#toggleCanData").click(function() {
        $("#canData").toggle(); // zeigt oder versteckt den Div
    });

        
    setInterval(function () {
            $('#canData').load(`http://${myip}:8081/trace`);
    }, 200);
// // Hilfsvariable, damit Plotly-Events nur einmalig registriert werden
let isPlotInitialized = false;

// Gespeicherten State beim Seitenstart aus dem localStorage laden
let savedRelayout = JSON.parse(localStorage.getItem('plotlyZoomState')) || {};
let savedVisibility = JSON.parse(localStorage.getItem('plotlyVisibilityState')) || {};

// Reset-Button Funktion einrichten
const resetBtn = document.getElementById('reset-plot-btn');
if (resetBtn) {
    resetBtn.addEventListener('click', function () {
        // 1. Browser-Speicher leeren
        localStorage.removeItem('plotlyZoomState');
        localStorage.removeItem('plotlyVisibilityState');
        savedRelayout = {};
        savedVisibility = {};

        // 2. Aktuellen Plot sofort auf Standard zurücksetzen
        const plotDiv = document.getElementById('plotly-div');
        if (plotDiv && plotDiv.data) {
            // Alle Linien wieder einblenden
            const updateTraces = { visible: true };
            Plotly.restyle(plotDiv, updateTraces);

            // Alle Achsen auf Autorange zurücksetzen
            const updateLayout = { 'xaxis.autorange': true };
            Object.keys(plotDiv.layout).forEach(key => {
                if (key.startsWith('yaxis')) {
                    updateLayout[`${key}.autorange`] = true;
                }
            });
            Plotly.relayout(plotDiv, updateLayout);
        }
    });
}


// // Zyklisches Laden der CAN-Daten
// setInterval(function () {
//     const plotDiv = document.getElementById('plotly-div');
//     if (!plotDiv) return;

//     fetch(`http://${myip}:8081/plotdata`)
//         .then(response => {
//             if (!response.ok) throw new Error(`HTTP ${response.status}`);
//             const contentType = response.headers.get("content-type");
//             if (!contentType || !contentType.includes("application/json")) {
//                 throw new Error(`Kein JSON: ${contentType}`);
//             }
//             return response.json();
//         })
//         .then(data => {
//             // 1. Gespeicherte Sichtbarkeit (Legenden-Klicks) anwenden
//             data.forEach(trace => {
//                 if (savedVisibility[trace.name] !== undefined) {
//                     trace.visible = savedVisibility[trace.name];
//                 }
//             });

//             // Einheiten ermitteln
//             const units = [...new Set(data.map(trace => trace.unit || "unknown"))];

//             // 2. Layout aufbauen
//             const layout = {
//                 title: 'CAN Signals',
//                 height: 600,
//                 with: 800,
//                 showlegend: true,
//                 legend: {orientation: "v", x: 1.15, y: 1.0, font: { size:17 }, xanchor: "right", yanchor: "top"},
//                 // Zoom beibehalten
//                 uirevision: true,
//                 tickfont:{size: 20 },
//                 automargin: true,
//                 // Hintergrund transparent
//                 paper_bgcolor: 'rgba(255,255,255,0.05)',
//                 plot_bgcolor: 'rgba(0,0,0,0)'

//             };

//             // 3. Gespeicherten X-Achsen-Zoom anwenden
//             if (savedRelayout['xaxis.range[0]'] !== undefined && savedRelayout['xaxis.range[1]'] !== undefined) {
//                 layout.xaxis.range = [
//                     savedRelayout['xaxis.range[0]'],
//                     savedRelayout['xaxis.range[1]']
//                 ];
//                 layout.xaxis.autorange = false;
//             }

//             // Achsen dynamisch anlegen
//             units.forEach((unit, idx) => {
//                 layout.xaxis = {domain: [0.08 * idx, 1]};
//                 // const posvalue = 0.05;
//                 const axisNo = idx + 1;
//                 const layoutName =
//                 axisNo === 1
//                 ? "yaxis"
//                 : `yaxis${axisNo}`;
                
//                 layout[layoutName] = {
//                     title: {text: unit, standoff: 10, font: { size: 20 }},
//                     tickfont:{size: 20 },
//                     // tickformat: ".2f",
//                     tickformat: "~.2f",
//                     anchor: "free",
//                     overlaying: axisNo === 1 ? undefined: "y",
//                     side:"left",
//                     showgrid: axisNo === 1,
//                     position: 0.0 + idx * 0.08,
//                     automargin: true,
//                 };
//                 data.forEach(trace => {
                    
//                     if ((trace.unit || "unknown") === unit) {
//                         trace.line = {width: 4};
//                         trace.mode = "lines+markers"; 
//                         trace.marker = {size: 6};
//                         trace.yaxis =
//                             axisNo === 1
//                                 ? "y"
//                                 : `y${axisNo}`;
//                     }
//                                 }); // <--- 1. FEHLTE: Schließt data.forEach
//             }); // <--- 2. FEHLTE: Schließt units.forEach
//             // // 4. Y-Achsen dynamisch anlegen & gespeicherten Y-Zoom anwenden
//             // units.forEach((unit, idx) => {
//             //     const axisNo = idx + 1;
//             //     const layoutName = axisNo === 1 ? "yaxis" : `yaxis${axisNo}`;

//             //     layout[layoutName] = {
//             //         title: { text: unit, standoff: 10, font: { size: 20 } },
//             //         tickfont: { size: 20 }
//             //     };

//             //     if (axisNo > 1) {
//             //         layout[layoutName].overlaying = 'y';
//             //         layout[layoutName].side = 'left';
//             //         layout[layoutName].position = 0.08 * idx;
//             //     }

//             //     const range0 = savedRelayout[`${layoutName}.range[0]`];
//             //     const range1 = savedRelayout[`${layoutName}.range[1]`];

//             //     if (range0 !== undefined && range1 !== undefined) {
//             //         layout[layoutName].range = [range0, range1];
//             //         layout[layoutName].autorange = false;
//             //     }
//             // });

//             // // 5. Traces den richtigen Y-Achsen zuordnen
//             // data.forEach(trace => {
//             //     const unit = trace.unit || "unknown";
//             //     const unitIdx = units.indexOf(unit);
//             //     trace.yaxis = unitIdx > 0 ? `y${unitIdx + 1}` : 'y';
            
        
//         // });

//             // 6. Plot erstellen (beim ersten Mal) oder aktualisieren (danach)
//             if (!isPlotInitialized) {
//                 Plotly.newPlot(plotDiv, data, layout).then(() => {
//                     // Event-Listener für Zoom & Pan
//                     plotDiv.on('plotly_relayout', function (eventData) {
//                         if (!eventData) return;

//                         Object.keys(eventData).forEach(key => {
//                             if (key.includes('.autorange') && eventData[key] === true) {
//                                 const axisName = key.split('.')[0];
//                                 delete savedRelayout[`${axisName}.range[0]`];
//                                 delete savedRelayout[`${axisName}.range[1]`];
//                                 delete eventData[key];
//                             }
//                         });

//                         Object.assign(savedRelayout, eventData);
//                         localStorage.setItem('plotlyZoomState', JSON.stringify(savedRelayout));
//                     });

//                     // Event-Listener für Legenden-Klicks
//                     plotDiv.on('plotly_restyle', function () {
//                         plotDiv.data.forEach(trace => {
//                             savedVisibility[trace.name] = trace.visible;
//                         });
//                         localStorage.setItem('plotlyVisibilityState', JSON.stringify(savedVisibility));
//                     });

//                     isPlotInitialized = true;
//                 });
//             } else {
//                 Plotly.react(plotDiv, data, layout);
//             }
//         })
//         .catch(error => {
//             console.error('Plot Update Fehler:', error);
//         });

// }, 750);


    setInterval(function () {

        const plotDiv = document.getElementById('plotly-div');

        if (!plotDiv) {
            return;
        }

        fetch(`http://${myip}:8081/plotdata`)
        // .then(response => response.json())
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const contentType = response.headers.get("content-type");
            if (!contentType ||
                !contentType.includes("application/json")) {
                throw new Error(
                    `Kein JSON: ${contentType}`
                );
            }
            return response.json();
        })
 
        .then(data => {
            // Alle vorhandenen Einheiten bestimmen
            const units = [...new Set(
                data.map(trace => trace.unit || "unknown")
            )];

            const layout = {
                title: 'CAN Signals',
                // height:700,
                // with:1000,
                showlegend: true,
                legend: {orientation: "v", x: 1.2, y: 1.0, font: { size:10 }, xanchor: "right", yanchor: "top"},
                // Zoom beibehalten
                uirevision: true,
                tickfont:{size: 10 },
                automargin: true,
                // Hintergrund transparent
                paper_bgcolor: 'rgba(255,255,255,0.0)',
                plot_bgcolor: 'rgba(0,0,0,0.1)',
            

            };
            // Achsen dynamisch anlegen
            units.forEach((unit, idx) => {
                layout.xaxis = {domain: [0.08 * idx, 1]};
                // const posvalue = 0.05;
                const axisNo = idx + 1;
                const layoutName =
                axisNo === 1
                ? "yaxis"
                : `yaxis${axisNo}`;
                
                layout[layoutName] = {
                    title: {text: unit, standoff: 10, font: { size: 10 }},
                    tickfont:{size: 10 },
                    // tickformat: ".2f",
                    tickformat: "~.2f",
                    anchor: "free",
                    overlaying: axisNo === 1 ? undefined: "y",
                    side:"left",
                    showgrid: axisNo === 1,
                    position: 0.0 + idx * 0.08,
                    automargin: true,
                };
                data.forEach(trace => {
                    
                    if ((trace.unit || "unknown") === unit) {
                        trace.line = {width: 2};
                        trace.mode = "lines+markers"; 
                        trace.marker = {size: 3};
                        trace.yaxis =
                            axisNo === 1
                                ? "y"
                                : `y${axisNo}`;
                    }
                });
            });
// if (plotDiv.layout) {

//     localStorage.setItem(
//         "plotlyLayoutState",
//         JSON.stringify(plotDiv.layout)
//     );

// }
// const savedLayout =
//     localStorage.getItem(
//         "plotlyLayoutState"
//     );

// if (savedLayout) {

//     Object.assign(
//         layout,
//         JSON.parse(savedLayout)
//     );

// }
            Plotly.react(
                'plotly-div',
                data,
                layout
            );
        })
        .catch(error => {
            console.error("Plot Update Fehler:", error);
        });

}, 750);






// function updateSignalDashboard() {

//     fetch(`http://${myip}:8081/plotdata`)
//     .then(r => r.json())
//     .then(data => {

//         const gaugeContainer =
//             document.getElementById("gauges");

//         if (!gaugeContainer)
//             return;

//         gaugeContainer.innerHTML = "";

//         data.forEach(trace => {

//             if (!trace.y || !trace.y.length)
//                 return;

//             const lastValue =
//                 trace.y[trace.y.length - 1];

//             const gaugeDiv =
//                 document.createElement("div");

//             gaugeDiv.style.width = "400px";
//             gaugeDiv.style.height = "250px";

//             gaugeContainer.appendChild(gaugeDiv);

//             gaugeDiv.innerHTML = `
//                 <div style="
//                     border:2px solid #ffffff;
//                     border-radius:8px;
//                     padding:10px;
//                     width:400px;
//                     background:#00000;
//                     color:#ffffff;
//                     font-family:monospace;
//                     text-align:center;
//                 ">
//                     <div style="font-size:28px; color:white; margin-bottom:10px; word-wrap:break-word;">
//                         ${trace.name}
//                     </div>

//                     <div style=" font-size:28px; font-weight:bold;">
//                         ${lastValue.toFixed(2)}
//                     </div>

//                     <div style=" font-size:28px; color:#ffffff;">
//                         ${trace.unit || ""}
//                     </div>
//                 </div>
//             `;





        // });

    // });
// }

updateSignalDashboard();
// setInterval(updateSignalDashboard, 400);
updateWidgetValues();
setInterval(updateWidgetValues, 300);


    // Plot initial verstecken
    $("#plotContainer").show();

    $("#togglePlot").click(function() {
        $("#plotly-div").toggle();
    });


});

function toggleMenu() {
    document.getElementById("actionMenu").classList.toggle("show");
}

window.onclick = function(event) {
    try {
        if (!event.target.closest('.action-container')) {

            const actionMenu = document.getElementById("actionMenu");

            if (actionMenu) {
                actionMenu.classList.remove("show");
            } else {
                console.info("actionMenu nicht vorhanden");
            }
        }
    } catch (e) {
        console.info("actionMenu nicht verfügbar:", e);
    }
};

window.onclick = function(event) {
    if (!event.target.closest('.action-container')) {
    document.getElementById("actionMenu").classList.remove("show");
    }
}

if (typeof latestData === "undefined") {let latestData = [];}

let widgets = JSON.parse(localStorage.getItem("signalDashboard") || "[]");
function saveLayout()
{
    localStorage.setItem(
        "signalDashboard",
        JSON.stringify(widgets)
    );
}
function fillSignalSelect()
{
    const select =
        document.getElementById(
            "signalSelect"
        );

    if (!select)
        return;

    select.innerHTML = "";
    latestData.forEach(trace => {
        const opt = document.createElement("option");
        opt.value = trace.name;
        opt.textContent = trace.name;
        select.appendChild(opt);
    });
}

function addWidget()
{
    const signal = document.getElementById("signalSelect").value;
    if ( signal && !widgets.includes(signal) )
    { widgets.push(signal); saveLayout(); renderDashboard();}
}

function removeWidget(signal)
{
    widgets =
        widgets.filter(
            x => x !== signal
        );

    saveLayout();

    renderDashboard();
}

function renderDashboard(){
    const dashboard = document.getElementById("dashboard");
    if (!dashboard)
        return;
    dashboard.innerHTML = "";
    widgets.forEach(signalName => {
        const trace = latestData.find( t => t.name === signalName );
        if (!trace || !trace.y || trace.y.length === 0)
        {
            return;
        }
        const lastValue = trace.y[ trace.y.length - 1];
        const unit = trace.unit || "";
        const div = document.createElement("div");
        div.className ="lcd-widget";
        div.dataset.signal = signalName;
        div.innerHTML = `
            <button class="delete-btn" onclick="removeWidget('${signalName}')">
                X hide Signal
            </button>
            <div class="lcd-name">
                ${signalName}
            </div>
            <div class="lcd-row" style="display: flex; justify-content: center; align-items: center; gap: 8px;">
                <div class="lcd-value">
                    ${Number(lastValue).toFixed(2)}
                </div>
                <div class="lcd-unit">
                    ${unit}
            </div>
        `;
        dashboard.appendChild(div);
    });
    initSortable();
}

function initSortable()
{
    const dashboard =
        document.getElementById(
            "dashboard"
        );

    if (
        !dashboard ||
        dashboard.sortableInitialized
    )
    {
        return;
    }

    dashboard.sortableInitialized = true;

    new Sortable(
        dashboard,
        {
            animation:150,
            onEnd:function(){widgets = []; document.querySelectorAll(".lcd-widget").forEach(el => {widgets.push(el.dataset.signal);});saveLayout();}
        }
    );
}

function updateSignalDashboard()
{
    fetch(
        `http://${myip}:8081/numdata`
    )
    .then(response => {

        if (!response.ok)
            throw new Error(
                `HTTP ${response.status}`
            );

        return response.json();
    })

            .then(data => {

            if (typeof latestData === "undefined") {
                latestData = data;
            }
            if (!latestData) {
            latestData = data;
            }

            // Erstes Laden: alle Signale anzeigen
            if (widgets.length === 0)
            {
                widgets = data.map(
                    trace => trace.name
                );

                saveLayout();
            }
            fillSignalSelect();
            renderDashboard();
        })
    .catch(error => {console.error("Dashboard Fehler:", error);

    });
}

function updateTrace(trace)
{
    const idx = latestData.findIndex(
        t => t.name === trace.name
    );

    if (idx >= 0) {
        latestData[idx] = trace;
    } else {
        latestData.push(trace);
        fillSignalSelect();
    }
    
}

function updateWidgetValues()
{
    fetch(`http://${myip}:8081/numdata`)
    .then(response => {
        if (!response.ok) {
            // setTimeout(updateWidgetValues, 20);
            return updateWidgetValues();
        }
        return response.json();
    })
    .then(data => {
        // Optional: globalen Zwischenspeicher ebenfalls aktuell halten

        widgets.forEach(signalName => {
            const trace = data.find(t => t.name === signalName);
            
            if (!trace || !trace.y?.length) {return;}
            // 1. Wenn trace fehlt, leer ist oder null/undefined/"None" -> sofort abbrechen
       
           
                const value = trace.y;
                
                const valueDiv = document.querySelector(`[data-signal="${signalName}"] .lcd-value`);
                // const unitDiv = document.querySelector(`[data-signal="${signalName}"] .lcd-unit`);
                
                if (valueDiv){ valueDiv.textContent = Number(value).toFixed(2);}
                updateTrace(trace);

        });
    })
    .catch(error => {console.error("Fehler beim Aktualisieren der Werte:", error);
    });
}

document.addEventListener(
    "DOMContentLoaded",
    function()
    {
        renderDashboard()
        // updateSignalDashboard();
        updateWidgetValues()
        setInterval(updateWidgetValues(), 500);
        fillSignalSelect();
    }
);
$("#addSignalBtn").click(function () {
    addWidget();
});

