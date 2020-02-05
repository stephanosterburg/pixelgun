function convert_imgs(sourceDir)
{
     // Options for opening a camera RAW document.
     var openOptions = new CameraRAWOpenOptions();
     openOptions.colorSpace = ColorSpaceType.SRGB;
     openOptions.bitsPerChannel = BitsPerChannelType.SIXTEEN;

     // Define TIFF save options
     var tiffSaveOptions = new TiffSaveOptions();
     tiffSaveOptions.embedColorProfile = true;
     tiffSaveOptions.imageCompression = TIFFEncoding.TIFFLZW;

     // Folder of all CR2 images
     var srcFolderStr = sourceDir;
     // Define TIFF sub-directory
     var tiffSubFolder = srcFolderStr + "/TIFF/";
     // Get a list of all images in a given folder
     var fileList = Folder(srcFolderStr).getFiles();

     for (var i = 1; i < fileList.length; i++) {
         var fileRef = File(fileList[i]);
         var doc = open(fileRef, openOptions);
         // decode a Uniform Resource Identifier (URI)
         var docName = decodeURI(doc.name);
         // Get base name
         var baseName = docName.split('/').pop().split('.')[0];
         // Define TIFF output
         var outFile = new File(tiffSubFolder + '/' + baseName + '.tif');
         // Set color space
         doc.convertProfile('sRGB IEC61966-2.1', Intent.RELATIVECOLORIMETRIC, true, true);
         // Save TIFF
         doc.saveAs(outFile, tiffSaveOptions, true);
         // Close document
         doc.close(SaveOptions.DONOTSAVECHANGES);
     }
 }

 convert_imgs(arguments[0]);
