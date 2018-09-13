#!/usr/bin/env python

##################
# Dependancies
##################
## Native
## Dependancies
import Tkinter           as tk
import tkinter.ttk as ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
#Internal
import lib.tools

##################
# Setup localisation
##################
import gettext
_ = gettext.gettext


###############################################################################
###############################################################################
###
###    /$$$$$$$   /$$$$$$   /$$$$$$  /$$$$$$$$
###   | $$__  $$ /$$__  $$ /$$__  $$| $$_____/
###   | $$  \ $$| $$  \ $$| $$  \__/| $$
###   | $$$$$$$ | $$$$$$$$|  $$$$$$ | $$$$$
###   | $$__  $$| $$__  $$ \____  $$| $$__/
###   | $$  \ $$| $$  | $$ /$$  \ $$| $$
###   | $$$$$$$/| $$  | $$|  $$$$$$/| $$$$$$$$
###   |_______/ |__/  |__/ \______/ |________/
###
###############################################################################
### Base interface
###############################################################################
class Interface():
    def __init__(self, regions, title='Trajectory Viewer', dynamicWindowSize=True, windowSize=[800,600], launch=True, verbose=0, **kwargs):
        '''
            IMPORTANT: Matplotlib (mpl) MUST be initialised with mpl.use('TkAgg') as soon as mpl is imported.
            '''
        ## Settings
        plt.ioff()

        ## Store data
        self.regions = regions

        ## Style
        self.style = Style()

        ## Window
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry(str(windowSize[0])+'x'+str(windowSize[1]))
        self.root.minsize(windowSize[0], windowSize[1])

        ## Menubar
        self.menubar = tk.Menu(self.root, foreground=self.style.fg, bg=self.style.bglight)
        self.filemenu = tk.Menu(self.menubar, tearoff=0, foreground=self.style.fg, bg=self.style.bglight, activebackground='#D9CB9E', activeforeground='#000000')
        self.filemenu.add_command(label=_('Quit'), command=self.quit)
        self.root.config(menu=self.menubar, bg=self.style.bglight)

        ## Frames
        self.frame_selection = tk.Frame(self.root, bg=self.style.bglight)
        self.frame_selection.pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        self.frame_data      = tk.Frame(self.root, bg=self.style.bgdark)
        self.frame_data.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=1)

        ## Prepare options
        self.frame_selection_value = tk.StringVar()
        self.frame_selection = ttk.Combobox(self.frame_selection, textvariable=self.frame_selection_value, state='readonly')
        self.frame_selection.pack(side=tk.LEFT)
        self.frame_selection['values'] = [label for label in regions if regions[label].plot]
        self.frame_selection.current(0)
        self.frame_selection.bind("<<ComboboxSelected>>", self.drawMap)

        ## Prepare canvas
        self.drawMap(**kwargs)


        ## Navigation
        self.root.protocol('WM_DELETE_WINDOW',    self.quit)


        ## Launch
        if(launch):
            self.root.focus_force()
            self.root.mainloop()




    ###########################################################################
    ## Draw Map
    ###########################################################################
    def drawMap(self, event='', **kwargs):
        try:
            self.canvas.get_tk_widget().pack_forget()
            self.canvas._tkcanvas.pack_forget()
            self.canvas = None
            self.toolbar = None
        except: pass
        fig = plt.figure('1')
        print self.frame_selection_value.get()
        for activity in self.regions[self.frame_selection_value.get()].activities:
            activity.plot, = plt.plot(activity.getPositionsUTMX(), activity.getPositionsUTMY(), color='C0', **kwargs)
        activeElements = lib.tools.Persistant()
        plt.axis('equal')
        self.canvas = FigureCanvasTkAgg(fig, self.frame_data)
        self.canvas.draw()
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.frame_data)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        self.canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas.mpl_connect('button_press_event', lambda event: lib.tools.mapClickCallback(event, self.canvas, self.toolbar, self.regions[self.frame_selection_value.get()].activities, activeElements, kwargs['linewidth']))
        self.canvas.mpl_connect('scroll_event', lambda event: lib.tools.mapZoom(event, self.canvas))



    ###########################################################################
    ## Operational functions
    ###########################################################################

    def quit(self):
        ''' Quit the program. '''
        self.root.destroy()
        self.root.quit()




##################
## Style
##################
class Style():
    def __init__(self, fg='#b6b6b6', bglight='#535353', bgdark='#262626', selection='#676767', bgborder='#424242', error='#FF0000', plotStyle=None):
        self.fg        = fg
        self.bglight   = bglight
        self.bgdark    = bgdark
        self.selection = selection
        self.bgborder  = bgborder
        self.error     = error
        if(plotStyle): self.plotStyle = plotStyle
        else:          self.plotStyle = PlotStyle()

class PlotStyle():
    def __init__(self, majorTickLength=8, minorTickLength=4, cursorWidth=2, majorTickGridLineStyle='-'):
        self.majorTickLength        = majorTickLength
        self.minorTickLength        = minorTickLength
        self.cursorWidth            = cursorWidth
        self.majorTickGridLineStyle = '-'
