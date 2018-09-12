#!/usr/bin/env python

## Dependancies
#Native
import os, math
from xml.dom import minidom
from datetime import datetime, timedelta
#Packages
import utm
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image


###############################################################################
## Library
###############################################################################
class ActivityType():
    def __init__(self, name):
        self.name       = name

    def bindActivities(self, listOfActivities):
        indeces = []
        for i in range(len(listOfActivities)):
            if(listOfActivities[i].getActivityType() == self.lookupName and len(listOfActivities[i].getPositionsLat()) > 0):
                indeces.append(i)

        self.activities = [listOfActivities[ix] for ix in indeces]
        return True

class Region():
    def __init__(self, name, latLim, longLim, plot=False):
        self.name    = name
        self.latLim  = latLim
        self.longLim = longLim
        self.plot    = plot

    def bindActivities(self, listOfActivities):
        indeces = []
        for i in range(len(listOfActivities)):
            lat_ = listOfActivities[i].getPositionsLat()
            long_ = listOfActivities[i].getPositionsLong()
            if(len(lat_) > 0 and lat_[0] > self.latLim[0] and lat_[0] < self.latLim[1] and long_[0] > self.longLim[0] and long_[0] < self.longLim[1]):
                indeces.append(i)

        self.activities = [listOfActivities[ix] for ix in indeces]
        return True

class Map():
    def __init__(self, filename, originLat, originLong, scale, region):
        self.filename   = filename
        self.originLat  = originLat
        self.originLong = originLong
        self.scale      = scale          ## px/m
        self.region     = region
        self.load()

    def load(self):
        self.img = Image.open(self.filename)
        self.img = self.img.resize((int(self.img.size[0]/self.scale),int(self.img.size[1]/self.scale)), Image.ANTIALIAS)

    def plot(self):
        x,y,_,_ = utm.from_latlon(self.originLat,self.originLong)
        plt.imshow(self.img, extent=[x,x+self.img.size[0],y,y+self.img.size[1]], interpolation='bicubic')


class Activity:
    def __init__(self, filename):
        self.filename = filename
        self.importXML()

    def __len__(self):          return self.length
    def getName(self):          return self.filename
    def getActivityType(self):  return self.activityType
    def getCalories(self):      return self.calories
    def getStartTime(self):     return self.startTime
    def getDuration(self):      return self.duration
    def getEndTime(self):       return self.getStartTime() + self.getDuration()
    def getDistance(self):      return self.distance

    def getPositionsLat(self):  return self.positionsLatLong[:,0]
    def getPositionsLong(self): return self.positionsLatLong[:,1]
    def getPositionsUTMX(self): return self.positions[:,0]
    def getPositionsUTMY(self): return self.positions[:,1]
    def getPositions(self):     return self.positions
    def getPositionsAlt(self):  return self.altitude


class ActivityTCX(Activity):

    def importXML(self):
        data      = minidom.parse(self.filename)
        activity  = data.getElementsByTagName('Activity')[0]
        lap       = activity.getElementsByTagName('Lap')[0]
        positions = lap.getElementsByTagName('Trackpoint')
        self.activityType     = activity.attributes['Sport'].value
        self.calories         = int(lap.getElementsByTagName('Calories')[0].childNodes[0].nodeValue)
        self.startTime        = datetime.strptime(lap.attributes['StartTime'].value, '%Y-%m-%dT%H:%M:%S.000Z')
        self.duration         = timedelta(seconds=int(lap.getElementsByTagName('TotalTimeSeconds')[0].childNodes[0].nodeValue))
        self.distance         = int(lap.getElementsByTagName('DistanceMeters')[0].childNodes[0].nodeValue) # In metres
        self.positionsLatLong = np.array([[float(pos.getElementsByTagName('LatitudeDegrees')[0].childNodes[0].nodeValue) for pos in positions],
                                          [float(pos.getElementsByTagName('LongitudeDegrees')[0].childNodes[0].nodeValue) for pos in positions]]).transpose()
        try:
            self.UTMZone      = utm.from_latlon(self.positionsLatLong[0][0],self.positionsLatLong[0][1])[2:]
            self.positions    = np.array([utm.from_latlon(pll[0],pll[1])[:2] for pll in self.positionsLatLong])
            self.length           = len(self.positions[:,0])
            self.altitude     = [float(pos.getElementsByTagName('AltitudeMeters')[0].childNodes[0].nodeValue) for pos in positions]
        except:
            self.UTMZone      = (None, None)
            self.positions    = np.array([[],[]])
            self.length       = 0
            self.altitude     = []
            print('Warning: Empty positions in '+self.filename)



class ActivityGPX(Activity):
    def importXML(self, activities=[]):
        data      = minidom.parse(self.filename)
        positions = data.getElementsByTagName('trkpt')
        ## Attempt to find activity name in filename
        self.activityType     = 'running'
        for activity in activities:
            if(activity.lower() in os.path.basename(self.filename.lower())): self.activityType = activity
        self.calories         = 0
        self.startTime        = datetime.strptime(positions[0].getElementsByTagName('time')[0].childNodes[0].nodeValue, '%Y-%m-%dT%H:%M:%SZ')
        self.duration         = self.startTime-datetime.strptime(positions[-1].getElementsByTagName('time')[0].childNodes[0].nodeValue, '%Y-%m-%dT%H:%M:%SZ')
        self.positionsLatLong = np.array([[float(pos.attributes['lat'].value) for pos in positions],
                                          [float(pos.attributes['lon'].value) for pos in positions]]).transpose()
        self.UTMZone          = utm.from_latlon(self.positionsLatLong[0][0],self.positionsLatLong[0][1])[2:]
        self.positions        = np.array([utm.from_latlon(pll[0],pll[1])[:2] for pll in self.positionsLatLong])
        self.length           = len(self.positions[:,0])
        self.altitude         = [float(pos.getElementsByTagName('ele')[0].childNodes[0].nodeValue) for pos in positions]
        self.distance         = getCumulativeLength(self.positions)

class Persistant():
    data = []


def getCumulativeLength(positions):
    length = 0
    for pIx in range(len(positions)-1):
        length += math.sqrt((positions[pIx+1][0]-positions[pIx][0])**2+(positions[pIx+1][1]-positions[pIx][1])**2)
    return length


def closestPoint(point, points):
    deltas = points - point
    dist_2 = np.einsum('ij,ij->i', deltas, deltas)
    return min(dist_2)

def findNearestActivity(x,y, activities):
    dists = [closestPoint((x,y), activity.getPositions()) for activity in activities]
    return dists.index(min(dists))


def mapClickCallback(event, fig, activities, activeElements, linewidth):
    ''' Fire when user click on map. '''
    ## Interactivity conditions
    if(fig.canvas.manager.toolbar._active is not None): return False
    if(event.button != 1): return False
    ## Flush previous interactive elements
    try:
        for activeElement in activeElements.data: activeElement.remove()
        activeElements.data = []
    except: pass
    ## Find closest trajectory (expensive)
    aIx = findNearestActivity(event.xdata, event.ydata, activities)
    ## Highlight closest trajectory
    activity_plot, = plt.plot(activities[aIx].getPositionsUTMX(), activities[aIx].getPositionsUTMY(), color='#eb3c15', zorder=100)
    activeElements.data.append(activity_plot)
    activeElements.data.append(plt.text(activities[aIx].getPositionsUTMX()[0], activities[aIx].getPositionsUTMY()[0], activities[aIx].getName(), fontsize=12))
    fig.canvas.draw()
    return True

def mapZoom(event, fig, base_scale=2.):
    ''' https://stackoverflow.com/questions/11551049/matplotlib-plot-zooming-with-scroll-wheel. '''
    ax = plt.gca()
    # get the current x and y limits
    cur_xlim = ax.get_xlim()
    cur_ylim = ax.get_ylim()
    cur_xrange = (cur_xlim[1] - cur_xlim[0])*.5
    cur_yrange = (cur_ylim[1] - cur_ylim[0])*.5
    xdata = event.xdata # get event x location
    ydata = event.ydata # get event y location
    if event.button == 'up':
        # deal with zoom in
        scale_factor = 1/base_scale
    elif event.button == 'down':
        # deal with zoom out
        scale_factor = base_scale
    else:
        # deal with something that should never happen
        scale_factor = 1
        print event.button
    # set new limits
    ax.set_xlim([xdata - cur_xrange*scale_factor,
                 xdata + cur_xrange*scale_factor])
    ax.set_ylim([ydata - cur_yrange*scale_factor,
                 ydata + cur_yrange*scale_factor])
    fig.canvas.draw()
