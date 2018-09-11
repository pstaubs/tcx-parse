#!/usr/bin/env python

## Dependancies
#Native
import os, logging, argparse
from datetime import datetime
import yaml
#Packages
import matplotlib.pyplot as plt
from prettytable import PrettyTable
#Internal
import lib.tools

###############################################################################
## Settings
###############################################################################
path = 'data'
linewidth = 1
results_folder = 'output'

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
        except:
            with open('tcx_parse.yml', 'w') as stream:
                config = {'regions':
                            {'Global':
                                {'lat1': -180.0,
                                 'lat2':  180.0,
                                 'long1':-180.0,
                                 'long2': 180.0,
                                 'plot':  False
                                }
                            },
                          'activityTypes': ['running', 'cycling', 'cross country skiing', 'ice skating', 'paddle boating']
                         }
                yaml.dump(config, stream, default_flow_style=False, allow_unicode=True)

        regions = {label: lib.tools.Region(label, latLim=[config['regions'][label]['lat1'], config['regions'][label]['lat2']], longLim=[config['regions'][label]['long1'], config['regions'][label]['long2']], plot=config['regions'][label]['plot']) for label in config['regions']}
        activityTypes = {label: lib.tools.ActivityType(label) for label in config['activityTypes']}


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
            elif(count < 100):    print('    '+str(count)+' activities found. Parsing may take several seconds...')
            elif(count < 1000):   print('    '+str(count)+' activities found. Parsing may take several minutes...')
            elif(count < 10000):  print('    '+str(count)+' activities found. Parsing may take up to an hour...')
            elif(count < 100000): print('    '+str(count)+' activities found. Parsing may take several hours...')

        ## Load activities into memory
        activities = []
        for root, dirs, files in os.walk(path):
            for filename in files:
                if(len(activities) > count): break
                if(os.path.splitext(filename)[1].lower() == '.tcx'):
                    activity = lib.tools.Activity(os.path.join(path,filename))
                    if(activity.getActivityType().lower().replace('_',' ') not in config['activityTypes']): continue
                    activities.append(activity)


        #########################
        ## Activities by time.
        #########################
        monthly_statistics = {}
        for activity in activities:
            if(activity.getStartTime().year not in monthly_statistics):  monthly_statistics[activity.getStartTime().year] = [0 for x in range(12)]
            monthly_statistics[activity.getStartTime().year][activity.getStartTime().month-1] += 1

        if(datetime.now().year in monthly_statistics):
            t = PrettyTable()
            t.title = 'Activities this year'
            t.field_names = [datetime(2000,x,1).strftime("%B") for x in range(1,13)]
            t.add_row([str(x) for x in monthly_statistics[datetime.now().year]])
            print(t)

        t = PrettyTable()
        t.title = 'Activities all time'
        t.field_names = [datetime(2000,x,1).strftime("%B") for x in range(1,13)]
        t.add_row([str(sum([monthly_statistics[year][month] for year in monthly_statistics])) for month in range(12)])
        print(t)

        fig = plt.figure('Activities by month')
        plt.bar([x-0.5 for x in range(12)], [sum([monthly_statistics[year][month] for year in monthly_statistics]) for month in range(12)], width=1)
        ax = plt.gca()
        ax.set_xticks(range(12))
        ax.set_xticklabels([datetime(2000,x,1).strftime("%B") for x in range(1,13)])
        if(not os.path.exists(results_folder)): os.mkdir(results_folder)
        fig.savefig(os.path.join(results_folder,'monthly.png'))
        plt.close()

        #########################
        ## Activities by region
        #########################
        ## Prepare and dump region statistics
        for region_name in regions:
            regions[region_name].bindActivities(activities)

            t = PrettyTable()
            t.title = 'Stats for region: '+regions[region_name].name
            t.field_names = ['Stat','Value']
            t.add_row(['Number:',str(len(regions[region_name].activities))])
            t.add_row(['Distance:',str(round(sum([activity.getDistance() for activity in regions[region_name].activities])/1000.0,1))+' km'])
            try:    t.add_row(['Avg. speed:',str(round(sum([activity.getDistance() for activity in regions[region_name].activities])/sum([activity.getDuration().seconds for activity in regions[region_name].activities])*3.6, 1))+' km/h'])
            except: t.add_row(['Avg. speed:','- km/h'])
            t.add_row(['Calories:',str(sum([activity.getCalories() for activity in regions[region_name].activities]))])
            t.add_row(['Total time:',str(round(sum([activity.getDuration().seconds for activity in regions[region_name].activities])/3600.0, 2))+' h'])
            try:    t.add_row(['Avg. time:',str(round(sum([activity.getDuration().seconds for activity in regions[region_name].activities])/60.0/float(len(regions[region_name].activities)), 1))+' min'])
            except: t.add_row(['Avg. time:','- min'])
            print(t)

            if(regions[region_name].plot):
                print('    Preparing map for region: '+regions[region_name].name)
                fig = plt.figure(regions[region_name].name)
                #for mapName in bitmapMaps:
                #    if(bitmapMaps[mapName].region == region_name): bitmapMaps[mapName].plot()
                for activity in regions[region_name].activities:
                    activity.plot, = plt.plot(activity.getPositionsUTMX(), activity.getPositionsUTMY(), color='C0', linewidth=linewidth)
                activeElements = lib.tools.Persistant()
                plt.axis('equal')
                fig.canvas.mpl_connect('button_press_event', lambda event: lib.tools.mapClickCallback(event, fig, regions[region_name].activities, activeElements, linewidth))
                plt.show()


        #########################
        ## Activities by type
        #########################
        for activity_name in activityTypes:
            activityTypes[activity_name].bindActivities(activities)

            t = PrettyTable()
            t.title = 'Stats for activity: '+activityTypes[activity_name].name
            t.field_names = ['Stat','Value']
            t.add_row(['Number:',str(len(activityTypes[activity_name].activities))])
            t.add_row(['Distance:',str(round(sum([activity.getDistance() for activity in activityTypes[activity_name].activities])/1000.0,1))+' km'])
            try:    t.add_row(['Avg. speed:',str(round(sum([activity.getDistance() for activity in activityTypes[activity_name].activities])/sum([activity.getDuration().seconds for activity in activityTypes[activity_name].activities])*3.6, 1))+' km/h'])
            except: t.add_row(['Avg. speed:','- km/h'])
            t.add_row(['Calories:',str(sum([activity.getCalories() for activity in activityTypes[activity_name].activities]))])
            t.add_row(['Total time:',str(round(sum([activity.getDuration().seconds for activity in activityTypes[activity_name].activities])/3600.0, 2))+' h'])
            try:    t.add_row(['Avg. time:',str(round(sum([activity.getDuration().seconds for activity in activityTypes[activity_name].activities])/60.0/float(len(activityTypes[activity_name].activities)), 1))+' min'])
            except: t.add_row(['Avg. time:','- min'])
            print(t)


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
