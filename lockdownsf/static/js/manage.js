const orig_dir = 'orig/';


// https://www.smashingmagazine.com/2018/01/drag-drop-file-uploader-vanilla-js/
let filesDone = 0
let filesToDo = 0


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
window.onload=function() {

    // https://www.smashingmagazine.com/2018/01/drag-drop-file-uploader-vanilla-js/
    dropArea = document.getElementById('drop-area')
    ;['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false)
    })
    ;['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false)
    })
    ;['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false)
    })
    dropArea.addEventListener('drop', handleDrop, false)
    progressBar = document.getElementById('progress-bar')



    // // choose file button
    // document.getElementById('img-file-path').onchange = function() {
    //     document.getElementById("init-upload-photo").style.visibility = 'visible';
    // };

    // // init file upload button
    // document.getElementById('init-upload-photo').onclick = initSingleUpload;

    // // upload complete div operating as eventhandler flag
    // uploadedImage = document.createElement('div');
    // uploadedImage.id = "uploaded-image";
    // uploadedImage.addEventListener("click", extractImageData);
}



// https://www.smashingmagazine.com/2018/01/drag-drop-file-uploader-vanilla-js/
function preventDefaults(e) {
    e.preventDefault()
    e.stopPropagation()
}

function highlight(e) {
    dropArea.classList.add('highlight')
}

function unhighlight(e) {
    dropArea.classList.remove('highlight')
}

function handleDrop(e) {
    let dt = e.dataTransfer
    let files = dt.files

    handleFiles(files)
}

function handleFiles(files) {
    files = [...files]
    initializeProgress(files.length)
    files.forEach(uploadFile)
    files.forEach(previewFile)
}

function uploadFile(file, i) { 
    var url = 'YOUR URL HERE'
    var xhr = new XMLHttpRequest()
    var formData = new FormData()
    xhr.open('POST', url, true)

    // Add following event listener
    xhr.upload.addEventListener("progress", function(e) {
        updateProgress(i, (e.loaded * 100.0 / e.total) || 100)
    })

    xhr.addEventListener('readystatechange', function(e) {
        if (xhr.readyState == 4 && xhr.status == 200) {
            // Done. Inform the user
        }
        else if (xhr.readyState == 4 && xhr.status != 200) {
            // Error. Inform the user
        }
    })

    formData.append('file', file)
    xhr.send(formData)
}

function previewFile(file) {
    let reader = new FileReader()
    reader.readAsDataURL(file)
    reader.onloadend = function() {
        let img = document.createElement('img')
        img.src = reader.result
        document.getElementById('gallery').appendChild(img)
    }
}

function initializeProgress(numFiles) {
    progressBar.value = 0
    uploadProgress = []
  
    for (let i = numFiles; i > 0; i--) {
        uploadProgress.push(0)
    }
}
  
function updateProgress(fileNumber, percent) {
    uploadProgress[fileNumber] = percent
    let total = uploadProgress.reduce((tot, curr) => tot + curr, 0) / uploadProgress.length
    progressBar.value = total
}





function makeTagStatusEditable(tag_id) {
    // TODO replace this with metadata or function argument
    var all_tag_statuses = ["ACTIVE", "DISABLED"];
    // get tag status element we're modifying
    var tagStatusDisplayCellEl = document.getElementById("tag-status-display-cell-" + tag_id);
    var tagStatusDisplayEl = document.getElementById("tag-status-display-" + tag_id);
    //var curr_status = tagStatusDisplayEl.innerHTML;
    // tagStatusDisplayEl.style.visibility = 'hidden';
    // tagStatusDisplayEl.onclick = '';
    tagStatusDisplayEl.remove();
    tagStatusDisplayCellEl.remove();

    // display hidden elements
    document.getElementById("tag-status-select-cell-" + tag_id).style.visibility = 'visible';
    document.getElementById("tag-status-select-" + tag_id).style.visibility = 'visible';
    document.getElementById("tag-submit-cell-" + tag_id).style.visibility = 'visible';
    document.getElementById("tag-submit-" + tag_id).style.visibility = 'visible';

    // Leaving the rest of this swill to remind myself to avoid gratutitous HTML-JS fuckstick sidework any and every time I can
    // Apparently adding an input element (via js) to the middle of a (html) form isn't sufficient to have the contents of that
    // input element posted along with the other contents of the form. Or if it is, the solution eluded me for hours.
    // YGBFKM this is what I'm doing with my life. 

    // add status dropdown, with curr_status selected
    // var tagStatusSelectEl = document.createElement("select");
    // tagStatusSelectEl.id = "tag-status-select-" + tag_id;
    // tagStatusSelectEl.name = "tag-status-select-" + tag_id;
    // tagStatusSelectEl.setAttribute("class", "form-control");
    // for (var i=0; i<all_tag_statuses.length; i++) {
    //     var optionEl = document.createElement('option');
    //     optionEl.value = all_tag_statuses[i];
    //     optionEl.innerHTML = all_tag_statuses[i];
    //     if (curr_status == all_tag_statuses[i]) {
    //         optionEl.selected = true;
    //     }
    //     tagStatusSelectEl.appendChild(optionEl);
    // }
    // tagStatusCellEl.appendChild(tagStatusSelectEl);

    // append submit button
    // var tagSubmitEl = document.getElementById("tag-submit-" + tag_id);
    // var submitEl = document.createElement('input');
    // submitEl.setAttribute("type", "submit");
    // submitEl.value = "Update";
    // tagSubmitEl.appendChild(submitEl);

    // create for within js, unable to get html form to acknowledge js-created input button
    // var formEl = document.createElement('form');
    // formEl.action = "/lockdownsf/manage/tag_edit/";
    // formEl.method = "POST";

    // var formEl = document.getElementById('tag-form-' + tag_id);
    // formEl.appendChild(submitEl);
    // var formHtml = formEl.innerHTML;
}


// https://stackoverflow.com/questions/24718769/html5-javascript-how-to-get-the-selected-folder-name
function selectFolder(e) {
    var files = e.target.files;
    var relativePath = files[0].webkitRelativePath;
    var folder = relativePath.split("/");

    // var el = document.getElementById("multi-file-upload").value = relativePath;
    // alert(folder[0]);

    initUpload(files)
}


function initUpload(files) {
    // const files = document.getElementById('multi-file-upload').files;
    if (!files) {
        return alert('No files found in directory.');
    }

    for (var i=0; i<files.length; i++) {
        getSignedRequest(files[i], i);
    }
}


function getSignedRequest(file, sequence) {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", "/lockdownsf/sign_s3?file_name=" + file.name + "&file_type=" + file.type);
    xhr.onreadystatechange = function(){
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                var response = JSON.parse(xhr.responseText);
                uploadFileClassic(file, sequence, response.data, response.url);
            }
            else {
                alert("Could not get signed URL for file [" + file.name + "] sequence [" + sequence + "]");
            }
        }
    };
    xhr.send();
}


function uploadFileClassic(file, sequence, s3Data, url) {
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
                // display new image table and album creation form, hide file selector 
                var tableEl = document.getElementById("image-preview-table");
                tableEl.style.display = "block"; 
                document.getElementById("album-create-form").style.display = "block";
                document.getElementById("file-upload-selector").style.display = "none";

                // add row to image preview table for each image added to s3
                var rowEl = tableEl.insertRow(-1);
                // checkbox
                var checkboxCellEl = rowEl.insertCell(-1);
                var checkboxEl = document.createElement('input')
                checkboxEl.setAttribute("type", "checkbox");
                checkboxEl.name = "images-to-upload";
                checkboxEl.value = url
                checkboxEl.checked = true;
                checkboxCellEl.appendChild(checkboxEl);
                // image
                var imgCellEl = rowEl.insertCell(-1);
                var imgEl = document.createElement('img');
                imgEl.src = url;
                imgEl.width = 200;
                var imgLinkEl = document.createElement('a');
                imgLinkEl.href = url;
                imgLinkEl.target = "new";
                imgLinkEl.appendChild(imgEl);
                imgCellEl.appendChild(imgLinkEl);
                // filename
                var filenameCellEl = rowEl.insertCell(-1);
                filenameCellEl.innerHTML = file.name;
                // filetype
                var filetypeCellEl = rowEl.insertCell(-1);
                filetypeCellEl.innerHTML = file.type;

                // increment the image counter - TODO have this interact with sequence value and a slider widget
                var image_count = tableEl.rows.length - 1;
                document.getElementById("album-create-label").innerHTML = image_count + " images staged and ready for import";

                // // extract and set properties using EXIF
                // var domImg = document.createElement('div');
                // domImg.src = url;
                // EXIF.getData(domImg, extractImageData);
            }
            else {
                alert("Could not upload file: " + file.name);
            }
        }
    };
    xhr.send(postData);
}





/*
    Function called when file input updated. If there is a file selected, then
    start upload procedure by asking for a signed request from the app.
*/
function initSingleUpload() {
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
    getSingleSignedRequest(newFile);
}


function getSingleSignedRequest(file) {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", "/lockdownsf/sign_s3?file_name=" + file.name + "&file_type=" + file.type);
    xhr.onreadystatechange = function(){
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                var response = JSON.parse(xhr.responseText);
                uploadSingleFile(file, response.data, response.url);
            }
            else {
                alert("Could not get signed URL.");
            }
        }
    };
    xhr.send();
}


function uploadSingleFile(file, s3Data, url) {
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


function updateAlbumFormAction() {
    var baseAction = "/lockdownsf/manage/album_view/"
    var selectedValue = document.getElementById("select-album").value;
    document.getElementById("goto-album-form").action = baseAction + selectedValue + "/";
}
