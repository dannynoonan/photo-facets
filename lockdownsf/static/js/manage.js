// const orig_dir = 'orig/';


// https://www.smashingmagazine.com/2018/01/drag-drop-file-uploader-vanilla-js/
// let filesDone = 0
// let filesToDo = 0


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
//window.onload=function() {

    // https://www.smashingmagazine.com/2018/01/drag-drop-file-uploader-vanilla-js/
    // dropArea = document.getElementById('drop-area')
    // ;['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    //     dropArea.addEventListener(eventName, preventDefaults, false)
    // })
    // ;['dragenter', 'dragover'].forEach(eventName => {
    //     dropArea.addEventListener(eventName, highlight, false)
    // })
    // ;['dragleave', 'drop'].forEach(eventName => {
    //     dropArea.addEventListener(eventName, unhighlight, false)
    // })
    // dropArea.addEventListener('drop', handleDrop, false)
    // progressBar = document.getElementById('progress-bar')



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
//}



// https://www.smashingmagazine.com/2018/01/drag-drop-file-uploader-vanilla-js/
// function preventDefaults(e) {
//     e.preventDefault()
//     e.stopPropagation()
// }

// function highlight(e) {
//     dropArea.classList.add('highlight')
// }

// function unhighlight(e) {
//     dropArea.classList.remove('highlight')
// }

// function handleDrop(e) {
//     let dt = e.dataTransfer
//     let files = dt.files

//     handleFiles(files)
// }

// function handleFiles(files) {
//     files = [...files]
//     initializeProgress(files.length)
//     files.forEach(uploadFile)
//     files.forEach(previewFile)
// }

// function uploadFile(file, i) { 
//     var url = 'YOUR URL HERE'
//     var xhr = new XMLHttpRequest()
//     var formData = new FormData()
//     xhr.open('POST', url, true)

//     // Add following event listener
//     xhr.upload.addEventListener("progress", function(e) {
//         updateProgress(i, (e.loaded * 100.0 / e.total) || 100)
//     })

//     xhr.addEventListener('readystatechange', function(e) {
//         if (xhr.readyState == 4 && xhr.status == 200) {
//             // Done. Inform the user
//         }
//         else if (xhr.readyState == 4 && xhr.status != 200) {
//             // Error. Inform the user
//         }
//     })

//     formData.append('file', file)
//     xhr.send(formData)
// }

// function previewFile(file) {
//     let reader = new FileReader()
//     reader.readAsDataURL(file)
//     reader.onloadend = function() {
//         let img = document.createElement('img')
//         img.src = reader.result
//         document.getElementById('gallery').appendChild(img)
//     }
// }

// function initializeProgress(numFiles) {
//     progressBar.value = 0
//     uploadProgress = []
  
//     for (let i = numFiles; i > 0; i--) {
//         uploadProgress.push(0)
//     }
// }
  
// function updateProgress(fileNumber, percent) {
//     uploadProgress[fileNumber] = percent
//     let total = uploadProgress.reduce((tot, curr) => tot + curr, 0) / uploadProgress.length
//     progressBar.value = total
// }





function makeTagStatusEditable(tag_id) {
    // get tag status element we're modifying
    var tagStatusDisplayCellEl = document.getElementById("tag-status-display-cell-" + tag_id);
    var tagStatusDisplayEl = document.getElementById("tag-status-display-" + tag_id);
    tagStatusDisplayEl.remove();
    tagStatusDisplayCellEl.remove();

    // display hidden elements
    document.getElementById("tag-status-select-cell-" + tag_id).style.visibility = 'visible';
    document.getElementById("tag-status-select-" + tag_id).style.visibility = 'visible';
    document.getElementById("tag-submit-cell-" + tag_id).style.visibility = 'visible';
    document.getElementById("tag-submit-" + tag_id).style.visibility = 'visible';
}


function makeTagsEditable() {
    // remove display elements
    document.getElementById("tag-display-cell").remove();

    // display hidden elements
    document.getElementById("tag-checkbox-cell").setAttribute("class", "");

    // activate flag
    document.getElementById("update-tags-flag").value = "true";

    // display submit button
    document.getElementById("submit-cell").setAttribute("class", "");
}


function makeDescriptionEditable() {
    // remove display elements
    document.getElementById("description-display-cell").remove();

    // display hidden elements
    document.getElementById("description-input-cell").setAttribute("class", "");

    // activate flag
    document.getElementById("update-description-flag").value = "true";

    // display submit button
    document.getElementById("submit-cell").setAttribute("class", "");
}


function makeAlbumNameEditable() {
    // remove display elements
    document.getElementById("album-name-display-cell").remove();

    // display hidden elements
    document.getElementById("album-name-input-cell").setAttribute("class", "");

    // activate flag
    document.getElementById("update-album-name-flag").value = "true";

    // display submit button
    document.getElementById("submit-cell").setAttribute("class", "");
}


var totalFileCount = 0;
var successFileCount = 0;
var failedFiles = [];
var totalRetryCount = 0;

// https://stackoverflow.com/questions/24718769/html5-javascript-how-to-get-the-selected-folder-name
function selectFolder(e) {
    var files = e.target.files;
    totalFileCount = files.length;  // TODO weed out non-images?  oversized images?
    var relativePath = files[0].webkitRelativePath;
    var folder = relativePath.split("/");

    document.getElementById("album-import-progress").style.display = 'block';

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
        // exclude non-image files
        fileSuperType = files[i].type.split("/")[0];
        // alert('fileSuperType: ' + fileSuperType)
        if (fileSuperType != "image") {
            addToFailedFiles(files[i].name);
        }
        else {
            getSignedRequest(files[i], i, 0);
        }
    }
}


function getSignedRequest(file, sequence, retryCount) {
    // handle failed requests
    if (retryCount > 5) {
        // alert("Could not get signed URL for file [" + file.name + "] sequence [" + sequence + "]");
        addToFailedFiles(file.name);
        if (successFileCount + failedFiles.length == totalFileCount) {
            // alert("Total retry count: " + totalRetryCount);
            document.getElementById("album-create-submit").style.display = 'block';
        }
    }
    // create request
    var xhr = new XMLHttpRequest();
    var tmp_dir = document.getElementById("tmp-dir-uuid").value;
    xhr.open("GET", "/lockdownsf/sign_s3?file_name=" + tmp_dir + "/" + file.name + "&file_type=" + file.type);
    xhr.onreadystatechange = function(){
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                var response = JSON.parse(xhr.responseText);
                uploadFileClassic(file, sequence, response.data, response.url);
            }
            else {
                // alert("Could not get signed URL for file [" + file.name + "] sequence [" + sequence + "]");
                totalRetryCount++;
                getSignedRequest(file, sequence, retryCount+1)
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
                document.getElementById("album-import-photos-form").style.display = "block";
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
                //var image_count = tableEl.rows.length - 1;
                document.getElementById("s3-upload-success").style.display = 'block';
                successFileCount++;
                document.getElementById("s3-upload-success").innerHTML = successFileCount + " images staged and ready for import.";

                // progress bar
                var procdFilePct = Math.floor(90 * (successFileCount + failedFiles.length) / totalFileCount) + 10;
                var progressBar = document.getElementById("album-import-progress-bar");
                progressBar.setAttribute("aria-valuenow", procdFilePct);
                progressBar.style.width = procdFilePct+"%";
                if (procdFilePct >= 100) {
                    document.getElementById("album-import-progress").style.display = 'none';
                }

                if (successFileCount + failedFiles.length == totalFileCount) {
                    // alert("Total retry count: " + totalRetryCount);
                    document.getElementById("album-import-photos-submit").style.display = 'block';
                }

                // // extract and set properties using EXIF
                // var domImg = document.createElement('div');
                // domImg.src = url;
                // EXIF.getData(domImg, extractImageData);
            }
            else {
                // alert("Could not upload file: " + file.name);
                addToFailedFiles(file.name);
                if (successFileCount + failedFiles.length == totalFileCount) {
                    // alert("Total retry count: " + totalRetryCount);
                    document.getElementById("album-import-photos-submit").style.display = 'block';
                }
            }
        }
    };
    xhr.send(postData);
}


// this function is hideous, it regenerates the whole shebang from scratch each time it's called
function addToFailedFiles(fileName) {
    failedFiles.push(fileName);
    failure_message = failedFiles.length + " images failed to be staged for upload: <ul>";
    for (var i=0; i<failedFiles.length; i++) {
        failure_message += "<li>" + failedFiles[i] + "</li>";
    }
    failure_message += "</ul>";
    document.getElementById("s3-upload-failure").style.display = 'block';
    document.getElementById("s3-upload-failure").innerHTML = failure_message;
}



function showOrHideAlbumTitleInput() {
    var selectedAlbum = document.getElementById("select-album-id").value;
    if (selectedAlbum == 0) {
        document.getElementById("new-album-name").style.display = "block";
    }
    else {
        document.getElementById("new-album-name").style.display = "none";
    }
}


function updateAlbumFormAction() {
    var baseAction = "/lockdownsf/manage/album_view/"
    var selectedValue = document.getElementById("select-album").value;
    document.getElementById("goto-album-form").action = baseAction + selectedValue + "/";
}





/*
    Function called when file input updated. If there is a file selected, then
    start upload procedure by asking for a signed request from the app.
*/
// function initSingleUpload() {
//     const files = document.getElementById('img-file-path').files;
//     const uuidFileName = document.getElementById('photo-uuid').value;
//     var file = files[0];
//     if (!file) {
//         return alert('No file selected.');
//     }
//     // to replace file.name with uuid, a new file must be created
//     var blob = file.slice(0, file.size, file.type); 
//     var newFile = new File([blob], uuidFileName, {type: file.type});
//     // retain original img file name in DOM
//     document.getElementById("photo-file-name-display").innerHTML = file.name;
//     document.getElementById("photo-file-name").value = file.name;
//     getSingleSignedRequest(newFile);
// }


// function getSingleSignedRequest(file) {
//     var xhr = new XMLHttpRequest();
//     xhr.open("GET", "/lockdownsf/sign_s3?file_name=" + file.name + "&file_type=" + file.type);
//     xhr.onreadystatechange = function(){
//         if (xhr.readyState === 4) {
//             if (xhr.status === 200) {
//                 var response = JSON.parse(xhr.responseText);
//                 uploadSingleFile(file, response.data, response.url);
//             }
//             else {
//                 alert("Could not get signed URL.");
//             }
//         }
//     };
//     xhr.send();
// }


// function uploadSingleFile(file, s3Data, url) {
//     var xhr = new XMLHttpRequest();
//     xhr.open("POST", s3Data.url);
  
//     var postData = new FormData();
//     for (key in s3Data.fields){
//         postData.append(key, s3Data.fields[key]);
//     }
//     postData.append('file', file);
  
//     xhr.onreadystatechange = function() {
//         if (xhr.readyState === 4) {
//             if (xhr.status === 200 || xhr.status === 204) {
//                 document.getElementById("preview").src = url;
//                 document.getElementById("img-properties").style.display = "block";
//                 document.getElementById("photo-file-path-display").innerHTML = url;
//                 document.getElementById("photo-file-path").value = url;           
//                 document.getElementById("photo-file-format-display").innerHTML = file.type;
//                 document.getElementById("photo-file-format").value = file.type;

//                 // // extract and set properties using EXIF
//                 // var domImg = document.createElement('div');
//                 // domImg.src = url;
//                 // EXIF.getData(domImg, extractImageData);

//                 // var uploadedImg = document.getElementById("uploaded-image")
//                 // uploadedImg.src = url;

//                 // trigger event allowing uploadedImage data to be extracted via EXIF without embedding that
//                 // function here. I'm sure there's a better way to do this but all I could figure out for now 
//                 uploadedImage.src = url;
//                 uploadedImage.click();
//             }
//             else {
//                 alert("Could not upload file: " + file.name);
//             }
//         }
//     };
//     xhr.send(postData);
// }


// function extractImageData() {
//     EXIF.getData(uploadedImage, function() {
//         var imgData = EXIF.getAllTags(this);
//         console.log(imgData);				
//         // extract and calculate latitude data
//         var latData = imgData.GPSLatitude;				 			
//         var latDegree = latData[0].numerator / latData[0].denominator;
//         document.getElementById("photo-lat-degree").innerHTML = latDegree;
//         var latMinute = latData[1].numerator / latData[1].denominator;
//         document.getElementById("photo-lat-minute").innerHTML = latMinute;
//         var latSecond = latData[2].numerator / latData[2].denominator;
//         document.getElementById("photo-lat-second").innerHTML = latSecond;
//         var latDirection = imgData.GPSLatitudeRef;
//         document.getElementById("photo-lat-direction").innerHTML = latDirection;
//         var latFinal = convertDMSToDD(latDegree, latMinute, latSecond, latDirection);
//         document.getElementById("photo-latitude-display").innerHTML = latFinal;
//         document.getElementById("photo-latitude").value = latFinal;
//         // extract and calculate longitude data
//         var lngData = imgData.GPSLongitude;
//         var lngDegree = lngData[0].numerator / lngData[0].denominator;
//         document.getElementById("photo-lng-degree").innerHTML = lngDegree;
//         var lngMinute = lngData[1].numerator / lngData[1].denominator;
//         document.getElementById("photo-lng-minute").innerHTML = lngMinute;
//         var lngSecond = lngData[2].numerator / lngData[2].denominator;
//         document.getElementById("photo-lng-second").innerHTML = lngSecond;
//         var lngDirection = imgData.GPSLongitudeRef;
//         document.getElementById("photo-lng-direction").innerHTML = lngDirection;
//         var lngFinal = convertDMSToDD(lngDegree, lngMinute, lngSecond, lngDirection);
//         document.getElementById("photo-longitude-display").innerHTML = lngFinal;
//         document.getElementById("photo-longitude").value = lngFinal;
//         // extract dimensions
//         var width = imgData.PixelXDimension;
//         var height = imgData.PixelYDimension;
//         document.getElementById("photo-width-display").innerHTML = width;
//         document.getElementById("photo-width").value = width;
//         document.getElementById("photo-height-display").innerHTML = height;
//         document.getElementById("photo-height").value = height;
//         var adjustedWidth = width;
//         var adjustedHeight = height;
//         // extract date
//         var dateTaken = imgData.DateTime;
//         document.getElementById("photo-date-taken-display").innerHTML = dateTaken;
//         document.getElementById("photo-date-taken").value = dateTaken;
//     });
// }


// function convertDMSToDD(degrees, minutes, seconds, direction) { 
//     var dd = degrees + (minutes/60) + (seconds/3600);
//     if (direction == "S" || direction == "W") {
//         dd = dd * -1; 
//     }
//     return dd;
// }
