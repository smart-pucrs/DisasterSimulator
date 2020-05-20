var mymap = null;
var variablesMarkerGroup = null;
var constantsMarkerGroup = null;
var startMatchFunctionId = null;
var updateStateFunctionId = null;
var stepSpeed = 1000;
var logId = '#log';
var btnLogId = '#btn-log';
var btnPauseId = '#btn-pause';
var entityBoxId = '#entity-box';
var playing = true;
var iconLength = [28, 35];
var iconAncor = [17, 18];
var currentEntity = {'type': null, 'id': null, 'active': false};

var currentStep = 0;
var currentMatch = 0;

// Markers Icons
var floodIcon = L.icon({
    iconUrl: '/static/images/flood.png',
    iconSize: iconLength,
    iconAnchor: iconAncor
});

var photoIcon = L.icon({
    iconUrl: '/static/images/photo.png',
    iconSize: iconLength,
    iconAnchor: iconAncor
});

var victimIcon0 = L.icon({
    iconUrl: '/static/images/victim_0.png',
    iconSize: iconLength,
    iconAnchor: iconAncor
});

var victimIcon1 = L.icon({
    iconUrl: '/static/images/victim_1.png',
    iconSize: iconLength,
    iconAnchor: iconAncor
});

var victimIcon2 = L.icon({
    iconUrl: '/static/images/victim_2.png',
    iconSize: iconLength,
    iconAnchor: iconAncor
});

var victimIcon3 = L.icon({
    iconUrl: '/static/images/victim_3.png',
    iconSize: iconLength,
    iconAnchor: iconAncor
});

var waterSampleIcon = L.icon({
    iconUrl: '/static/images/water_sample.png',
    iconSize: iconLength,
    iconAnchor: iconAncor
});

var agentCarIcon = L.icon({
    iconUrl: '/static/images/car.png',
    iconSize: [50, 55],
    iconAnchor: [25, 27]
});

var agentBoatIcon = L.icon({
    iconUrl: '/static/images/boat.png',
    iconSize: [50, 55],
    iconAnchor: [25, 27]
});

var agentDroneIcon = L.icon({
    iconUrl: '/static/images/drone.png',
    iconSize: [50, 55],
    iconAnchor: [25, 27]
});

var doctorIcon = L.icon({
    iconUrl: '/static/images/doctor.png',
    iconSize: [40, 45],
    iconAnchor: [15, 13]
});

var nurseIcon = L.icon({
    iconUrl: '/static/images/nurse.png',
    iconSize: [40, 45],
    iconAnchor: [15, 13]
});

var pharmacistIcon = L.icon({
    iconUrl: '/static/images/pharmacist.png',
    iconSize: [40, 45],
    iconAnchor: [15, 13]
});

var photographerIcon = L.icon({
    iconUrl: '/static/images/photographer.png',
    iconSize: [40, 45],
    iconAnchor: [15, 13]
});

var teacherIcon = L.icon({
    iconUrl: '/static/images/teacher.png',
    iconSize: [40, 45],
    iconAnchor: [15, 13]
});

var centralIcon = L.icon({
    iconUrl: '/static/images/central.png',
    iconSize: [40, 50],
    iconAnchor: [20, 25]
});

/**
 * Handle error in Json Requests
 */
function handleError(error){
    logError(error);
}

/**
 * Start draw the current match.
 */
function startMatch(){
    currentStep = 0;
    currentMatch = 0;

    fetch($SCRIPT_ROOT + '/simulator/info/matches').then(response => {
        if(response.status == 200){
            response.json().then(data => setMatchInfo(data));
        }else{
            response.json().then(error => handleError(error));
        }
    }).then(result => {
        fetch($SCRIPT_ROOT + '/simulator/match/'+currentMatch+'/info/map').then(response => {
            if(response.status == 200){
                response.json().then(data => setMapConfig(data));
    
                clearInterval(startMatchFunctionId);
                updateStateFunctionId = setInterval(nextStep, stepSpeed);
            }else{
                response.json().then(error => handleError(error));
            }
        });
    });
}

var pos_lat, pos_lon;
document.getElementById("mapid").addEventListener("contextmenu", function (event) {
    // Prevent the browser's context menu from appearing
    event.preventDefault();

    // Add marker
    // L.marker([lat, lng], ....).addTo(map);
    alert('Lat: '+pos_lat + '\nLon:' + pos_lon);

    return false; // To disable default popup.
});

/**
 * Get next step from the Flask and refresh the graphic interface.
 */
function nextStep() {
    currentStep++;
    fetch($SCRIPT_ROOT + '/simulator/match/' + currentMatch + '/step/' + currentStep).then(response => {
        if (response.status == 200) {
            response.json().then(data =>{
                process_simulation_data(data);
            });
        } else {
            response.json().then(error => handleError(error));
            currentStep--;
        }
    });

    fetch($SCRIPT_ROOT + '/simulator/info/matches').then(response => {
        if(response.status == 200){
            response.json().then(data => setMatchInfo(data));
        }else{
            response.json().then(error => handleError(error));
        }
    });
}


/**
 * Get previous step from the Flask and refresh the graphic interface.
 */
function prevStep() {
    currentStep--;
    fetch($SCRIPT_ROOT + '/simulator/match/' + currentMatch + '/step/' + currentStep).then(response => {
        if(response.status == 200){
            response.json().then(data => {
                process_simulation_data(data);
            });
        }else{
            response.json().then(error => handleError(error));
            currentStep++;
        }
    });
    
    fetch($SCRIPT_ROOT + '/simulator/info/matches').then(response => {
        if(response.status == 200){
            response.json().then(data => setMatchInfo(data));
        }else{
            response.json().then(error => handleError(error));
        }
    });
}

/**
 * Set the information of the match, the map and all events.
 */
function handle_new_match(data) {
    setMatchInfo(data['match_info']);
    setMapConfig(data['map_info']);
    process_simulation_data(data['step_info']);
}


/**
 * Get next match and refresh the graphic interface.
 */
function nextMatch() {
    currentMatch++;

    var oldStepValue = currentStep;
    currentStep = -1;

    fetch($SCRIPT_ROOT + '/simulator/match/'+currentMatch+'/info/map').then(response => {
        if(response.status == 200){
            response.json().then(data => setMapConfig(data));

            nextStep();
        }else{
            response.json().then(error => handleError(error));
            currentMatch--;
            currentStep = oldStepValue;
        }
    });
}

/**
 * Get previous match and refresh the graphic interface.
 */
function prevMatch() {
    if(currentMatch == 0){
        logError("Already in the first step.");
        return;
    }

    currentMatch--;
    var oldStepValue = currentStep;
    currentStep = -1;

    fetch($SCRIPT_ROOT + "/simulator/match/"+currentMatch+"/info/map").then(response => {
        if(response.status == 200){
            response.json().then(data => setMapConfig(data));

            nextStep();
        }else{
            response.json().then(error => console.log("asdas"));
            currentMatch++;
            currentStep = oldStepValue;
        }
    });
}

/**
 * Set information in match fields.
 */
function setMatchInfo(match_info) {
    $('#step').text((currentStep + 1) + ' of ' + match_info['total_steps']);
    $('#current-match').text((currentMatch + 1) + ' of ' + match_info['total_matches']);
}

/**
 * Set information in Map fields.
 */
function setMapConfig(config) {
    if (mymap != null) {
        mymap.remove();
    }

    mymap = L.map('mapid');
    L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw', {
        maxZoom: 19,
        attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors, ' +
            '<a href="https://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, ' +
            'Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
        id: 'mapbox.streets'
    }).addTo(mymap);

    variablesMarkerGroup = L.layerGroup().addTo(mymap);
    constantsMarkerGroup = L.layerGroup().addTo(mymap);

    let lat = parseFloat(config['centerLat']);
    let lon = parseFloat(config['centerLon']);

    mymap.setView([lat, lon], 17);

    L.marker([lat, lon], { icon: centralIcon }).addTo(constantsMarkerGroup);
    let bounds = [[config['minLat'], config['minLon']], [config['maxLat'], config['maxLon']]];

    L.rectangle(bounds, { weight: 1 }).on('click', function (e) {
        console.info(e);
    }).addTo(constantsMarkerGroup);
    console.log(config);

    mymap.addEventListener('mousemove', function(ev) {
        pos_lat = ev.latlng.lat;
        pos_lon = ev.latlng.lng;
    });

    $('#current-map').text(config['osm']);
}

/**
 * Handle the step data drawing all markers in map.
 */
function process_simulation_data(data) {
    logNormal('Processing simulation data');

    variablesMarkerGroup.clearLayers();
    currentEntity['active'] = false;

    let events = data['environment']['events'];
    let old_locations = [];
    let marker;
    for (let i=0; i < events.length; i++) {
        event_location = events[i]['location'];

        event_location = format_location(event_location, old_locations);
        old_locations.push(event_location);
        event_location_formatted = [events[i]['location']['lat'], events[i]['location']['lon']];

        marker = null;
        switch (events[i]['type']) {
            case 'flood':
                marker = L.marker(event_location_formatted, { icon: floodIcon });
                L.circle(event_location_formatted, {
                    color: '#504E0F',
                    fillColor: '#504E0F',
                    fillOpacity: 0.65,
                    radius: events[i]['radius'] * 109000
                }).addTo(variablesMarkerGroup);
                break;
            case 'victim':
                if (events[i]['lifetime'] == 0) {
                    marker = L.marker(event_location_formatted, { icon: victimIcon3 });
                }
                else if (events[i]['lifetime'] < 5) {
                    marker = L.marker(event_location_formatted, { icon: victimIcon2 });
                } else if (events[i]['lifetime'] < 10) {
                    marker = L.marker(event_location_formatted, { icon: victimIcon1 });
                } else {
                    marker = L.marker(event_location_formatted, { icon: victimIcon0 });
                }
                break;
            case 'photo':
                marker = L.marker(event_location_formatted, { icon: photoIcon });
                break;
            case 'water_sample':
                marker = L.marker(event_location_formatted, { icon: waterSampleIcon });
                break;
            default:
                continue;
        }

        if (events[i]['type'] == currentEntity['type']){
            if (events[i]['identifier'] == currentEntity['id']){
                setCurrentEntity(events[i]);
            }
        }

        marker.on('click', function (e) {setCurrentEntity(e.sourceTarget.info)});  
        marker.info = events[i];
        marker.addTo(variablesMarkerGroup);
    }

    let actors = data['actors'];
    $('#active-agents').text(actors.length);

    for (let i=0; i < actors.length; i++) {
        type = actors[i]['type'];

        agent_location = format_location(actors[i]['location'], old_locations);
        old_locations.push(agent_location);
        agent_location_formated = [agent_location['lat'], agent_location['lon']];

        marker = null;
        if (type == 'agent'){
            switch(actors[i]['role']){
                case 'drone':
                    marker = L.marker(agent_location_formated, { icon: agentDroneIcon });
                    break;
                case 'car':
                    marker = L.marker(agent_location_formated, { icon: agentCarIcon });
                    break;
                case 'boat':
                    marker = L.marker(agent_location_formated, { icon: agentBoatIcon });
                    break;
                case 'analyser':
                    marker = L.marker(agent_location_formated, { icon: agentBoatIcon });
                    break;
                case 'collector':
                    marker = L.marker(agent_location_formated, { icon: agentBoatIcon });
                    break;
                case 'truck':
                    marker = L.marker(agent_location_formated, { icon: doctorIcon });
                    break;
                case 'ugv':
                    marker = L.marker(agent_location_formated, { icon: nurseIcon });
                    break;
                case 'helicopter':
                    marker = L.marker(agent_location_formated, { icon: photographerIcon });
                    break;
                default:
                    logError('Role not found.');
                    continue;
            }
        }else{
            switch(actors[i]['profession']){
                case 'doctor':
                    marker = L.marker(agent_location_formated, { icon: doctorIcon });
                    break;
                case 'nurse':
                    marker = L.marker(agent_location_formated, { icon: nurseIcon });
                    break;
                case 'pharmacist':
                    marker = L.marker(agent_location_formated, { icon: pharmacistIcon });
                    break;
                case 'teacher':
                    marker = L.marker(agent_location_formated, { icon: teacherIcon });
                    break;
                case 'photographer':
                    marker = L.marker(agent_location_formated, { icon: photographerIcon });
                    break;
                case 'vonlunteer':
                    marker = L.marker(agent_location_formated, { icon: teacherIcon });
                    break;
                default:
                    logError('Profession not found.');
                    continue;
            }
        }

        if (actors[i]['type'] == currentEntity['type']){
            if (actors[i]['token'] == currentEntity['id']){
                setCurrentEntity(actors[i]);
            }
        }

        marker.on('click', onClickMarkerHandler);  
        marker.info = actors[i];
        marker.addTo(variablesMarkerGroup);

        printRoute(actors[i]['route']);

    }

    if (!currentEntity['active']){
        $(entityBoxId).hide();
    }
}

/**
 * Handler for all 'onClick' event from markers.
 */
function onClickMarkerHandler(event){
    if (event.sourceTarget.info != undefined){
        setCurrentEntity(event.sourceTarget.info);
    }
}

/**
 * Set information in entity info fields.
 */
function setCurrentEntity(info){
    $("#entity-list-info").empty();

    if ($(entityBoxId).is(':hidden')){
        $(entityBoxId).show();
    }
    let value;

    for (let key in info){
        switch (key) {
            case 'location':
                value = "[ " + info[key]['lat'] + ", " + info[key]['lon'] + " ]";
                break;
            case 'route':
                value = []
                for(let i=0; i<info[key].length; i++){
                    value.push("["+info[key][i]['lat']+","+info[key][i]['lon']+"]");
                }
                break;
            case 'destination_distance':
                value = (info[key] * 100).toFixed(2).toString() + ' km';
                break;
            case 'social_assets':
                value = [];
                let location, temp;
                for (let i=0; i<info[key].length; i++){
                    temp = info[key][i];
                    delete temp['location'];
                    value.push(temp);
                }

                break;
            case 'radius':
                value = (info[key] * 100).toFixed(2).toString() + ' km';
                break;
            default:
                value = info[key];
        }
        $("#entity-list-info").append("<li><b>"+key+":</b> "+value+"</li>");
    }

    currentEntity['type'] = info['type'];
    currentEntity['active'] = true;
    if (info['type'] == 'agent' || info['type'] == 'social_asset'){
        currentEntity['id'] = info['token'];
    }else{
        currentEntity['id'] = info['identifier'];
    }
}

/**
 * Check whether the entered location is within the array given.
 */
function containsLocation(locations, location){
    for (let i=0; i < locations.length; i++){
        if (locations[i]['lat'] == location['lat']){
            if (locations[i]['lon'] == location['lon']) return true;
        }
    }

    return false;
}

/**
 * Format the location incrementing the lat coordination by 1/10000.
 */
function format_location(event_location, old_locations){
    let new_location = event_location;
    let alfa = 0.0001;

    while (containsLocation(old_locations, new_location)){
        new_location['lat'] += alfa;
    }

    return new_location;
}

/**
 * Initialize the simulator info fields.
 */
function init() {
    logNormal('Initializing variables.');

    fetch($SCRIPT_ROOT + '/simulator/info/config').then(response => {
        if(response.status == 200){
            response.json().then(data => setSimulationInfo(data));
            startMatchFunctionId = setInterval(startMatch, stepSpeed);
        }else{
            response.json().then(error => handleError(error.message));
        }
    });

}

/**
 * Draw the route given with red circles.
 */
function printRoute(route){
    for (let i=0; i<route.length; i++){
        L.circle([route[i]['lat'], route[i]['lon']], {
                color: 'red',
                radius: 10
        }).addTo(variablesMarkerGroup);
    }

}

/**
 * Set simulation info fields.
 */
function setSimulationInfo(sim_info) {
    $('#simulation-url').text(sim_info['simulation_url']);
    $('#api-url').text(sim_info['api_url']);
    $('#max-agents').text(sim_info['max_agents']);
    $('#first-step-time').text(sim_info['first_step_time']);
    $('#step-time').text(sim_info['step_time']);
    $('#social-asset-timeout').text(sim_info['social_asset_timeout']);
}

/**
 * Pause the next step interval.
 */
function pause() {
    if (playing) {
        logNormal('Paused.');

        clearInterval(updateStateFunctionId);
        $(btnPauseId).text('Play');
        playing = false;
    } else {
        logNormal('Playing.');

        updateStateFunctionId = setInterval(nextStep, stepSpeed);
        $(btnPauseId).text('Pause');
        playing = true;
    }
}

/**
 * Hide or Show the log field.
 */
function setLog() {
    if ($(logId).is(':hidden')) {
        logNormal('Hiding Log.');

        $(logId).show();
        $(btnLogId).text('Hide log');
    } else {
        logNormal('Showing Log.');

        $(logId).hide();
        $(btnLogId).text('Show log');
    }
}

/**
 * Event handler for radio box field.
 */
$(function () {
    $('#speed input[type=radio]').change(function(){
        stepSpeed = parseInt(this.value);
        
        if (playing){
            clearInterval(updateStateFunctionId);
            updateStateFunctionId = setInterval(nextStep, stepSpeed);
        }

        logNormal("Step speed change to " + $(this).val() + " ms");
  
    })
})

/**
 * Add log in text area.
 */
function log(tag, message) {
    var oldText = $(logId).val();
    var formattedText = oldText + '\n[ ' + tag + ' ] ## ' + message;
    $(logId).focus().val(formattedText);
}

function logNormal(message) {
    log('NORMAL', message);
}

function logError(message) {
    log('ERROR', message);
}

function logCritical(message) {
    log('CRITICAL', message);
}

$(entityBoxId).hide();

window.onload = function () {
    this.init();
};