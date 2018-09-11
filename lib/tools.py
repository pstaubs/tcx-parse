#!/usr/bin/env python

## Dependancies
#Native
import xml.etree.ElementTree
from datetime import datetime, timedelta
#Packages
import utm
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image


namespace = {'schema': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'}

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



class Activity():
    def __init__(self, filename):
        self.filename = filename
        self.importXML()

    def getName(self):          return self.filename
    def getActivity(self):      return self.data.find('schema:Activities', namespace).find('schema:Activity', namespace)
    def getActivityType(self):  return self.getActivity().attrib['Sport']
    def getCalories(self):      return int(self.getActivity().find('schema:Lap', namespace).find('schema:Calories', namespace).text)
    def getStartTime(self):     return datetime.strptime(self.getActivity().find('schema:Lap', namespace).attrib['StartTime'], '%Y-%m-%dT%H:%M:%S.000Z')
    def getDuration(self):      return timedelta(seconds=int(self.getActivity().find('schema:Lap', namespace).find('schema:TotalTimeSeconds', namespace).text))
    def getEndTime(self):       return self.getStartTime() + self.getDuration()
    def getDistance(self):      return int(self.getActivity().find('schema:Lap', namespace).find('schema:DistanceMeters', namespace).text) # In metres

    def getPositions(self):     return self.getActivity().find('schema:Lap', namespace).find('schema:Track', namespace).findall('schema:Trackpoint', namespace)
    def getPositionsLat(self):  return [float(pos.find('schema:Position', namespace).find('schema:LatitudeDegrees', namespace).text) for pos in self.getPositions()]
    def getPositionsLong(self): return [float(pos.find('schema:Position', namespace).find('schema:LongitudeDegrees', namespace).text) for pos in self.getPositions()]
    def getPositionsAlt(self):  return [float(pos.find('schema:AltitudeMeters', namespace).text) for pos in self.getPositions()]
    def getPositionsUTMX(self): return [utm.from_latlon(lat,long)[0] for lat,long in zip(self.getPositionsLat(),self.getPositionsLong())]
    def getPositionsUTMY(self): return [utm.from_latlon(lat,long)[1] for lat,long in zip(self.getPositionsLat(),self.getPositionsLong())]

    def importXML(self):
        self.data = xml.etree.ElementTree.parse(self.filename).getroot()

class Persistant():
    data = []

def closestPoint(point, points):
    deltas = points - point
    dist_2 = np.einsum('ij,ij->i', deltas, deltas)
    return min(dist_2)

def findNearestActivity(x,y, activities):
    dists = [closestPoint((x,y),np.asarray([activity.getPositionsUTMX(),activity.getPositionsUTMY()]).transpose()) for activity in activities]
    return dists.index(min(dists))


def mapClickCallback(event, fig, activities, activeElements, linewidth):
    if(fig.canvas.manager.toolbar._active is not None): return False
    if(event.button != 1): return False
    try:
        for activeElement in activeElements.data: activeElement.remove()
        activeElements.data = []
    except: pass
    for activity in activities: activity.plot.set_color('C0')
    aIx = findNearestActivity(event.xdata, event.ydata, activities)
    activities[aIx].plot.set_color('#eb3c15')
    activeElements.data.append(plt.text(activities[aIx].getPositionsUTMX()[0], activities[aIx].getPositionsUTMY()[0], activities[aIx].getName(), fontsize=12))
    fig.canvas.draw()
    return True
