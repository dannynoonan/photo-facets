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
// dict of tags to media_item external_ids
var tagsToKeys = {};
// array of currently displayed media_item external_ids
var displayedMarkerKeys = [];

// const baseLatLng = {lat: 37.773972, lng: -122.431297};

// called when page first loads
function initGmap() {
    console.log(photoCollection);
    // init gmap
    gmap = new google.maps.Map(document.getElementById('gmap'), {
        zoom: mapMeta['zoom_level'],
        center: {
            lat: parseFloat(mapMeta['latitude']), 
            lng: parseFloat(mapMeta['longitude'])
        },
        mapTypeId: 'terrain'
    });
    // load locations from images
    loadPhotoCollection();
    // add album pulldowns, counts to checkbox tagCountSpans, and check all tagCheckboxes
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
            // add keys to tagsToKeys 
            if (media_item.tags) {
                for (var k = 0; k < media_item.tags.length; k++) {
                    tag = media_item.tags[k];
                    if (tag in tagsToKeys) {
                        tagsToKeys[tag].push(media_item.external_id);
                    }
                    else {
                        tagsToKeys[tag] = [media_item.external_id];
                    }
                }
            }
            // add to keysToDomImgs
            var domImg = document.createElement('div');
            domImg.id = media_item.external_id;
            domImg.src = media_item.thumb_url;
            keysToDomImgs[media_item.external_id] = domImg;
            // console.log(domImg);
        }			
    }
}

function addFacetsToNav() {
    // create album pulldown with counts per album in photoCollection
    if (Object.keys(allAlbums).length > 1) {  
        var albumSelect = document.createElement('select');
        albumSelect.setAttribute('id', 'album-select'); 
        albumSelect.className = 'form-control';
        albumSelect.onchange = function() {
            location = this.options[this.selectedIndex].value;
        }
        // add all-album option
        var albumOption = document.createElement('option');
        albumOption.setAttribute('value', "/lockdownsf/"); 
        // if (selectedAlbumId == "0") {
        //     albumOption.selected = true;
        // }
        var albumLabel = document.createTextNode('-- Zoom to album --'); 
        albumOption.appendChild(albumLabel); 
        albumSelect.appendChild(albumOption);  
        // add each album option
        for (var albumId in allAlbums) {
            var url = "/lockdownsf/album_map/" + albumId + "/"
            var albumOption = document.createElement('option');
            albumOption.setAttribute('value', url); 
            if (albumId == selectedAlbumId) {
                albumOption.selected = true;
            }
            var albumLabel = document.createTextNode(allAlbums[albumId]); 
            albumOption.appendChild(albumLabel); 
            albumSelect.appendChild(albumOption);     
        }
        // add select element to facet-panel
        document.getElementById('facet-panel').appendChild(albumSelect);
    }
    // create checkboxes with counts for all tags found in photoCollection
    for (var tag in tagsToKeys) {
        // create checkbox for each tag
        var tagCheckbox = document.createElement('input');
        tagCheckbox.setAttribute('type', 'checkbox');
        tagCheckbox.id = tag + '_checkbox';
        tagCheckbox.checked = true;
        // add listener for adding/removing markers to map for tag
        tagCheckbox.onclick = toggleMarkersForTag;
        // create textNode and span element for displaying tag label and counts
        var tagLabel = document.createTextNode(tag);   
        var tagCount = document.createElement('span');
        tagCount.innerHTML = tagsToKeys[tag].length;
        tagCount.className = 'badge badge-primary badge-pill';
        // wrap checkbox, textNode, and span in list item and add to facet-panel
        var tagLi = document.createElement('li');
        tagLi.className = 'list-group-item d-flex justify-content-between align-items-center';
        tagLi.appendChild(tagCheckbox);
        tagLi.appendChild(tagLabel);
        tagLi.appendChild(tagCount);
        document.getElementById('facet-panel').appendChild(tagLi);
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
    var gphotos_url = "https://photos.google.com/lr/photo/" + domImg.id;
    var contentDiv = "<div class=\"marker-window-landscape\"><a href=\"" + gphotos_url + "\" target=\"new\"><img src=\"" + domImg.src + "\"></a></div>";
    // console.log("content for photo id [" + domImg.id + "]: " + contentDiv);          
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

// remove gmap from all markers to hide them, empty displayedMarkerKeys array, uncheck all tag checkboxes
function hideAllMarkers() {
    // remove gmap from all markers to hide them
    for (var key in keysToMarkers) {
        keysToMarkers[key].setMap(null);
    }
    // reset displayedMarkerKeys array
    displayedMarkerKeys = [];
    // uncheck all tag checkboxes
    for (var tag in tagsToKeys) {
        var tagCheckbox = document.getElementById(tag + '_checkbox');
        tagCheckbox.checked = null;
    }
}

// add gmap to all markers to display them, add all markers to displayedMarkerKeys array, check all tag checkboxes
function displayAllMarkers() {
    // add gmap to all markers to display them, add all markers to displayedMarkerKeys array
    for (var key in keysToMarkers) {
        keysToMarkers[key].setMap(gmap);
        displayedMarkerKeys.push(key);        
    }
    // check all tag checkboxes
    for (var tag in tagsToKeys) {
        var tagCheckbox = document.getElementById(tag + '_checkbox');
        tagCheckbox.checked = true;
    }
}

// add gmap to subset of markers to display them, update tag checkbox div and displayedMarkerKeys array
function toggleMarkersForTag() {
    // extract tag name from checkbox element id
    var tagToToggle = this.id.split('_')[0];
    // if checkbox is checked, display markers for this tag  
    if (this.checked) {
        for (var i = 0; i < tagsToKeys[tagToToggle].length; i++) {
            for (var markerKey in keysToMarkers) {
                if (markerKey == tagsToKeys[tagToToggle][i]) {
                    keysToMarkers[markerKey].setMap(gmap);
                    displayedMarkerKeys.push(markerKey);
                }
            }
        }
    }

    // if checkbox is unchecked, hide markers for this tag
    else {
        var keysForTagToToggle = tagsToKeys[tagToToggle];
        // loop thru each key associated to the tag being hidden
        for (var i = 0; i < keysForTagToToggle.length; i++) {
            var keyToPotentiallyRemove = keysForTagToToggle[i];
            // match the key to its marker
            for (var markerKey in keysToMarkers) {
                if (markerKey == keyToPotentiallyRemove) {
                    var markerToPotentiallyRemove = keysToMarkers[markerKey];
                    // if this key is in tagsToKeys for another currently displayed tag, do not remove it
                    var keyInOtherDisplayedTag = false;
                    keyScan:
                    for (var tag in tagsToKeys) {
                        // if tag is same tag we're hiding: ignore
                        if (tag == tagToToggle) { continue; }
                        // if tag isn't currently displayed: ignore
                        var tagCheckbox = document.getElementById(tag + '_checkbox');
                        if (!(tagCheckbox.checked)) { continue; }
                        // if tag is currently displayed, look for keyToPotentiallyRemove in that 
                        var keysForTag = tagsToKeys[tag];
                        for (var j = 0; j < keysForTag.length; j++) {
                            if (keysForTag[j] == keyToPotentiallyRemove) {
                            keyInOtherDisplayedTag = true;
                            break keyScan;
                            } 
                        }
                    }
                    // if this key is not in tagsToKeys for any other currently displayed tags, update its marker's map and remove it from displayedMarkerKeys array
                    if (!(keyInOtherDisplayedTag)) {
                    markerToPotentiallyRemove.setMap(null);
                    var index = displayedMarkerKeys.indexOf(markerKey);
                    if (index !== -1) displayedMarkerKeys.splice(index, 1);
                    }
                }
            }
        }
    }
}
