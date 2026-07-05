function analyzeAircraft(plane){

            const analysis={
                score:0,
                level:"Routine",
                reasons:[],
                alerts:[]
            };

            if(plane.category==="Military"){
                analysis.score+=50;
                analysis.reasons.push("Military aircraft");
            }

            if(isFavorite(plane.icao_hex)){
                analysis.score+=35;
                analysis.reasons.push("Favorite aircraft");
            }

            if(plane.distance_miles<=5){
                analysis.score+=25;
                analysis.reasons.push("Within 5 miles");
            }

            else if(plane.distance_miles<=15){
                analysis.score+=10;
                analysis.reasons.push("Within 15 miles");
            }

            if(getAltitudeValue(plane)>=0 && getAltitudeValue(plane)<3000){
                analysis.score+=20;
                analysis.reasons.push("Flying below 3,000 ft");
            }

            if((plane.speed||0)>500){
                analysis.score+=15;
                analysis.reasons.push("High speed");
            }

            if((plane.aircraft_type||"").startsWith("H")){
                analysis.score+=20;
                analysis.reasons.push("Helicopter");
            }

            if(plane.category==="Unknown"){
                analysis.score+=10;
                analysis.reasons.push("Unknown classification");
            }

            if(analysis.score>=90){
                analysis.level="Critical";
            }

            else if(analysis.score>=70){
                analysis.level="High";
            }

            else if(analysis.score>=40){
                analysis.level="Elevated";
            }

            if(analysis.score>=70){
                analysis.alerts.push("Worth monitoring");
            }

            return analysis;
        }

function buildIntelligenceHtml(plane) {
            const analysis = plane.analysis || analyzeAircraft(plane);

            const scorePercent = Math.min(100, analysis.score);

            const reasonsHtml = analysis.reasons.length
                ? analysis.reasons.map(reason => `<li>✓ ${reason}</li>`).join("")
                : "<li>No unusual activity detected.</li>";

            const alertsHtml = analysis.alerts.length
                ? analysis.alerts.map(alert => `<li>⚠ ${alert}</li>`).join("")
                : "<li>No special recommendations.</li>";

            return `
                <div style="
                    margin-top:12px;
                    padding:12px;
                    border:1px solid #444;
                    background:#101010;
                    border-radius:8px;
                ">
                    <div style="
                        text-align:center;
                        font-size:16px;
                        font-weight:bold;
                        color:#4fc3f7;
                        margin-bottom:10px;
                    ">
                        SKYLOG ANALYSIS
                    </div>

                    <div style="margin-bottom:10px;">
                        <strong>Intelligence Score</strong><br>
                        <span style="font-size:26px; font-weight:bold;">
                            ${analysis.score}
                        </span>
                        <span style="color:#aaa;"> / 100</span>

                        <div style="
                            margin-top:6px;
                            height:10px;
                            background:#222;
                            border-radius:10px;
                            overflow:hidden;
                        ">
                            <div style="
                                width:${scorePercent}%;
                                height:100%;
                                background:#4fc3f7;
                            "></div>
                        </div>
                    </div>

                    <div style="margin-bottom:10px;">
                        <strong>Threat Level</strong><br>
                        <span style="font-size:18px; font-weight:bold;">
                            ${analysis.level}
                        </span>
                    </div>

                    <hr>

                    <strong>Why SkyLog Flagged This</strong>
                    <ul style="margin-top:6px; padding-left:18px;">
                        ${reasonsHtml}
                    </ul>

                    <strong>Recommendation</strong>
                    <ul style="margin-top:6px; padding-left:18px;">
                        ${alertsHtml}
                    </ul>
                </div>
            `;
        }
