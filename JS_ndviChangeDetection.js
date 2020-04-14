//Define the Area of Interest
var AOI = ee.FeatureCollection("users/labiadhmoez/PerryRidge");

//Define the before (refrence period) and after (current years) dates
var bef_start_date = '1990-01-01';
var bef_end_date = '2000-12-31';

var aft_start_date = '2018-01-01';
var aft_end_date = '2019-12-31';

// Define a cloud threshold
var cloud_threshold = 30;

// Define a cloud mask function for Landsat-5 collection
function cloudMaskL5 (image) {
  var qa = image.select('pixel_qa');
  var cloud = qa.bitwiseAnd(1 << 5)
                  .and(qa.bitwiseAnd(1 << 7))
                  .or(qa.bitwiseAnd(1 << 3));
  var maskEdge = image.mask().reduce(ee.Reducer.min());
  return image.updateMask(cloud.not()).updateMask(maskEdge);
}

// Define a cloud mask function for Landsat-8 collection
function maskL8sr(image) {
  var cloudShadowBitMask = (1 << 3);
  var cloudsBitMask = (1 << 5);
  var qa = image.select('pixel_qa');
  var mask = qa.bitwiseAnd(cloudShadowBitMask).eq(0)
                 .and(qa.bitwiseAnd(cloudsBitMask).eq(0));
  return image.updateMask(mask);
}

// Define a function to caclulate NDVI for Landsat-5 collection 
function L5_ndvi (image) {
    var l5_ndvi = image.normalizedDifference(['B4', 'B3']).rename('L5_NDVI');
    return image.addBands(l5_ndvi);
        }

// Define a function to caclulate NDVI for Landsat-8 collection 
function L8_ndvi(image) {
    var l8_ndvi = image.normalizedDifference(['B5', 'B4']).rename('L8_NDVI');
    return image.addBands(l8_ndvi);
        }        

// Add Landsat-5 collection. Filter by date and AOI. Apply Cloud Mask and NDVI functions.        
var bef_L5 = ee.ImageCollection('LANDSAT/LT05/C01/T1_SR')
                 .filterDate(bef_start_date, bef_end_date)
                 .filter(ee.Filter.calendarRange(7,8,'month'))
                 .filter(ee.Filter.lt('CLOUD_COVER', cloud_threshold))
                 .filterBounds(AOI)
                 .map(cloudMaskL5)
                 .map(L5_ndvi);
                 
// Add Landsat-8 collection. Filter by date and AOI. Apply Cloud Mask and NDVI functions.                       
var aft_L8 = ee.ImageCollection("LANDSAT/LC08/C01/T1_SR")
                 .filterDate(aft_start_date, aft_end_date)
                 .filter(ee.Filter.calendarRange(7,8,'month'))
                 .filter(ee.Filter.lt('CLOUD_COVER', cloud_threshold))
                 .filterBounds(AOI)
                 .map(maskL8sr)
                 .map(L8_ndvi);
print (bef_L5);
print (aft_L8);

// Compute statisctis (mean, StDev) and NDVI change/anomalie 
var bef_mean_NDVI = bef_L5.select ('L5_NDVI').mean();
var aft_mean_NDVI = aft_L8.select ('L8_NDVI').mean(); 
var bef_stDev_NDVI = bef_L5.select ('L5_NDVI').reduce (ee.Reducer.stdDev());

var ndviChange = ((aft_mean_NDVI.subtract(bef_mean_NDVI))
                                .divide(bef_mean_NDVI))
                                .multiply(100)
                                .rename('ndviChange')
                                .clip(AOI);

                                
var ndviAnomaly = ((aft_mean_NDVI.subtract(bef_mean_NDVI))
                                 .divide(bef_stDev_NDVI))
                                 .rename ('ndviZscore')
                                 .clip(AOI);

//Set visualisation parameters
var NdviChangeVizParam = {
  min: -50,
  max: 20,
  palette: ['purple','red','orange','yellow','green'],
};

var NdviAnomalyVizParam = {
  min: -3,
  max: 3,
  palette: ['purple','red','orange','yellow','green'],
};

//Add layers to the map
Map.centerObject(AOI, 12);
Map.addLayer(ndviAnomaly.clip(AOI), NdviAnomalyVizParam, 'ndviZscore');
Map.addLayer(ndviChange.clip(AOI), NdviChangeVizParam, 'ndviChange');


//Export outputs to GDrive.

Export.image.toDrive({
  image: ndviChange,
  description: 'NDVIchange_1990-2000_2018-2019_07-08',
  scale: 30,
  region: AOI
});

Export.image.toDrive({
  image: ndviAnomaly,
  description: 'ndviZscore_1990-2000_2018-2019_07-08',
  scale: 30,
  region: AOI
});

