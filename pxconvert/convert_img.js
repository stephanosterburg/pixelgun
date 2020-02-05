function convert_img(inFile, outFile)
{
     // Define Camera RAW open options
     var openOptions = new CameraRAWOpenOptions();
     openOptions.colorSpace = ColorSpaceType.SRGB;
     openOptions.bitsPerChannel = BitsPerChannelType.SIXTEEN;

     // Define TIFF save options
     var tiffSaveOptions = new TiffSaveOptions();
     tiffSaveOptions.embedColorProfile = true;
     tiffSaveOptions.imageCompression = TIFFEncoding.TIFFLZW;

     var inFileStr = inFile;
     var infileRef = File(inFileStr);
     var outFileStr = outFile;
     var outfileRef = File(outFileStr);
     var doc = open(infileRef, openOptions);
     // Set color space
     doc.convertProfile('sRGB IEC61966-2.1', Intent.RELATIVECOLORIMETRIC, true, true);
     // Save TIFF
     doc.saveAs(outfileRef, tiffSaveOptions, true);
     // Close document
     doc.close(SaveOptions.DONOTSAVECHANGES);
 }

 convert_img(arguments[0], arguments[1]);
