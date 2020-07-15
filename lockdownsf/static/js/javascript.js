var gmap;
// flattened array of photos loaded from photoCollection, with generated keys and src urls 
var loadedPhotos = [];
// dict of photo keys to domImgs
var keysToDomImgs = {};
// dict of photo keys to google.maps.Marker objects
var keysToMarkers = {};
// dict of categories to photo keys
var catsToKeys = {};
// array of currently displayed keys
var displayedMarkerKeys = [];
var doop = 1;

const imgBaseUrl = '/static/img/';
const maxImgHeight = 450;
const maxImgWidth = 600;
const baseLatLng = {lat: 37.773972, lng: -122.431297};

// called when page first loads
function initGmap() {
    console.log(photoCollection);
    // init gmap
    gmap = new google.maps.Map(document.getElementById('gmap'), {
        zoom: 13,
        center: baseLatLng,
        mapTypeId: 'terrain'
    });
    // load locations from images
    loadPhotoCollection();
    console.log(catsToKeys);
    // add counts to checkbox catCountSpans, check all catCheckboxes
    for (var cat in catsToKeys) {
        var catCountSpan = document.getElementById(cat + '_count');
        catCountSpan.innerHTML = catsToKeys[cat].length;
        var catCheckbox = document.getElementById(cat + '_checkbox');
        catCheckbox.checked = true;
    }
    // activate photos to be displayed
    initAndDisplayAllPhotoMarkers();
}
      
// 
function loadPhotoCollection() {
    for (var i = 0; i < photoCollection.length; i++) {		
        neighborhood = photoCollection[i].neighborhood;
        for (var j = 0; j < photoCollection[i].photos.length; j++) {
        // add to loadedPhotos
        photo = photoCollection[i].photos[j];
        photo.key = neighborhood + '_' + photo.id;
        photo.src = imgBaseUrl + neighborhood + '/IMG_' + photo.id + '.jpg';
        loadedPhotos.push(photo);
        // add keys to catsToKeys 
        for (var k = 0; k < photo.cats.length; k++) {
            cat = photo.cats[k];
            if (cat in catsToKeys) {
                catsToKeys[cat].push(photo.key);
            }
            else {
                catsToKeys[cat] = [photo.key];
            }
        }
        // add to keysToDomImgs
        var domImg = document.createElement('div');
        domImg.id = photo.key;
        domImg.src = photo.src;
        keysToDomImgs[photo.key] = domImg;
        console.log(domImg);
        }			
    }
}

//
function initAndDisplayAllPhotoMarkers() {
    for (var key in keysToDomImgs) {
        initAndDisplayPhotoMarker(keysToDomImgs[key]);
    }   
}

// extract location data from domImg, init marker/add to gmap/push to markers array
function initAndDisplayPhotoMarker(domImg) {
    EXIF.getData(domImg, function() {
        var imgData = EXIF.getAllTags(this);
        console.log(imgData);				
        // extract and calculate latitude data
        var latData = imgData.GPSLatitude;				 			
        var latDegree = latData[0].numerator / latData[0].denominator;
        var latMinute = latData[1].numerator / latData[1].denominator;
        var latSecond = latData[2].numerator / latData[2].denominator;
        var latDirection = imgData.GPSLatitudeRef;
        var latFinal = convertDMSToDD(latDegree, latMinute, latSecond, latDirection);
        // extract and calculate longitude data
        var lngData = imgData.GPSLongitude;
        var lngDegree = lngData[0].numerator / lngData[0].denominator;
        var lngMinute = lngData[1].numerator / lngData[1].denominator;
        var lngSecond = lngData[2].numerator / lngData[2].denominator;
        var lngDirection = imgData.GPSLongitudeRef;
        var lngFinal = convertDMSToDD(lngDegree, lngMinute, lngSecond, lngDirection);
        // extract dimensions
        var width = imgData.PixelXDimension;
        var height = imgData.PixelYDimension;
        var adjustedWidth = width;
        var adjustedHeight = height;

        if (width > height) {
            // landscape or pano
            if (width > maxImgWidth) {
                adjustedWidth = maxImgWidth;
                adjustedHeight = (adjustedWidth / width) * height;
                console.log('landscape photo id [' + domImg.id + '] width [' + width + '] height [' + height + '] adjustedWidth [' + adjustedWidth + '] adjustedHeight [' + adjustedHeight + ']');
            }
        }
        // portrait, square, or vertical pano
        else {
            if (height > maxImgHeight) {
                adjustedHeight = maxImgHeight;
                adjustedWidth = (adjustedHeight / height) * width;
                console.log('portrait photo id [' + domImg.id + '] width [' + width + '] height [' + height + '] adjustedWidth [' + adjustedWidth + '] adjustedHeight [' + adjustedHeight + ']');
            }
        }
          
        // init marker
        var marker = new google.maps.Marker({
            position: {lat: latFinal, lng: lngFinal},
            map: gmap,
            title: domImg.id
        });          
        //
        var contentDiv = "<div class=\"marker-window-landscape\" style=\"height:" + adjustedHeight + "; width:" + adjustedWidth + ";\"><img src=\"" + this.src + "\" height=\"" + adjustedHeight + "\" width=\"" + adjustedWidth + "\"></div>";
        //var contentDiv = "<div class=\"marker-window-landscape\"><img src=\"" + this.src + "\" height=\"" + adjustedHeight + "\" width=\"" + adjustedWidth + "\"></div>";
        console.log("content for photo id [" + domImg.id + "]: " + contentDiv);          
        var markerWindow = new google.maps.InfoWindow({
            content: contentDiv,
            //maxWidth: 1200
        });
        // add listener to marker 
        marker.addListener('click', function() {
            markerWindow.open(gmap, marker);
        });
        // add marker to keysToMarkers
        keysToMarkers[domImg.id] = marker;
    });
}

function convertDMSToDD(degrees, minutes, seconds, direction) { 
    var dd = degrees + (minutes/60) + (seconds/3600);
    if (direction == "S" || direction == "W") {
        dd = dd * -1; 
    }
    return dd;
}

// remove gmap from all markers to hide them, empty displayedMarkerKeys array, uncheck all category checkboxes
function hideAllMarkers() {
    // remove gmap from all markers to hide them
    for (var key in keysToMarkers) {
        keysToMarkers[key].setMap(null);
    }
    // reset displayedMarkerKeys array
    displayedMarkerKeys = [];
    // uncheck all category checkboxes
    for (var cat in catsToKeys) {
        var catCheckbox = document.getElementById(cat + '_checkbox');
        catCheckbox.checked = null;
    }
}

// add gmap to all markers to display them, add all markers to displayedMarkerKeys array, check all category checkboxes
function displayAllMarkers() {
    // add gmap to all markers to display them, add all markers to displayedMarkerKeys array
    for (var key in keysToMarkers) {
        keysToMarkers[key].setMap(gmap);
        displayedMarkerKeys.push(key);        
    }
    // check all category checkboxes
    for (var cat in catsToKeys) {
        var catCheckbox = document.getElementById(cat + '_checkbox');
        catCheckbox.checked = true;
    }
}

// add gmap to subset of markers to display them, update category checkbox div and displayedMarkerKeys array
function toggleMarkersForCategory(category) {
    if (!(category in catsToKeys)) {
        return;
    } 
    // get category checkbox element to toggle it on/off
    var categoryCheckbox = document.getElementById(category + '_checkbox');
    // if checkbox is checked, display markers for this category  
    if (categoryCheckbox.checked) {
        for (var i = 0; i < catsToKeys[category].length; i++) {
            for (var markerKey in keysToMarkers) {
                if (markerKey == catsToKeys[category][i]) {
                    keysToMarkers[markerKey].setMap(gmap);
                    displayedMarkerKeys.push(markerKey);
                }
            }
        }
    }

    // if checkbox is unchecked, hide markers for this category
    else {
        var keysForCategory = catsToKeys[category];
        // loop thru each key associated to the category being hidden
        for (var i = 0; i < keysForCategory.length; i++) {
            var keyToPotentiallyRemove = keysForCategory[i];
            // match the key to its marker
            for (var markerKey in keysToMarkers) {
                if (markerKey == keyToPotentiallyRemove) {
                    var markerToPotentiallyRemove = keysToMarkers[markerKey];
                    // if this key is in catsToKeys for another currently displayed cat, do not remove it
                    var keyInOtherDisplayedCat = false;
                    keyScan:
                    for (var cat in catsToKeys) {
                        // if cat is same category we're hiding: ignore
                        if (cat == category) { continue; }
                        // if cat isn't currently displayed: ignore
                        var catCheckbox = document.getElementById(cat + '_checkbox');
                        if (!(catCheckbox.checked)) { continue; }
                        // if cat is currently displayed, look for keyToPotentiallyRemove in that 
                        var keysForCat = catsToKeys[cat];
                        for (var j = 0; j < keysForCat.length; j++) {
                            if (keysForCat[j] == keyToPotentiallyRemove) {
                            keyInOtherDisplayedCat = true;
                            break keyScan;
                            } 
                        }
                    }
                    // if this key is not in catsToKeys for any other currently displayed cats, update its marker's map and remove it from displayedMarkerKeys array
                    if (!(keyInOtherDisplayedCat)) {
                    markerToPotentiallyRemove.setMap(null);
                    var index = displayedMarkerKeys.indexOf(markerKey);
                    if (index !== -1) displayedMarkerKeys.splice(index, 1);
                    }
                }
            }
        }
    }
}

// 
// https://devcenter.heroku.com/articles/s3-upload-python
// (function() {
//     document.getElementById("img-file-input").onchange = function(){
//         var files = document.getElementById("img-file-input").files;
//         var file = files[0];
//         if (!file) {
//             return alert("No file selected.");
//         }
//         getSignedRequest(file);
//     };
// })();


/*
    Function called when file input updated. If there is a file selected, then
    start upload procedure by asking for a signed request from the app.
*/
function initUpload(){
    const files = document.getElementById('img-file-path').files;
    const uuidFileName = document.getElementById('photo-uuid').value;
    var file = files[0];
    if (!file) {
        return alert('No file selected.');
    }
    // to replace file.name with uuid, a new file must be created
    var blob = file.slice(0, file.size, file.type); 
    var newFile = new File([blob], uuidFileName, {type: file.type});
    // retain original img file name in DOM
    document.getElementById("photo-file-name-display").innerHTML = file.name;
    document.getElementById("photo-file-name").value = file.name;
    getSignedRequest(newFile);
}

/*
    Bind listeners when the page loads.
*/
window.onload=function(){
    // choose file button
    document.getElementById('img-file-path').onchange = function(){
        document.getElementById("init-upload-photo").style.visibility = 'visible';
    };
    // init file upload button
    document.getElementById('init-upload-photo').onclick = initUpload;
}


function getSignedRequest(file) {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", "/lockdownsf/sign_s3?file_name=" + file.name + "&file_type=" + file.type);
    xhr.onreadystatechange = function(){
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                var response = JSON.parse(xhr.responseText);
                uploadFile(file, response.data, response.url);
            }
            else {
                alert("Could not get signed URL.");
            }
        }
    };
    xhr.send();
}


function uploadFile(file, s3Data, url) {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", s3Data.url);
  
    var postData = new FormData();
    for (key in s3Data.fields){
        postData.append(key, s3Data.fields[key]);
    }
    postData.append('file', file);
  
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4) {
            if (xhr.status === 200 || xhr.status === 204) {
                document.getElementById("preview").src = url;
                document.getElementById("img-properties").style.display = "block";
                document.getElementById("photo-file-path-display").innerHTML = url;
                document.getElementById("photo-file-path").value = url;           
                document.getElementById("photo-file-format-display").innerHTML = file.type;
                document.getElementById("photo-file-format").value = file.type;

                // extract and set properties using EXIF
                var domImg = document.createElement('div');
                domImg.src = url;

                // TODO extract method
                EXIF.getData(domImg, function() {
                    var imgData = EXIF.getAllTags(this);
                    console.log(imgData);				
                    // extract and calculate latitude data
                    var latData = imgData.GPSLatitude;				 			
                    var latDegree = latData[0].numerator / latData[0].denominator;
                    document.getElementById("photo-lat-degree").innerHTML = latDegree;
                    var latMinute = latData[1].numerator / latData[1].denominator;
                    document.getElementById("photo-lat-minute").innerHTML = latMinute;
                    var latSecond = latData[2].numerator / latData[2].denominator;
                    document.getElementById("photo-lat-second").innerHTML = latSecond;
                    var latDirection = imgData.GPSLatitudeRef;
                    document.getElementById("photo-lat-direction").innerHTML = latDirection;
                    var latFinal = convertDMSToDD(latDegree, latMinute, latSecond, latDirection);
                    document.getElementById("photo-latitude-display").innerHTML = latFinal;
                    document.getElementById("photo-latitude").value = latFinal;
                    // extract and calculate longitude data
                    var lngData = imgData.GPSLongitude;
                    var lngDegree = lngData[0].numerator / lngData[0].denominator;
                    document.getElementById("photo-lng-degree").innerHTML = lngDegree;
                    var lngMinute = lngData[1].numerator / lngData[1].denominator;
                    document.getElementById("photo-lng-minute").innerHTML = lngMinute;
                    var lngSecond = lngData[2].numerator / lngData[2].denominator;
                    document.getElementById("photo-lng-second").innerHTML = lngSecond;
                    var lngDirection = imgData.GPSLongitudeRef;
                    document.getElementById("photo-lng-direction").innerHTML = lngDirection;
                    var lngFinal = convertDMSToDD(lngDegree, lngMinute, lngSecond, lngDirection);
                    document.getElementById("photo-longitude-display").innerHTML = lngFinal;
                    document.getElementById("photo-longitude").value = lngFinal;
                    // extract dimensions
                    var width = imgData.PixelXDimension;
                    var height = imgData.PixelYDimension;
                    document.getElementById("photo-width-display").innerHTML = width;
                    document.getElementById("photo-width").value = width;
                    document.getElementById("photo-height-display").innerHTML = height;
                    document.getElementById("photo-height").value = height;
                    var adjustedWidth = width;
                    var adjustedHeight = height;
                    // extract date
                    var dateTaken = imgData.DateTime;
                    document.getElementById("photo-date-taken-display").innerHTML = dateTaken;
                    document.getElementById("photo-date-taken").value = dateTaken;
            
                    // if (width > height) {
                    //     // landscape or pano
                    //     if (width > maxImgWidth) {
                    //         adjustedWidth = maxImgWidth;
                    //         adjustedHeight = (adjustedWidth / width) * height;
                    //         console.log('landscape photo id [' + domImg.id + '] width [' + width + '] height [' + height + '] adjustedWidth [' + adjustedWidth + '] adjustedHeight [' + adjustedHeight + ']');
                    //     }
                    // }
                    // // portrait, square, or vertical pano
                    // else {
                    //     if (height > maxImgHeight) {
                    //         adjustedHeight = maxImgHeight;
                    //         adjustedWidth = (adjustedHeight / height) * width;
                    //         console.log('portrait photo id [' + domImg.id + '] width [' + width + '] height [' + height + '] adjustedWidth [' + adjustedWidth + '] adjustedHeight [' + adjustedHeight + ']');
                    //     }
                    // }

                });
            }
            else {
                alert("Could not upload file.");
            }
        }
    };
    xhr.send(postData);
}
