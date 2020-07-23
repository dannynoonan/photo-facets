const orig_dir = 'orig/';

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
    Bind listeners when the page loads.
*/
window.onload=function(){
    // choose file button
    document.getElementById('img-file-path').onchange = function(){
        document.getElementById("init-upload-photo").style.visibility = 'visible';
    };

    // init file upload button
    document.getElementById('init-upload-photo').onclick = initUpload;

    // upload complete div operating as eventhandler flag
    uploadedImage = document.createElement('div');
    uploadedImage.id = "uploaded-image";
    uploadedImage.addEventListener("click", extractImageData);
}


/*
    Function called when file input updated. If there is a file selected, then
    start upload procedure by asking for a signed request from the app.
*/
function initUpload() {
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

                // // extract and set properties using EXIF
                // var domImg = document.createElement('div');
                // domImg.src = url;
                // EXIF.getData(domImg, extractImageData);

                // var uploadedImg = document.getElementById("uploaded-image")
                // uploadedImg.src = url;

                // trigger event allowing uploadedImage data to be extracted via EXIF without embedding that
                // function here. I'm sure there's a better way to do this but all I could figure out for now 
                uploadedImage.src = url;
                uploadedImage.click();
            }
            else {
                alert("Could not upload file: " + file.name);
            }
        }
    };
    xhr.send(postData);
}


function extractImageData() {
    EXIF.getData(uploadedImage, function() {
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
    });
}


function convertDMSToDD(degrees, minutes, seconds, direction) { 
    var dd = degrees + (minutes/60) + (seconds/3600);
    if (direction == "S" || direction == "W") {
        dd = dd * -1; 
    }
    return dd;
}


function updateNeighborhoodFormAction() {
    var baseAction = "/lockdownsf/admin/edit_neighborhood/"
    var selectedValue = document.getElementById("select-neighborhood").value;
    document.getElementById("goto-neighborhood-form").action = baseAction + selectedValue + "/";
}
