'''

This Google Earth Engine Script computes a Linear Regression analysis 
for estimating trends in NDVI time series based on Landsat 5 and 8 Time Series.
User inputs are: AOI and Time Series start/end dates.
Note that: Landsat-5 imagery is available from March 1984 to May 2012.
           Landsat-8 imagery is available from April 2013 to Present.
           
Author: Moez Labiadh
Last updated on May 05, 2020.

'''

import ee
from ee_plugin import Map  #remove this if you're running the script outside of GEE QGIS plugin.

#initialize EE
try:
  ee.Initialize()
  print('The Earth Engine package initialized successfully!')
except ee.EEException as e:
  print('The Earth Engine package failed to initialize! Try to Authenticate EE')
except:
    print("Unexpected error:", sys.exc_info()[0])
    raise

# Define the Area of Interest
AOI = ee.FeatureCollection("users/labiadhmoez/PerryRidge")
#AOI = ee.Geometry.Polygon([[[-117.73, 49.73],[-117.73, 49.54], [-117.50, 49.54],[-117.50, 49.73]]])

# Define the before (refrence period) and after (current years) dates
L5_start_date = '1990-01-01'
L5_end_date = '2011-12-31'

L8_start_date = '2013-01-01'
L8_end_date = '2019-12-31'

# Define a cloud threshold
cloud_threshold = 30

# Define a cloud mask function for Landsat-8 collection
def MaskL8sr(image):
    cloudShadowBitMask = (1 << 3)
    cloudsBitMask = (1 << 5)
    qa = image.select('pixel_qa')
    mask = qa.bitwiseAnd(cloudShadowBitMask)\
           and(qa.bitwiseAnd(cloudsBitMask))
    return image.updateMask(mask.Not())

# Define a cloud mask function for Landsat-5 collection
def MaskL5sr (image):
    qa = image.select('pixel_qa')
    cloud = qa.bitwiseAnd(1 << 5) and(qa.bitwiseAnd(1 << 7))\
                                   or(qa.bitwiseAnd(1 << 3))
    maskEdge = image.mask().reduce(ee.Reducer.min())
    return image.updateMask(cloud.Not()).updateMask(maskEdge)
    
# Define NDVI indice function for Landsat-5 collection 
def L5_NDVI (image):
    ndvi = image.normalizedDifference(['B4', 'B3']).rename('NDVI')
    return image.addBands(ndvi)
    
# Define NDVI indice function for Landsat-8 collection 
def L8_NDVI(image):
    ndvi = image.normalizedDifference(['B5', 'B4']).rename('NDVI')
    return image.addBands(ndvi)
    
# Add Landsat-5 collection. Filter by date and AOI. Apply Cloud Mask and NDVI function        
bef_L5 = ee.ImageCollection('LANDSAT/LT05/C01/T1_SR')\
           .filterDate(L5_start_date, L5_end_date)\
           .filter(ee.Filter.calendarRange(7,8,'month'))\
           .filter(ee.Filter.lt('CLOUD_COVER', cloud_threshold))\
           .filterBounds(AOI)\
           .map(MaskL5sr)\
           .map(L5_NDVI)
    
# Add Landsat-8 collection. Filter by date and AOI. Apply Cloud Mask and NDVI function                       
aft_L8 = ee.ImageCollection("LANDSAT/LC08/C01/T1_SR")\
           .filterDate(L8_start_date, L8_end_date)\
           .filter(ee.Filter.calendarRange(7,8,'month'))\
           .filter(ee.Filter.lt('CLOUD_COVER', cloud_threshold))\
           .filterBounds(AOI)\
           .map(MaskL8sr)\
           .map(L8_NDVI)

# Create a Time band 
def createTimeBand (image):
    #Scale milliseconds by a large constant to avoid very small slopes in the linear regression output.
    return image.addBands(image.metadata('system:time_start').divide(1e18))

#Merge L5 and L8 collections into a single Time Series.
Collection = bef_L5.merge(aft_L8)\
                   .map(createTimeBand)\
                   .sort('system:time_start')

count_images = Collection.size().getInfo()
print("Your LANDSAT-8 query returned", count_images, "images")

#Reduce the collection with the linear fit reducer.
#Independent variable are followed by dependent variables.
linearFit = Collection.select(['system:time_start', 'NDVI'])\
                      .reduce(ee.Reducer.linearFit())\
                      .clip(AOI);
  
image_bands = linearFit.bandNames().getInfo()
print ("This image has the following bands:",image_bands)

#Export the output to Google Grive.
params = {
    'description': 'ndvitrend_slope_1990-2019',
    'scale': 30,
    'region': AOI.geometry().getInfo()['coordinates'] #get list of coordinates from AOI
  }

task = ee.batch.Export.image.toDrive(linearFit.select('scale'), **params)
task.start()

print ("Check your Google Drive for output. Upload might take a while")

print ("Processing Completed!")
