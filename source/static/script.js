
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
        // .then(data => {

        //     Plotly.react(
        //         'plotly-div',
        //         data,
        //         {
        //             title: 'CAN Signals',
        //             showlegend: true,

        //             // Zoom beibehalten
        //             uirevision: true,

        //             // Hintergrund transparent
        //             paper_bgcolor: 'rgba(0,0,0,0)',
        //             plot_bgcolor: 'rgba(0,0,0,0)'
        //         }
        //     );

        // })
        // .catch(error => {
        //     console.error("Plot Update Fehler:", error);
    //     });

    // }, 1000);
        .then(data => {

            // Alle vorhandenen Einheiten bestimmen
            const units = [...new Set(
                data.map(trace => trace.unit || "unknown")
            )];

            const layout = {
                title: 'CAN Signals',
                showlegend: true,

                // Zoom beibehalten
                uirevision: true,

                // Hintergrund transparent
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)'
            };

            // Achsen dynamisch anlegen
            units.forEach((unit, idx) => {

                const axisNo = idx + 1;

                const layoutName =
                    axisNo === 1
                        ? "yaxis"
                        : `yaxis${axisNo}`;

                layout[layoutName] = {
                    title: unit,

                    overlaying:
                        axisNo === 1
                            ? undefined
                            : "y",

                    side:
                        axisNo % 2 === 0
                            ? "right"
                            : "left",

                    showgrid: axisNo === 1
                };

                // Traces dieser Einheit zuordnen
                data.forEach(trace => {

                    if ((trace.unit || "unknown") === unit) {

                        trace.yaxis =
                            axisNo === 1
                                ? "y"
                                : `y${axisNo}`;
                    }
                });
            });

            Plotly.react(
                'plotly-div',
                data,
                layout
            );
        })
        .catch(error => {
            console.error("Plot Update Fehler:", error);
        });

}, 1000);


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

// window.onclick = function(event) {
//     if (!event.target.closest('.action-container')) {
//     document.getElementById("actionMenu").classList.remove("show");
//     }
// }


