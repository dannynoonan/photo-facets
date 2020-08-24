// var facetLabels = {
//     "mural": "Murals",
//     "boarded": "Boarded up",
//     "sign": "Signs/Messages",
//     "park": "Parks",
//     "slow_streets": "Slow streets",
//     "dining": "Restaurants",
//     "bar": "Bars",
//     "food_market": "Food markets",
//     "non_food_shop": "Shops (non food)",
//     "salon": "Salons",
//     "exercise": "Gyms/Yoga studios",
//     "laundry": "Laundry",
//     "medical": "Medical",
//     "financial": "Banks/Finance",
//     "municipal": "Municipal",
//     "performance_venue": "Performance venue",
//     "religious": "Religious",
// };

var gmap;
// dict of external_ids to media_items loaded from photoCollection 
var loadedMediaItems = {};
// dict of media_item external_ids to domImgs
var keysToDomImgs = {};
// dict of media_item external_ids to google.maps.Marker objects
var keysToMarkers = {};
// dict of categories to media_item external_ids
var catsToKeys = {};
// array of currently displayed media_item external_ids
var displayedMarkerKeys = [];

const baseLatLng = {lat: 37.773972, lng: -122.431297};

// called when page first loads
function initGmap() {
    console.log(photoCollection);
    // init gmap
    gmap = new google.maps.Map(document.getElementById('gmap'), {
        zoom: 14,
        center: baseLatLng,
        mapTypeId: 'terrain'
    });
    // load locations from images
    loadPhotoCollection();
    console.log(catsToKeys);
    // add counts to checkbox catCountSpans, check all catCheckboxes
    addFacetsToNav();
    // activate photos to be displayed
    initAndDisplayAllPhotoMarkers();
}
      
// 
function loadPhotoCollection() {
    for (var i = 0; i < photoCollection.length; i++) {		
        album = photoCollection[i].album;
        for (var j = 0; j < photoCollection[i].media_items.length; j++) {
            // add to loadedMediaItems
            var media_item = photoCollection[i].media_items[j];
            loadedMediaItems[media_item.external_id] = media_item;
            // add keys to catsToKeys 
            if (media_item.facets) {
                for (var k = 0; k < media_item.facets.length; k++) {
                    cat = media_item.facets[k];
                    if (cat in catsToKeys) {
                        catsToKeys[cat].push(media_item.external_id);
                    }
                    else {
                        catsToKeys[cat] = [media_item.external_id];
                    }
                }
            }
            // add to keysToDomImgs
            var domImg = document.createElement('div');
            domImg.id = media_item.external_id;
            domImg.src = media_item.thumb_url;
            keysToDomImgs[media_item.external_id] = domImg;
            console.log(domImg);
        }			
    }
}

function addFacetsToNav() {
    // create checkboxes with counts for all cats found in photoCollection
    for (var cat in catsToKeys) {
        // create checkbox for each facet
        var facetCheckbox = document.createElement('input');
        facetCheckbox.setAttribute('type', 'checkbox');
        facetCheckbox.id = cat + '_checkbox';
        facetCheckbox.checked = true;
        // add listener for adding/removing markers to map for category
        facetCheckbox.onclick = toggleMarkersForCategory;
        // create textNode and span element for displaying facet label and counts
        var facetLabel = document.createTextNode(cat);     
        var facetCount = document.createElement('span');
        facetCount.innerHTML = catsToKeys[cat].length;
        facetCount.className = 'badge badge-primary badge-pill';
        // wrap checkbox, textNode, and span in list item and add to facet-list
        var facetLi = document.createElement('li');
        facetLi.className = 'list-group-item d-flex justify-content-between align-items-center';
        facetLi.appendChild(facetCheckbox);
        facetLi.appendChild(facetLabel);
        facetLi.appendChild(facetCount);
        document.getElementById("facet-list").appendChild(facetLi);
    }
}

//
function initAndDisplayAllPhotoMarkers() {
    for (var key in keysToDomImgs) {
        initAndDisplayPhotoMarker(keysToDomImgs[key]);
    }   
}

//
function initAndDisplayPhotoMarker(domImg) {
    // init marker
    var latitude = parseFloat(loadedMediaItems[domImg.id].latitude);
    var longitude = parseFloat(loadedMediaItems[domImg.id].longitude);
    var marker = new google.maps.Marker({  
        position: {lat: latitude, lng: longitude},
        map: gmap,
        title: domImg.id
    });          
    //
    // var contentDiv = "<div class=\"marker-window-landscape\" style=\"height:" + adjustedHeight + "; width:" + adjustedWidth + ";\"><img src=\"" + this.src + "\" height=\"" + adjustedHeight + "\" width=\"" + adjustedWidth + "\"></div>";
    var contentDiv = "<div class=\"marker-window-landscape\"><img src=\"" + domImg.src + "\"></div>";
    console.log("content for photo id [" + domImg.id + "]: " + contentDiv);          
    var markerWindow = new google.maps.InfoWindow({
        content: contentDiv,
    });
    // add listener to marker 
    marker.addListener('click', function() {
        markerWindow.open(gmap, marker);
    });
    // add marker to keysToMarkers
    keysToMarkers[domImg.id] = marker;
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
function toggleMarkersForCategory() {
    // extract category name from checkbox element id
    var category = this.id.split('_')[0];
    // if checkbox is checked, display markers for this category  
    if (this.checked) {
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
