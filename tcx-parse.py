#!/usr/bin/env python

## Dependancies
#Native
import os, logging, argparse
import xml.etree.ElementTree
from datetime import datetime, timedelta
import yaml
#Packages
import matplotlib.pyplot as plt
from PIL import Image
import numpy as np
from prettytable import PrettyTable
#Internal
import include.conversion as utm

###############################################################################
## Settings
###############################################################################
path = 'data'
linewidth = 1
namespace = {'schema': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'}

###############################################################################
## Library
###############################################################################
class ActivityType():
    def __init__(self, name, lookupName):
        self.name       = name
        self.lookupName = lookupName

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


###############################################################################
## Core
###############################################################################
def main():
    try:
        #########################
        ## Parse arguments
        #########################
        parser = argparse.ArgumentParser()
        parser.add_argument('-a'      '--max-activities',      type=int,   dest='max_activities',          default=0,    help='[int]  Maximum number of activities to load.')
        commands = parser.parse_args()

        #########################
        ## Config
        #########################
        try:
            with open('tcx_parse.yml', 'r') as stream:
                config = yaml.load(stream)
        except yaml.YAMLError as exc:
            with open('tcx_parse.yml', 'r') as stream:
                config = {'regions':
                            {'Global':
                                {'lat1': -180.0,
                                 'lat2':  180.0,
                                 'long1':-180.0,
                                 'long2': 180.0,
                                 'plot':  False
                                }
                            },
                          'activityTypes': ['running', 'cycling', 'cross country skiing', 'ice skating']
                         }
                yaml.dump(config, stream, default_flow_style=False, allow_unicode=True)

        regions = {label: Region('label', latLim=[config['regions'][label]['lat1'], config['regions'][label]['lat2']], longLim=[config['regions'][label]['long1'], config['regions'][label]['long2']], plot=config['regions'][label]['plot']) for label in config['regions']}
        activityTypes = {label: ActivityType(label) for label in config['activityTypes']}


        #########################
        ## Load activities
        #########################
        ## Startup code, predetermine calculation time
        print('Parsing activities....')
        if(commands.max_activities): count = commands.max_activities
        else:
            count = 0
            for root, dirs, files in os.walk(path):
                for filename in files:
                    if(os.path.splitext(filename)[1].lower() == '.tcx'): count+=1
            if(count < 1):        print('    No activities found.')
            elif(count < 100):    print('    '+str(count)+' activities found. parsing may take several seconds...')
            elif(count < 1000):   print('    '+str(count)+' activities found. parsing may take several minutes...')
            elif(count < 10000):  print('    '+str(count)+' activities found. parsing may take up to an hour...')
            elif(count < 100000): print('    '+str(count)+' activities found. parsing may take several hours...')

        ## Load activities into memory
        activities = []
        for root, dirs, files in os.walk(path):
            for filename in files:
                if(len(activities) > count): break
                if(os.path.splitext(filename)[1].lower() == '.tcx'): activities.append(Activity(os.path.join(path,filename)))


        #########################
        ## Activities by time.
        #########################
        monthly_statistics = {}
        for activity in activities:
            if(activity.getStartTime().year not in monthly_statistics):  monthly_statistics[activity.getStartTime().year] = [0 for x in range(12)]
            monthly_statistics[activity.getStartTime().year][activity.getStartTime().month-1] += 1

        if(datetime.now().year in monthly_statistics):
            t = PrettyTable([datetime(2000,x,1).strftime("%B") for x in range(1,13)])
            t.add_row([str(x) for x in monthly_statistics[datetime.now().year]])
            print('  Activities this year:')
            print(t)

        t = PrettyTable([datetime(2000,x,1).strftime("%B") for x in range(1,13)])
        t.add_row([str(sum([monthly_statistics[year][month] for year in monthly_statistics])) for month in range(12)])
        print('  Activities all time:')
        print(t)

        fig = plt.figure('Activities by month')
        plt.bar([x-0.5 for x in range(12)], [sum([monthly_statistics[year][month] for year in monthly_statistics]) for month in range(12)], width=1)
        ax = plt.gca()
        ax.set_xticks(range(12))
        ax.set_xticklabels([datetime(2000,x,1).strftime("%B") for x in range(1,13)])
        plt.show()

        #########################
        ## Activities by region
        #########################
        ## Prepare and dump region statistics
        print('===============')
        for region_name in regions:
            regions[region_name].bindActivities(activities)

            print('Printing stats for region: '+regions[region_name].name)
            print('    Number:     '+str(len(regions[region_name].activities)))
            print('    Distance:   '+str(round(sum([activity.getDistance() for activity in regions[region_name].activities])/1000.0,1))+' km')
            try:    print('    Avg. speed:  '+str(round(sum([activity.getDistance() for activity in regions[region_name].activities])/sum([activity.getDuration().seconds for activity in regions[region_name].activities])*3.6, 1))+' km/h')
            except: print('    Avg. speed:  - km/h')
            print('    Calories:   '+str(sum([activity.getCalories() for activity in regions[region_name].activities])))
            print('    Total time: '+str(round(sum([activity.getDuration().seconds for activity in regions[region_name].activities])/3600.0, 2))+' h')
            try:    print('    Avg. time:  '+str(round(sum([activity.getDuration().seconds for activity in regions[region_name].activities])/60.0/float(len(regions[region_name].activities)), 1))+' min')
            except: print('    Avg. time:  - min')

            if(regions[region_name].plot):
                print('    Preparing map for region: '+regions[region_name].name)
                fig = plt.figure(regions[region_name].name)
                #for mapName in bitmapMaps:
                #    if(bitmapMaps[mapName].region == region_name): bitmapMaps[mapName].plot()

                for activity in regions[region_name].activities:
                    plt.plot(activity.getPositionsUTMX(), activity.getPositionsUTMY(), 'b', linewidth=linewidth)
                plt.axis('equal')
                plt.show()

            print('---------------')

        ## Prepare and dump activity statistics
        print('===============')
        for activity_name in activityTypes:
            activityTypes[activity_name].bindActivities(activities)

            print('Printing stats for activity: '+activityTypes[activity_name].name)
            print('    Number:     '+str(len(activityTypes[activity_name].activities)))
            print('    Distance:   '+str(round(sum([activity.getDistance() for activity in activityTypes[activity_name].activities])/1000.0,1))+' km')
            try:    print('    Avg. speed:  '+str(round(sum([activity.getDistance() for activity in activityTypes[activity_name].activities])/sum([activity.getDuration().seconds for activity in activityTypes[activity_name].activities])*3.6, 1))+' km/h')
            except: print('    Avg. speed:  - km/h')
            print('    Calories:   '+str(sum([activity.getCalories() for activity in activityTypes[activity_name].activities])))
            print('    Total time: '+str(round(sum([activity.getDuration().seconds for activity in activityTypes[activity_name].activities])/3600.0, 2))+' h')
            try:    print('    Avg. time:  '+str(round(sum([activity.getDuration().seconds for activity in activityTypes[activity_name].activities])/60.0/float(len(activityTypes[activity_name].activities)), 1))+' min')
            except: print('    Avg. time:  - min')
            print('---------------')

        ##import pdb; pdb.set_trace()

    ###################
    # Error and exit handling
    ###################
    ## User interruption
    except KeyboardInterrupt: print('==User exited== [0000]')
    ## Normal program exit
    except SystemExit, e: print('==Execution finished== [0001]')
    ## Raised error handling or uncaught exception handling with PDB traceback
    except Exception, e:
        try:
            if(isinstance(e, Exception) and str(e) and isinstance(e[0], list)): print('==Runtime error== ['+str(e[0][0]).zfill(4)+'] '+e[0][1])
            else:
                import sys
                from pdb       import post_mortem as pdb_post_mortem
                from traceback import print_exc   as traceback_print_exc
                _, _, tb = sys.exc_info()
                traceback_print_exc()
                pdb_post_mortem(tb)
                logging.exception(e)
        except UnboundLocalError: pass
###################
# Launch main
###################
if __name__ == '__main__':
    main()
