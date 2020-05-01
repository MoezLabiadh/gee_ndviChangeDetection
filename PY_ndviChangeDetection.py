'''

This Google Earth Engine Script computes NDVI change/anomalies based on Landsat 5 and 8 Time Series.
User inputs are: AOI and Time Series start/end dates.
Note that: Landsat-5 imagery is available from March 1984 to May 2012.
           Landsat-8 imagery is available from April 2013 to Present.
           
Author: Moez Labiadh
Last updated on May, 1, 2020.

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
bef_start_date = '1990-01-01'
bef_end_date = '2000-12-31'

aft_start_date = '2018-01-01'
aft_end_date = '2019-12-31'

# Define a cloud threshold
cloud_threshold = 30

# Define a cloud mask function for Landsat-5 collection
def MaskL5sr (image):
    qa = image.select('pixel_qa')
    cloud = qa.bitwiseAnd(1 << 5) and(qa.bitwiseAnd(1 << 7))\
                                   or(qa.bitwiseAnd(1 << 3))
    maskEdge = image.mask().reduce(ee.Reducer.min())
    return image.updateMask(cloud.Not()).updateMask(maskEdge)
    
# Define a cloud mask function for Landsat-8 collection
def MaskL8sr(image):
    cloudShadowBitMask = (1 << 3) # Create the Binary Cloud Shadow Mask by Left shifting value 1 to postion 3 and set all other Bits to 0.
    cloudsBitMask = (1 << 5) # Create the Binary Cloud Mask by Left shifting value 1 to postion 3 and set all other Bits to 0.
    qa = image.select('pixel_qa')
    mask = qa.bitwiseAnd(cloudShadowBitMask).eq(0)\
           and(qa.bitwiseAnd(cloudsBitMask).eq(0)) # Use the Bitwise AND operator to apply the Mask to the pixel_qa band
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
           .map(MaskL5sr)\
           .map(L5_NDVI)
    
# Add Landsat-8 collection. Filter by date and AOI. Apply Cloud Mask and NDVI function                       
aft_L8 = ee.ImageCollection("LANDSAT/LC08/C01/T1_SR")\
           .filterDate(aft_start_date, aft_end_date)\
           .filter(ee.Filter.calendarRange(7,8,'month'))\
           .filter(ee.Filter.lt('CLOUD_COVER', cloud_threshold))\
           .filterBounds(AOI)\
           .map(MaskL8sr)\
           .map(L8_NDVI)

#Get information on the returned images: Nbr of images returned per Collection, acquisition date, bands....
count_images_L8 = aft_L8.size()
count_images_L5 = bef_L5.size()
print("Your LANDSAT-8 query returned", count_images_L8.getInfo(), "images")
print("Your LANDSAT-5 query returned", count_images_L5.getInfo(), "images")

image = aft_L8.first()
image_date = image.date().format('YYYY-MM-dd').getInfo()
image_bands = image.bandNames().getInfo()
print ("This image was acquired on", image_date, "and has the following bands:",image_bands)

#Show a random Landsat-8 image from the collection
Map.centerObject(AOI, 8)
Map.addLayer (image.visualize(bands = ['B4', 'B3', 'B2'], min= 0, max= 3000, gamma= 1.4))

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
                 .rename ('ndviZscore')\
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

'''
  ## OPTION 1: Download to Google Drive
params = {
    'description': 'ndviZscore_1990-2000_2018-2019_07-08',
    'scale': 30,
    'region': AOI.geometry().getInfo()['coordinates'] #get list of coordinates from AOI
  }

task = ee.batch.Export.image.toDrive(ndviAnomaly, **params)
task.start()

print ("Check your Google Drive for output. Upload might take a while")
 ''' 
 
  ## OPTION 2: Download to Local Drive. This will generate a Download Link
def downloader(ee_object,region):
    try:
        #download image
        if isinstance(ee_object, ee.image.Image):
            print('Generating Download URL for Image')
            url = ee_object.getDownloadUrl({
                    'scale': 30,
                    'region': region
                })
            return url        
        #download imagecollection
        elif isinstance(ee_object, ee.imagecollection.ImageCollection):
            print('Generating Download URL for ImageCollection')
            ee_object_new = ee_object.mosaic()
            url = ee_object_new.getDownloadUrl({
                    'scale': 30,
                    'region': region
                })
            return url
    except:
        print("Download URL could not be generated")

polygon = ee.Geometry.Polygon (AOI.geometry().getInfo()['coordinates']) # Convert the AOI to a Geometry.Polygon.
region = polygon.toGeoJSONString()#region must be in JSON format

path = downloader(ndviChange,region)#call function
print(path)#print the download URL

print ("Processing Completed!")
