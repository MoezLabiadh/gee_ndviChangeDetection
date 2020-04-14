import ee
from ee_plugin import Map  #remove this if you are running the script outside of GEE QGIS plugin.
ee.Initialize()

# Define the Area of Interest
AOI = ee.FeatureCollection("users/labiadhmoez/PerryRidge")

# Define the before (refrence period) and after (current years) dates
bef_start_date = '1990-01-01'
bef_end_date = '2000-12-31'

aft_start_date = '2018-01-01'
aft_end_date = '2019-12-31'

# Define a cloud threshold
cloud_threshold = 30

# Define a cloud mask function for Landsat-5 collection
def cloudMaskL5 (image):
    qa = image.select('pixel_qa')
    cloud = qa.bitwiseAnd(1 << 5) and(qa.bitwiseAnd(1 << 7)) or(qa.bitwiseAnd(1 << 3))
    maskEdge = image.mask().reduce(ee.Reducer.min())
    return image.updateMask(cloud.Not()).updateMask(maskEdge)
    
# Define a cloud mask function for Landsat-8 collection
def maskL8sr(image):
    cloudShadowBitMask = (1 << 3)
    cloudsBitMask = (1 << 5)
    qa = image.select('pixel_qa')
    mask = qa.bitwiseAnd(cloudShadowBitMask).eq(0)\
           and(qa.bitwiseAnd(cloudsBitMask).eq(0))
    return image.updateMask(mask)
    
# Define NDVI indice function for Landsat-5 collection 
def L5_NDVI (image):
    l5_ndvi = image.normalizedDifference(['B4', 'B3']).rename('L5_NDVI')
    return image.addBands(l5_ndvi)
    
# Define NDVI indice function for Landsat-8 collection 
def L8_NDVI(image):
    l8_ndvi = image.normalizedDifference(['B5', 'B4']).rename('L8_NDVI')
    return image.addBands(l8_ndvi)
    
# Add Landsat-5 collection. Filter by date and AOI. Apply Cloud Mask and NDVI function        
bef_L5 = ee.ImageCollection('LANDSAT/LT05/C01/T1_SR')\
           .filterDate(bef_start_date, bef_end_date)\
           .filter(ee.Filter.calendarRange(7,8,'month'))\
           .filter(ee.Filter.lt('CLOUD_COVER', cloud_threshold))\
           .filterBounds(AOI)\
           .map(cloudMaskL5)\
           .map(L5_NDVI)
    
# Add Landsat-8 collection. Filter by date and AOI. Apply Cloud Mask and NDVI function                       
aft_L8 = ee.ImageCollection("LANDSAT/LC08/C01/T1_SR")\
           .filterDate(aft_start_date, aft_end_date)\
           .filter(ee.Filter.calendarRange(7,8,'month'))\
           .filter(ee.Filter.lt('CLOUD_COVER', cloud_threshold))\
           .filterBounds(AOI)\
           .map(maskL8sr)\
           .map(L8_NDVI) 

# Compute statisctis (mean, StDev) and NDVI change/anomalie 
bef_mean_NDVI = bef_L5.select ('L5_NDVI').mean()
aft_mean_NDVI = aft_L8.select ('L8_NDVI').mean() 
bef_stDev_NDVI = bef_L5.select ('L5_NDVI').reduce (ee.Reducer.stdDev())

ndviChange = ((aft_mean_NDVI.subtract(bef_mean_NDVI))\
                  .divide(bef_mean_NDVI))\
                  .multiply(100)\
                  .rename('ndviChange')\
                  .clip(AOI);

                                
ndviAnomaly = ((aft_mean_NDVI.subtract(bef_mean_NDVI))\
                 .divide(bef_stDev_NDVI))\
                 .rename ('Zscore')\
                 .clip(AOI)

# Set visualisation parameters
NdviChangeVizParam = {
  "min": -50,
  "max": 20,
  "palette": ['purple','red','orange','yellow','green']}
    
NdviAnomalyVizParam = {
  "min": -3,
  "max": 2,
  "palette": ['purple','red','orange','yellow','green']}
    
# Add layers to the map
Map.centerObject(AOI, 12)

Map.addLayer(ndviChange.clip(AOI), NdviChangeVizParam, 'ndviChange')
Map.addLayer(ndviAnomaly.clip(AOI), NdviAnomalyVizParam, 'ndviZscore')

#Download the outputs
  ## OPTION 1: Download to Google Drive
params = {
    'description': 'ndviZscore_1990-2000_2018-2019_07-08',
    'scale': 30,
    'region': AOI.geometry().getInfo()['coordinates'] #get list of coordinates from AOI
  }
  
task = ee.batch.Export.image.toDrive(ndviAnomaly, **params)
task.start()
print ("Check your Google Drive for output. Upload might take a while")

  ## OPTION 2: Download to Local Drive. This will generate a Download Link
def downloader(ee_object,region):
    try:
        #download image
        if isinstance(ee_object, ee.image.Image):
            print('This is an Image')
            url = ee_object.getDownloadUrl({
                    'scale': 30,
                    'region': region
                })
            return url
        
        #download imagecollection
        elif isinstance(ee_object, ee.imagecollection.ImageCollection):
            print('This is an ImageCollection')
            ee_object_new = ee_object.mosaic()
            url = ee_object_new.getDownloadUrl({
                    'scale': 30,
                    'region': region
                })
            return url
    except:
        print("Could not download")

geometry = AOI.geometry().getInfo()['coordinates'] #get list of coordinates from AOI
polygon = ee.Geometry.Polygon (geometry) #convert list of coordinates into Polygon Geometry
region = polygon.toGeoJSONString()#region must in JSON format

path = downloader(ndviChange,region)#call function
print(path)#print the download URL


print ("Done")
