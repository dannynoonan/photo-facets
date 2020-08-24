// var gmap;
// // flattened array of photos loaded from photoCollection, with generated keys and src urls 
// var loadedPhotos = [];
// // dict of photo keys to domImgs
// var keysToDomImgs = {};
// // dict of photo keys to google.maps.Marker objects
// var keysToMarkers = {};
// // dict of categories to photo keys
// var catsToKeys = {};
// // array of currently displayed keys
// var displayedMarkerKeys = [];
// var doop = 1;

// const imgBaseUrl = '/static/img/';
// const maxImgHeight = 450;
// const maxImgWidth = 600;
// const baseLatLng = {lat: 37.773972, lng: -122.431297};

// // called when page first loads
// function initGmap() {
//     console.log(photoCollection);
//     // init gmap
//     gmap = new google.maps.Map(document.getElementById('gmap'), {
//         zoom: 13,
//         center: baseLatLng,
//         mapTypeId: 'terrain'
//     });
//     // load locations from images
//     loadPhotoCollection();
//     console.log(catsToKeys);
//     // add counts to checkbox catCountSpans, check all catCheckboxes
//     for (var cat in catsToKeys) {
//         var catCountSpan = document.getElementById(cat + '_count');
//         catCountSpan.innerHTML = catsToKeys[cat].length;
//         var catCheckbox = document.getElementById(cat + '_checkbox');
//         catCheckbox.checked = true;
//     }
//     // activate photos to be displayed
//     initAndDisplayAllPhotoMarkers();
// }
      
// // 
// function loadPhotoCollection() {
//     for (var i = 0; i < photoCollection.length; i++) {		
//         neighborhood = photoCollection[i].neighborhood;
//         for (var j = 0; j < photoCollection[i].photos.length; j++) {
//         // add to loadedPhotos
//         photo = photoCollection[i].photos[j];
//         photo.key = neighborhood + '_' + photo.id;
//         photo.src = imgBaseUrl + neighborhood + '/IMG_' + photo.id + '.jpg';
//         loadedPhotos.push(photo);
//         // add keys to catsToKeys 
//         for (var k = 0; k < photo.cats.length; k++) {
//             cat = photo.cats[k];
//             if (cat in catsToKeys) {
//                 catsToKeys[cat].push(photo.key);
//             }
//             else {
//                 catsToKeys[cat] = [photo.key];
//             }
//         }
//         // add to keysToDomImgs
//         var domImg = document.createElement('div');
//         domImg.id = photo.key;
//         domImg.src = photo.src;
//         keysToDomImgs[photo.key] = domImg;
//         console.log(domImg);
//         }			
//     }
// }

// //
// function initAndDisplayAllPhotoMarkers() {
//     for (var key in keysToDomImgs) {
//         initAndDisplayPhotoMarker(keysToDomImgs[key]);
//     }   
// }

// // extract location data from domImg, init marker/add to gmap/push to markers array
// function initAndDisplayPhotoMarker(domImg) {
//     EXIF.getData(domImg, function() {
//         var imgData = EXIF.getAllTags(this);
//         console.log(imgData);				
//         // extract and calculate latitude data
//         var latData = imgData.GPSLatitude;				 			
//         var latDegree = latData[0].numerator / latData[0].denominator;
//         var latMinute = latData[1].numerator / latData[1].denominator;
//         var latSecond = latData[2].numerator / latData[2].denominator;
//         var latDirection = imgData.GPSLatitudeRef;
//         var latFinal = convertDMSToDD(latDegree, latMinute, latSecond, latDirection);
//         // extract and calculate longitude data
//         var lngData = imgData.GPSLongitude;
//         var lngDegree = lngData[0].numerator / lngData[0].denominator;
//         var lngMinute = lngData[1].numerator / lngData[1].denominator;
//         var lngSecond = lngData[2].numerator / lngData[2].denominator;
//         var lngDirection = imgData.GPSLongitudeRef;
//         var lngFinal = convertDMSToDD(lngDegree, lngMinute, lngSecond, lngDirection);
//         // extract dimensions
//         var width = imgData.PixelXDimension;
//         var height = imgData.PixelYDimension;
//         var adjustedWidth = width;
//         var adjustedHeight = height;

//         if (width > height) {
//             // landscape or pano
//             if (width > maxImgWidth) {
//                 adjustedWidth = maxImgWidth;
//                 adjustedHeight = (adjustedWidth / width) * height;
//                 console.log('landscape photo id [' + domImg.id + '] width [' + width + '] height [' + height + '] adjustedWidth [' + adjustedWidth + '] adjustedHeight [' + adjustedHeight + ']');
//             }
//         }
//         // portrait, square, or vertical pano
//         else {
//             if (height > maxImgHeight) {
//                 adjustedHeight = maxImgHeight;
//                 adjustedWidth = (adjustedHeight / height) * width;
//                 console.log('portrait photo id [' + domImg.id + '] width [' + width + '] height [' + height + '] adjustedWidth [' + adjustedWidth + '] adjustedHeight [' + adjustedHeight + ']');
//             }
//         }
          
//         // init marker
//         var marker = new google.maps.Marker({
//             position: {lat: latFinal, lng: lngFinal},
//             map: gmap,
//             title: domImg.id
//         });          
//         //
//         var contentDiv = "<div class=\"marker-window-landscape\" style=\"height:" + adjustedHeight + "; width:" + adjustedWidth + ";\"><img src=\"" + this.src + "\" height=\"" + adjustedHeight + "\" width=\"" + adjustedWidth + "\"></div>";
//         //var contentDiv = "<div class=\"marker-window-landscape\"><img src=\"" + this.src + "\" height=\"" + adjustedHeight + "\" width=\"" + adjustedWidth + "\"></div>";
//         console.log("content for photo id [" + domImg.id + "]: " + contentDiv);          
//         var markerWindow = new google.maps.InfoWindow({
//             content: contentDiv,
//             //maxWidth: 1200
//         });
//         // add listener to marker 
//         marker.addListener('click', function() {
//             markerWindow.open(gmap, marker);
//         });
//         // add marker to keysToMarkers
//         keysToMarkers[domImg.id] = marker;
//     });
// }

// function convertDMSToDD(degrees, minutes, seconds, direction) { 
//     var dd = degrees + (minutes/60) + (seconds/3600);
//     if (direction == "S" || direction == "W") {
//         dd = dd * -1; 
//     }
//     return dd;
// }

// // remove gmap from all markers to hide them, empty displayedMarkerKeys array, uncheck all category checkboxes
// function hideAllMarkers() {
//     // remove gmap from all markers to hide them
//     for (var key in keysToMarkers) {
//         keysToMarkers[key].setMap(null);
//     }
//     // reset displayedMarkerKeys array
//     displayedMarkerKeys = [];
//     // uncheck all category checkboxes
//     for (var cat in catsToKeys) {
//         var catCheckbox = document.getElementById(cat + '_checkbox');
//         catCheckbox.checked = null;
//     }
// }

// // add gmap to all markers to display them, add all markers to displayedMarkerKeys array, check all category checkboxes
// function displayAllMarkers() {
//     // add gmap to all markers to display them, add all markers to displayedMarkerKeys array
//     for (var key in keysToMarkers) {
//         keysToMarkers[key].setMap(gmap);
//         displayedMarkerKeys.push(key);        
//     }
//     // check all category checkboxes
//     for (var cat in catsToKeys) {
//         var catCheckbox = document.getElementById(cat + '_checkbox');
//         catCheckbox.checked = true;
//     }
// }

// // add gmap to subset of markers to display them, update category checkbox div and displayedMarkerKeys array
// function toggleMarkersForCategory(category) {
//     if (!(category in catsToKeys)) {
//         return;
//     } 
//     // get category checkbox element to toggle it on/off
//     var categoryCheckbox = document.getElementById(category + '_checkbox');
//     // if checkbox is checked, display markers for this category  
//     if (categoryCheckbox.checked) {
//         for (var i = 0; i < catsToKeys[category].length; i++) {
//             for (var markerKey in keysToMarkers) {
//                 if (markerKey == catsToKeys[category][i]) {
//                     keysToMarkers[markerKey].setMap(gmap);
//                     displayedMarkerKeys.push(markerKey);
//                 }
//             }
//         }
//     }

//     // if checkbox is unchecked, hide markers for this category
//     else {
//         var keysForCategory = catsToKeys[category];
//         // loop thru each key associated to the category being hidden
//         for (var i = 0; i < keysForCategory.length; i++) {
//             var keyToPotentiallyRemove = keysForCategory[i];
//             // match the key to its marker
//             for (var markerKey in keysToMarkers) {
//                 if (markerKey == keyToPotentiallyRemove) {
//                     var markerToPotentiallyRemove = keysToMarkers[markerKey];
//                     // if this key is in catsToKeys for another currently displayed cat, do not remove it
//                     var keyInOtherDisplayedCat = false;
//                     keyScan:
//                     for (var cat in catsToKeys) {
//                         // if cat is same category we're hiding: ignore
//                         if (cat == category) { continue; }
//                         // if cat isn't currently displayed: ignore
//                         var catCheckbox = document.getElementById(cat + '_checkbox');
//                         if (!(catCheckbox.checked)) { continue; }
//                         // if cat is currently displayed, look for keyToPotentiallyRemove in that 
//                         var keysForCat = catsToKeys[cat];
//                         for (var j = 0; j < keysForCat.length; j++) {
//                             if (keysForCat[j] == keyToPotentiallyRemove) {
//                             keyInOtherDisplayedCat = true;
//                             break keyScan;
//                             } 
//                         }
//                     }
//                     // if this key is not in catsToKeys for any other currently displayed cats, update its marker's map and remove it from displayedMarkerKeys array
//                     if (!(keyInOtherDisplayedCat)) {
//                     markerToPotentiallyRemove.setMap(null);
//                     var index = displayedMarkerKeys.indexOf(markerKey);
//                     if (index !== -1) displayedMarkerKeys.splice(index, 1);
//                     }
//                 }
//             }
//         }
//     }
// }
