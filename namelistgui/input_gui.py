"""
GUI to handle Rayleigh main input files
"""
from __future__ import print_function
import os
import wx
import wx.lib.scrolledpanel as scrolled
from namelists import InputFile, Variable
from diagnostic_outputs import OutputQuantities, render_tex, ProgressBar
import defaults
import matplotlib
matplotlib.use('WXAgg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas

if (defaults.use_tex):
    plt.rc('text', usetex=True)
    plt.rc('text.latex', preamble=r'\usepackage{amsmath}')

def AskYesNo(question, title=''):
    """ask user a yes/no question and return a boolean"""

    # build the message dialogue
    dial = wx.MessageDialog(None, question, title,
                            wx.YES_NO|wx.NO_DEFAULT|wx.ICON_QUESTION)

    # run it and get the answer/event
    ret = dial.ShowModal()

    if (ret == wx.ID_YES): # process user answer
        return True
    else:
        return False

def AskText(question, default='', title=''):
    """ask user to enter a text value"""

    # build the dialog
    dlg = wx.TextEntryDialog(None, str(question), title, value=default)

    if (dlg.ShowModal() != wx.ID_OK): # run it and capture answer
        dlg.Destroy()
        return None

    result = str(dlg.GetValue()) # convert answer to string
    return result

def ShowMessage(msg, title=None, kind='info'):
    """display a pop-up message"""
    kind = kind.lower()
    if (kind.startswith('info')):
        if (title is None): title = 'Information'
        opts = wx.OK|wx.ICON_INFORMATION
    elif (kind.startswith('error')):
        if (title is None): title = 'Error'
        opts = wx.OK|wx.ICON_ERROR
    elif (kind.startswith('warn')):
        if (title is None): title = 'Warning'
        opts = wx.OK|wx.ICON_WARNING
    else:
        opts = wx.OK
    if (title is None):
        title = ""
    dial = wx.MessageDialog(None, msg, title, opts)
    dial.ShowModal()

class InputGUI(wx.Frame):
    """
    Main GUI to handle Rayleigh input files
    """
    def __init__(self, parent, title):

        self.parent = parent

        # set size based on available screen size
        xscreen, yscreen = wx.DisplaySize()
        ysize = int(defaults.y_fact*yscreen)
        xsize = int(defaults.aspect_ratio*ysize)
        super(InputGUI, self).__init__(parent, title=title, size=(xsize,ysize))

        self.Centre() # position GUI in the center of the available space

        self.set_attributes() # initialize a bunch of empty attributes

        # build the main panel, button panel, and namelist panel
        self.mainpanel = wx.Panel(self)
        self.nmlpanel = NamelistPanel(self.mainpanel)
        self.buttons = ButtonPanel(self.mainpanel)

        self.set_menus() # initialize the menus

        self.set_statusbar() # initialize the status bar at the bottom

        # horizontal size management
        main_sizer = wx.BoxSizer(wx.HORIZONTAL) # sizer for main panel
        nml_sizer = wx.BoxSizer(wx.HORIZONTAL)  # sizer for left panel
        but_sizer = wx.BoxSizer(wx.HORIZONTAL)  # sizer for right panel

        _border = 5
        opts = wx.EXPAND|wx.ALL|wx.GROW

        nml_sizer.Add(self.nmlpanel, 1, opts, border=_border) # add each panel to its sizer
        but_sizer.Add(self.buttons, 1, opts, border=_border)
        main_sizer.Add(nml_sizer, 3, opts, border=_border) # add panel sizer to main sizer
        main_sizer.Add(but_sizer, 1, opts, border=_border) # make namelist panel 3x larger than buttons

        # apply the size manager
        self.mainpanel.SetSizer(main_sizer) # apply main sizer to main panel
        main_sizer.Layout()

    def set_attributes(self):
        """initialize a bunch of useful attributes"""

        self.input_file = None    # the InputFile object
        self.namelist = None      # the currently selected namelist
        self.file_loaded = False  # is an input file loaded or not

    def set_statusbar(self):
        """set the status bar"""
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetFieldsCount(3) # make 3 of them
        self.statusbar.SetStatusWidths([-1,-1,-2]) # last one is 2x size of 1st and 2nd, all stretch as needed
        self.statusbar.SetStatusText("", 0)
        self.statusbar.SetStatusText("Namelist:", 1)
        self.statusbar.SetStatusText("File:", 2)

    def reset_statusbar(self, text="", ind=0):
        """lazy shortcut to reset the status bar"""
        self.statusbar.SetStatusText(text, ind)

    def set_menus(self):
        """build the various menu and toolbar options"""
        #---MENU
        self.menubar = wx.MenuBar() # initialize a menu bar at the top

        fileMenu = wx.Menu() # initialize a menu and add items to it
        newItem  = fileMenu.Append(wx.ID_NEW, '&New Project', 'New')
        openItem = fileMenu.Append(wx.ID_OPEN, '&Open', 'Open Existing Input File')
        saveItem = fileMenu.Append(wx.ID_SAVE, '&Save', 'Write Project')
        quitItem = fileMenu.Append(wx.ID_EXIT, '&Quit', 'Quit')

        #toolMenu = wx.Menu() # initialize another menu and add stuff to it
        #pngItem  = toolMenu.Append(wx.ID_ANY, '&Build LaTeX Formulas', 'LaTeX Formulas')

        nmlMenu = wx.Menu() # initialize another menu

        # puposefully do *not* bind this with anything just yet
        nmlItem = nmlMenu.Append(wx.ID_ANY, '--No File Loaded--', '--No File Loaded--')

        # add the menu(s) to the menu bar
        self.menubar.Append(fileMenu, '&File')
        #self.menubar.Append(toolMenu, '&Tools')
        self.menubar.Append(nmlMenu, '&Namelists')

        self.nml_menu_index = 1 # index into menubar that returns the Namelist menu

        # finalize/build the menubar
        self.SetMenuBar(self.menubar)

        # direct GUI what to do when something is selected
        self.Bind(wx.EVT_MENU, self.buttons.OnNew,  newItem)
        self.Bind(wx.EVT_MENU, self.buttons.OnOpen, openItem)
        self.Bind(wx.EVT_MENU, self.buttons.OnSave, saveItem)
        self.Bind(wx.EVT_MENU, self.buttons.OnQuit, quitItem)

        #self.Bind(wx.EVT_MENU, self.buttons.OnBuildPNGs, pngItem)

        #---TOOLBAR
        toolbar = self.CreateToolBar() # build a toolbar

        # build tools
        file_dir = os.path.dirname(os.path.abspath(__file__)) # directory of current file
        image_dir = os.path.join(file_dir, 'images')
        ntool = toolbar.AddTool(wx.ID_ANY, 'New', wx.Bitmap(os.path.join(image_dir, 'new_file.png')))
        otool = toolbar.AddTool(wx.ID_ANY, 'Open', wx.Bitmap(os.path.join(image_dir, 'open_folder.png')))
        stool = toolbar.AddTool(wx.ID_ANY, 'Save', wx.Bitmap(os.path.join(image_dir, 'filesave.png')))

        # direct GUI what to do when something is selected
        self.Bind(wx.EVT_TOOL, self.buttons.OnNew,  ntool)
        self.Bind(wx.EVT_TOOL, self.buttons.OnOpen, otool)
        self.Bind(wx.EVT_TOOL, self.buttons.OnSave, stool)

        # finalize/build the toolbar
        toolbar.Realize()

    def reset_namelist_menu(self):
        """reset the namelists menu to be empty"""
        new_nml = wx.Menu() # build new menu

        # add single element, don't bind it to anything
        nmlItem = new_nml.Append(wx.ID_ANY, '--No File Loaded--', '--No File Loaded--')

        # replace the second menu, index=1
        self.menubar.Replace(self.nml_menu_index, new_nml, '&Namelists')

        self.namelist = None # there is no longer a current namelist
        self.statusbar.SetStatusText("Namelist: --No File Loaded--", 1)

    def update_namelist_menu(self):
        """update the namelists menu with supported namelists"""
        new_nml = wx.Menu() # build new menu

        # populate entries and bind their selection
        for i,nml in enumerate(self.input_file.namelists.keys()):
            item = new_nml.Append(i, self.input_file.namelists[nml].name)
            self.Bind(wx.EVT_MENU, self.SelectNamelist, item, id=i)

        # replace old menu in the 1st position with updated one (0-based indexing)
        self.menubar.Replace(self.nml_menu_index, new_nml, '&Namelists')

        # reset the namelist entries that are displayed
        self.nmlpanel.reset(unset_namelist=True) # ensure no namelist is currently selected

        self.statusbar.SetStatusText("Choose a namelist from the menu", 1)

    def SelectNamelist(self, e):
        """what to do when a namelist is selected from the menu"""
        _id = e.GetId()
        names = list(self.input_file.namelists.keys()) # all namelist names in the input file
        self.namelist = names[_id]

        self.nmlpanel.update(unset_namelist=False) # display the namelist values

        self.reset_statusbar()
        self.statusbar.SetStatusText("Namelist: {}".format(self.namelist), 1)

    def OnQuit(self, e):
        """exit the application"""
        self.buttons.Destroy()   # destroy individual panels
        self.nmlpanel.Destroy()
        self.mainpanel.Destroy()
        self.Close()             # close the application

class ButtonPanel(wx.Panel):
    """
    The button panel that will appear on the right side
    """
    def __init__(self, parent):

        self.parent = parent
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.SUNKEN_BORDER)

        self.mainparent = self.GetParent().GetParent() # very clunky(?), but works

        self.sizer = wx.BoxSizer(wx.VERTICAL) # space management in the vertical

        _border = 5
        button_opts = wx.EXPAND|wx.ALL|wx.GROW

        # build some buttons, bind them to an event handler, and add them to spacer
        names = ["Open", "Write to File", "Add New Variable",
                 "Remove Variable", "Add New Namelist", "Remove Namelist"]
        handles = [self.OnOpen, self.OnSave, self.AddVariable,
                   self.RemoveVariable, self.AddNamelist, self.RemoveNamelist]

        for name, handle in zip(names, handles):
            some_button = wx.Button(self, -1, name)
            some_button.Bind(wx.EVT_BUTTON, handle)
            self.sizer.Add(some_button, 1, button_opts, border=_border)

        # apply the size manager
        self.SetSizer(self.sizer)
        self.Fit()

    def AddVariable(self, e):
        """add a variable to the current namelist"""
        if (not self.mainparent.file_loaded):
            msg = "An input file must be loaded before a variable can be added"
            ShowMessage(msg, kind='warn')
            return
        if (self.mainparent.namelist is None):
            msg = "Use the menu to select a namelist, first"
            ShowMessage(msg, kind='info')
            return
        self.mainparent.statusbar.SetStatusText("Adding new variable", 0)

        # get variable name/value from user
        dlg = NewVariableDialog(self.parent, "Enter New Variable")
        if (dlg.ShowModal() != wx.ID_OK):
            dlg.Destroy()
            self.mainparent.reset_statusbar()
            return

        name, value = dlg.get_values()

        var = Variable(name, value) # add variable
        self.mainparent.input_file.namelists[self.mainparent.namelist].add_variable(var)

        self.mainparent.statusbar.SetStatusText("Added: {}".format(name), 0)

        self.mainparent.nmlpanel.update(unset_namelist=False) # update displayed namelist to include new entry

    def RemoveVariable(self, e):
        """remove a variable from current namelist"""
        if (not self.mainparent.file_loaded):
            msg = "An input file must be loaded before a variable can be removed"
            ShowMessage(msg, kind='warn')
            return
        if (self.mainparent.namelist is None):
            msg = "Use the menu to select a namelist, first"
            ShowMessage(msg, kind='info')
            return
        self.mainparent.statusbar.SetStatusText("Removing a variable", 0)

        remove_name = AskText("Enter variable name to remove", title="Remove Variable")

        if (remove_name is not None):
            self.mainparent.input_file.namelists[self.mainparent.namelist].remove_variable(remove_name)

            # redraw stuff
            self.mainparent.statusbar.SetStatusText("Removed: {}".format(remove_name), 0)
            self.mainparent.nmlpanel.update(unset_namelist=False) # update displayed namelist to include new entry

    def AddNamelist(self, e):
        """add a namelist"""
        if (not self.mainparent.file_loaded):
            msg = "An input file must be loaded before a namelist can be added"
            ShowMessage(msg, kind='warn')
            return
        self.mainparent.statusbar.SetStatusText("Adding a namelist", 0)

        name = AskText("Enter name of new namelist", title="Add a Namelist")

        if (name is not None):
            self.mainparent.input_file.add_namelist(name)

            # redraw stuff
            self.mainparent.update_namelist_menu() # update available namelist menu
            self.mainparent.statusbar.SetStatusText("Added: {}".format(name), 0)

    def RemoveNamelist(self, e):
        """remove a namelist"""
        if (not self.mainparent.file_loaded):
            msg = "An input file must be loaded before a namelist can be removed"
            ShowMessage(msg, kind='warn')
            return
        self.mainparent.statusbar.SetStatusText("Remove a namelist", 0)

        name = AskText("Enter name of namelist ro remove", title="Remove a Namelist")

        if (name is not None):
            self.mainparent.input_file.remove_namelist(name)

            # redraw stuff
            self.mainparent.update_namelist_menu() # update available namelist menu
            self.mainparent.statusbar.SetStatusText("Removed: {}".format(name), 0)

            if (self.mainparent.namelist == name):
                self.mainparent.nmlpanel.reset(unset_namelist=True)

    def OnBuildPNGs(self, e):
        """generate the LaTeX formula images"""
        if (not defaults.use_tex):
            msg = "LaTeX is disabled in the defaults.py file. To use this functionality, change the"
            msg += " use_tex option to True and restart the GUI."
            ShowMessage(msg, kind='warn')
            return
        question = "Quantity code formulas are displayed using PNG images, which need to be generated."
        question += "\n\n\nImages should only be generated if they do not already exist or"
        question += " the quantity codes have changed, e.g., more custom outputs have been added."
        question += "\n\n\nThis can take ~60 sec, do you want to proceed?"
        proceed = AskYesNo(question, title='Generate LaTeX Formula Images?')
        if (not proceed): return

        question = "Choose a path where the images will be saved. The default value from defaults.py is shown."
        path = AskText(question, default=defaults.quantity_code_image_path, title="Where to store images?")
        if (path is None): return
        defaults.quantity_code_image_path = path # user overrode this quantity, remember for later

        question = "If image files already exist, do you want to overwrite them?"
        overwrite = AskYesNo(question, title='Overwrite Existing Files?')

        # call render routine and display a progress bar
        Nq = len(self.mainparent.nmlpanel.output_quantities.quantities)
        offsets = list(self.mainparent.nmlpanel.output_quantities.offsets.keys())

        P = ProgressBar(Nq)
        P(0)
        for i,Q in enumerate(self.mainparent.nmlpanel.output_quantities.quantities):
            if (Q.name in offsets): continue
            render_tex(Q.code, Q.tex, defaults.quantity_code_image_path, overwrite=overwrite)

            P(i+1) # update progress bar

    def OnNew(self, e):
        """build an empty namelist"""
        self.mainparent.statusbar.SetStatusText("New Project", 0)

        filename = "__new_project__"
        self.mainparent.input_file = InputFile(filename, read=False)
        self.mainparent.statusbar.SetStatusText("---New Project---", 2)
        self.mainparent.file_loaded = True

        # reset menus and such
        self.mainparent.reset_namelist_menu()
        self.mainparent.nmlpanel.reset(unset_namelist=True)

    def OnOpen(self, e):
        """open/read an existing input file"""
        self.mainparent.statusbar.SetStatusText("Loading Files ...", 0)

        dirname = os.getcwd()
        dlg = wx.FileDialog(self, "Select File", dirname, "", "*", wx.FD_OPEN)

        if (dlg.ShowModal() != wx.ID_OK):
            dlg.Destroy()
            self.mainparent.reset_statusbar()
            return

        full_path = str(dlg.GetPath()) # get selected filename and convert to standard string

        self.mainparent.input_file = InputFile(full_path) # parse input file

        self.mainparent.update_namelist_menu() # update available namelist menu

        self.mainparent.reset_statusbar()
        self.mainparent.statusbar.SetStatusText("File: {}".format(full_path), 2)

        self.mainparent.file_loaded = True

    def OnSave(self, e):
        """save/write progress to a file"""
        if (not self.mainparent.file_loaded):
            msg = "An input file must be loaded/built before it can be written"
            ShowMessage(msg, kind='warn')
            return
        self.mainparent.statusbar.SetStatusText("Select a File ...", 0)

        dirname = os.getcwd()
        dlg = wx.FileDialog(self, "Save File", dirname, "", "*", wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)

        if (dlg.ShowModal() != wx.ID_OK):
            dlg.Destroy()
            self.mainparent.reset_statusbar()
            return

        full_path = str(dlg.GetPath()) # get selected filename and convert to standard string

        # set overwrite to True since the above FileDialog already asked
        self.mainparent.input_file.write(output=full_path, indent=defaults.indent, overwrite=True)
        self.mainparent.statusbar.SetStatusText("Written to: {}".format(full_path), 0)

        self.mainparent.input_file.filename = full_path
        self.mainparent.statusbar.SetStatusText("File: {}".format(full_path), 2)

    def OnQuit(self, e):
        """exit the application"""
        self.mainparent.OnQuit(e)

class NamelistPanel(scrolled.ScrolledPanel):
    """
    The namelist panel that will appear on the left side
    """
    def __init__(self, parent):

        self.parent = parent
        scrolled.ScrolledPanel.__init__(self, parent, wx.ID_ANY, style=wx.SUNKEN_BORDER)

        self.mainparent = self.GetParent().GetParent() # very clunky(?), but works

        self.main_sizer = None # will become a space manager in the vertical
        self.loaded = False

        #----
        # parse source tree to get valid quantity codes, latex definitions, and diagnostic types
        #----
        if (defaults.diagnostics_dir is None):
            search_path = defaults.rayleigh_dir
            default_loc = True
        else:
            search_path = defaults.diagnostis_dir
            default_loc = False
        self.output_quantities = OutputQuantities(search_path, default_location=default_loc)
        self.diag_type = None

        # draw/display the selected namelist
        if (self.mainparent.file_loaded and (self.mainparent.namelist is not None)):
            self.update(unset_namelist=False)

    def update(self, unset_namelist=False):
        """draw the Namelist panel"""

        self.reset(unset_namelist=unset_namelist) # make sure it is empty, to avoid overlapping text

        entry = "Namelist: {}".format(self.mainparent.namelist)
        title = wx.StaticText(self, -1, entry)

        # this option is only available if LaTeX is supported
        is_output_namelist = ((self.mainparent.namelist == "output_namelist") and defaults.use_tex)

        # buttons
        save = wx.Button(self, -1, 'Save Entries')
        save.Bind(wx.EVT_BUTTON, self.Save)
        close = wx.Button(self, -1, 'Close Namelist')
        close.Bind(wx.EVT_BUTTON, self.Remove)

        # only applicable to output namelist
        if (is_output_namelist):
            advanced_entry = wx.Button(self, -1, 'Choose \"<output>_values\"')
            advanced_entry.Bind(wx.EVT_BUTTON, self.OutputEntry)

        # size managers
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        title_sizer = wx.BoxSizer(wx.HORIZONTAL)
        grid_sizer = wx.GridBagSizer(0,0)

        _border = 5
        static_opts = wx.ALL|wx.ALIGN_CENTER
        text_opts = wx.EXPAND|wx.ALL

        # add the title & buttons to top row
        title_sizer.Add(title, 1, text_opts|wx.GROW|wx.ALIGN_CENTER, border=_border)
        if (is_output_namelist):
            title_sizer.Add(advanced_entry, 0, text_opts|wx.GROW, border=_border)
        title_sizer.Add(close, 0, text_opts|wx.GROW, border=_border)
        title_sizer.Add(save, 0, text_opts|wx.GROW, border=_border)

        # extract valid namelist variable names and their values
        nml = self.mainparent.input_file.namelists[self.mainparent.namelist]
        self.var_names = [v.name for v in nml.variables]
        self.var_values = [v.value for v in nml.variables]

        # add entries to individual sizers, span=(number of rows, number of columns)
        self.entries = []
        row = 0
        for i in range(len(self.var_names)):
            variable_name = self.var_names[i]
            name = wx.StaticText(self, -1, variable_name) # build lhs name
            val = ",".join(self.var_values[i])

            # make certain text-entry boxes more accepting of long entries
            if ("_values" in variable_name or "_levels" in variable_name or \
                "_indices" in variable_name or "_mode_ell" in variable_name):
                length = len(val)
                row_span = max(length // 50, 1) # arbitrarily choose 50 characters
                if (row_span > 1):
                    growable = True
                    style = wx.TE_MULTILINE
                else:
                    growable = False
                    style = 0

                # sort the values before displaying them, but ignore stuff with negative numbers
                if ("-" not in val):
                    if ("." in val): # val has been "comma-combined", so leverage this fact
                        val = [float(v) for v in val.split(",")]
                    else:
                        val = [int(v) for v in val.split(",")]
                    val.sort()
                    val = [str(v) for v in val]
                    val = ",".join(val)
            else:
                style = 0
                growable = False
                row_span = 1
            entry = wx.TextCtrl(self, i, val, style=style)  # build rhs entry, with current value filled in

            self.entries.append(entry) # store the rhs for use later

            # add name/entry to sizer
            grid_sizer.Add(name, pos=(row,0), flag=static_opts, border=_border)
            if (row_span > 1):
                grid_sizer.Add(entry, pos=(row,1), span=(row_span,1), flag=text_opts, border=_border)
            else:
                grid_sizer.Add(entry, pos=(row,1), flag=text_opts, border=_border)
            if (growable):
                grid_sizer.AddGrowableRow(row,1)

            row += row_span # not one, to avoid overlapping entries

        if (len(self.var_names) > 0):
            grid_sizer.AddGrowableCol(1,1) # make the second column "1" growable, i.e., grows as necessary

        # add individual sizers to main sizer
        self.main_sizer.Add(title_sizer, 0, wx.ALL|wx.EXPAND|wx.CENTER|wx.GROW, border=_border)
        self.main_sizer.Add(wx.StaticLine(self), 0, wx.ALL|wx.EXPAND|wx.GROW, border=_border)
        self.main_sizer.Add(grid_sizer, 0, wx.ALL|wx.EXPAND|wx.GROW, border=_border)

        self.SetSizer(self.main_sizer) # apply sizing/fit
        self.main_sizer.Fit(self)

        self.Center()

        self.parent.Layout()
        self.SetAutoLayout(1) # setup scrolling, if it is needed
        self.SetupScrolling()

        self.loaded = True

    def Save(self, e):
        """save entries from Namelist"""
        for i in range(len(self.var_names)):
            name = self.var_names[i]
            entry = str(self.entries[i].GetValue()).strip() # grab user entries

            # convert entry into a list
            if ("," in entry):
                vals = entry.split(",")
                values = [v.strip() for v in vals]
            else:
                values = [entry]

            variable = Variable(name, values) # build a Variable object

            # update the variable values
            n = self.mainparent.namelist
            self.mainparent.input_file.namelists[n].add_variable(variable)

        self.mainparent.statusbar.SetStatusText("Namelist saved", 0)

    def reset(self, unset_namelist=False):
        """reset the Namelist panel"""
        if (self.loaded):
            for child in self.GetChildren(): # loop over all children in the panel
                child.Destroy()
            try:
                self.main_sizer.Layout()
            except:
                pass
            self.loaded = False
            if (unset_namelist):
                self.mainparent.namelist = None
                self.mainparent.statusbar.SetStatusText("Namelist closed", 0)
                self.mainparent.statusbar.SetStatusText("Choose a namelist from the menu", 1)

    def Remove(self, e):
        """close the Namelist panel using a button"""
        self.reset(unset_namelist=True)

    def OutputEntry(self, e):
        """open up a better way to enter output values"""
        current_namelist = self.mainparent.namelist
        input_file = self.mainparent.input_file
        output_namelist = input_file.namelists[current_namelist]

        self.reset(unset_namelist=False) # clear the panel buttons/widgets, but keep namelist set

        _border = 5
        static_opts = wx.ALL|wx.ALIGN_CENTER
        text_opts = wx.EXPAND|wx.ALL

        # output types mapped to namelist appearance
        self.output_types = {"Shell Slice":"shellslice",
                             "Shell Spectra":"shellspectra",
                             "Point Probes":"point_probe",
                             "Meridional Slice":"meridional",
                             "Equatorial Slice":"equatorial",
                             "Az Average":"azavg",
                             "Shell Average":"shellavg",
                             "Global Average":"globalavg",
                             "SPH Mode":"sph_mode",
                             "Spherical 3D":"full3d"}
        self.output_type = None

        #----
        # build contents, will share much of the update() method content, but with important differences
        #
        #     output type: <output>    diagnostic type: <diagnostics>
        #            <close button>    <save/add button>
        #     ----------------------------------------------------------------------------------
        #              some kind of title/header page
        #     ----------------------------------------------------------------------------------
        #     <row 1: a check box> <row 2: quantity code> <row 3: Name> <row 4: LaTeX rendering>
        #     ...
        #     ... entries change based on <diagnostic type>
        #     ...
        #----
        self.main_sizer.Add(wx.StaticLine(self), 0, wx.ALL|wx.EXPAND|wx.GROW, border=_border)

        # size managers
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        title_sizer = wx.BoxSizer(wx.HORIZONTAL)
        combo_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.grid_sizer = wx.GridBagSizer(0,0)

        # setup the title
        self.num_values = 0
        self.output = wx.StaticText(self, -1, "Output Type: <select one>")
        self.diagnostic_type = wx.StaticText(self, -1, "Diagnostic Type: <select one>")

        # combo boxes and bind them
        keys = list(self.output_types.keys()); keys.sort()
        self.output_combo = wx.ComboBox(self, choices=keys, style=wx.CB_DROPDOWN)
        self.output_combo.Bind(wx.EVT_COMBOBOX, self.SelectOutput)

        keys = list(self.output_quantities.diagnostic_types.keys()); keys.sort()
        self.diag_type_combo = wx.ComboBox(self, choices=keys, style=wx.CB_DROPDOWN)
        self.diag_type_combo.Bind(wx.EVT_COMBOBOX, self.SelectDiagType)

        # buttons
        save = wx.Button(self, -1, 'Update/Save Selected Entries')
        save.Bind(wx.EVT_BUTTON, self.SaveValues)
        close = wx.Button(self, -1, 'Close Namelist')
        close.Bind(wx.EVT_BUTTON, self.Remove)
        back = wx.Button(self, -1, 'Return to Output_Namelist')
        back.Bind(wx.EVT_BUTTON, self.ReturnToOutput)

        # add title/combo/buttons to sizers
        title_sizer.Add(self.output, 1, text_opts|wx.GROW, border=_border)
        title_sizer.Add(self.diagnostic_type, 1, text_opts|wx.GROW, border=_border)
        combo_sizer.Add(self.output_combo, 1, text_opts|wx.GROW, border=_border)
        combo_sizer.Add(self.diag_type_combo, 1, text_opts|wx.GROW, border=_border)
        button_sizer.Add(close, 0, text_opts|wx.GROW, border=_border)
        button_sizer.Add(back, 0, text_opts|wx.GROW, border=_border)
        button_sizer.Add(save, 0, text_opts|wx.GROW, border=_border)

        # draw table of entries and update grid_sizer accordingly
        self.grid_sizer = self.change_entries(self.grid_sizer, static_opts, _border)

        # add stuff to sizers
        self.main_sizer.Add(title_sizer, 0, wx.ALL|wx.EXPAND|wx.CENTER|wx.GROW, border=_border)
        self.main_sizer.Add(combo_sizer, 0, wx.ALL|wx.EXPAND|wx.CENTER|wx.GROW, border=_border)
        self.main_sizer.Add(button_sizer, 0, wx.ALL|wx.EXPAND|wx.CENTER|wx.GROW, border=_border)
        self.main_sizer.Add(wx.StaticLine(self), 0, wx.ALL|wx.EXPAND|wx.GROW, border=_border)
        self.main_sizer.Add(self.grid_sizer, 0, wx.ALL|wx.EXPAND|wx.CENTER|wx.GROW, border=_border)

        self.SetSizer(self.main_sizer) # apply sizing/fit
        self.main_sizer.Fit(self)

        self.Center()

        self.parent.Layout()
        self.SetAutoLayout(1) # setup scrolling, if it is needed
        self.SetupScrolling()

        self.loaded = True

    def change_entries(self, grid_sizer, options, border):
        """add the table of entries to the grid sizer"""

        if (self.diag_type is None): return grid_sizer # no data selected, don't change anything

        # setup the grid of possible values
        header0 = wx.StaticText(self, -1, "Add/Remove")
        header1 = wx.StaticText(self, -1, "Quantity Code")
        header2 = wx.StaticText(self, -1, "Name")
        header3 = wx.StaticText(self, -1, "LaTeX Formula")
        grid_sizer.Add(header0, pos=(0,0), flag=options, border=border)
        grid_sizer.Add(header1, pos=(0,1), flag=options, border=border)
        grid_sizer.Add(header2, pos=(0,2), flag=options, border=border)
        grid_sizer.Add(header3, pos=(0,3), flag=options, border=border)
        grid_sizer.Add(wx.StaticLine(self), pos=(1,0), span=(1,4),
                               flag=wx.ALL|wx.EXPAND|wx.GROW, border=border)

        self.selected_values = [] # keep track of selected quantities

        quantities = self.output_quantities.diagnostic_types[self.diag_type]

        # choose a good height/width for formulas
        if (self.diag_type in ["Linear_Forces", "Angular_Momentum", "Energy_Flux",
                               "Induction", "Inertial_Forces", "Lorentz_Forces",
                               "Poynting_Flux", "TurbKE_Budget"]):
            width = 100
        elif (self.diag_type == "Thermal_Equation"):
            width = 150
        else:
            width = 30
        height = 20

        row = 2
        iquant = 0
        for Q in quantities:
            but = wx.ToggleButton(self, Q.code, "Add") # build button and place it in second column
            but.Bind(wx.EVT_TOGGLEBUTTON, self.OnToggle)
            grid_sizer.Add(but, pos=(row,0), flag=options, border=border)

            q_code = wx.StaticText(self, -1, str(Q.code)) # build other column entries
            q_name = wx.StaticText(self, -1, Q.name) # name

            formula = self.RenderTeX(Q, size=(width,height))

            # place column entries
            grid_sizer.Add(q_code, pos=(row,1), flag=options, border=border)
            grid_sizer.Add(q_name, pos=(row,2), flag=options, border=border)
            grid_sizer.Add(formula, pos=(row,3), flag=options, border=border)

            iquant += 1

            # add horizontal line every 5 quantities
            if (iquant % 5 == 0):
                grid_sizer.Add(wx.StaticLine(self), pos=(row+1,0), span=(1,4),
                               flag=wx.ALL|wx.EXPAND|wx.GROW, border=border)
                row_inc = 2
            else:
                row_inc = 1

            row += row_inc

        grid_sizer.AddGrowableCol(2,1) # make the name/formula columns "1" growable, i.e., grows as necessary
        grid_sizer.AddGrowableCol(3,1)

        return grid_sizer

    def RenderTeX(self, Q, size=None, dpi=50):
        """render the string using LaTeX, size=tuple containing (width,height) in pixels"""
        code = Q.code
        name = Q.name
        tex  = Q.tex
        if (defaults.use_tex):
            #try:
            if (1):
                # convert width/height in pixels to inches and add some padding
                if (size is None):
                    w = defaults.tex_width
                    h = defaults.tex_height
                else:
                    w,h = size
                w *= defaults.tex_padding/dpi
                h *= defaults.tex_padding/dpi
                fig = Figure(figsize=(w,h))
                formula = FigureCanvas(self, -1, fig)

                fig.clear()
                fig.text(0.05, 0.25, tex, fontsize=defaults.tex_fontsize) # draw the LaTeX formula onto canvas
                formula.draw()
            #try:
            #    filename = os.path.join(defaults.quantity_code_image_path, "{}.png".format(code))
            #    png_image = wx.Image(filename, wx.BITMATP_TYPE_ANY).ConvertToBitmap()
            #    formula = wx.StaticBitmap(self, -1, png_image) #, pos=position, size=size)
            else:
            #except:
                formula = wx.StaticText(self, -1, "Error Importing Formula Image")
        else:
            formula = wx.StaticText(self, -1, "LaTeX was disabled")

        return formula

    def OnToggle(self, e):
        """what to do when quantity code button is selected"""
        state = e.GetEventObject().GetValue() # state of button = True/False
        _id = e.GetId() # ID is the quantity code

        if (state):
            e.GetEventObject().SetLabel("Remove") # change button text

            if (_id not in self.selected_values): # add quantity
                self.selected_values.append(str(_id))

        else:
            e.GetEventObject().SetLabel("Add") # change button text

            if (_id in self.selected_values): # remove quantity
                self.selected_values.remove(str(_id))

    def SelectDiagType(self, e):
        """what to do when a diagnostic type was selected"""
        self.diag_type = str(self.diag_type_combo.GetValue())
        self.diagnostic_type.SetLabel("Diagnostic Type: {}".format(self.diag_type))

        border = 5
        opts = wx.ALL|wx.ALIGN_CENTER

        new_grid_sizer = wx.GridBagSizer(0,0) # build new table with updated info

        # fill in the data
        new_grid_sizer = self.change_entries(new_grid_sizer, opts, border)

        # hide old sizer content
        self.main_sizer.Hide(self.grid_sizer, recursive=True)

        # replace sizers
        self.main_sizer.Replace(self.grid_sizer, new_grid_sizer)

        # store new one
        self.grid_sizer = new_grid_sizer

        self.SetSizer(self.main_sizer) # apply sizing/fit
        self.main_sizer.Fit(self)

        self.Center()

        self.parent.Layout()
        self.SetAutoLayout(1) # setup scrolling, if it is needed
        self.SetupScrolling()

    def SelectOutput(self, e):
        """what to do when an output type was selected"""
        self.output_type = str(self.output_combo.GetValue())
        self.output.SetLabel("Output Type: {}".format(self.output_type))

    def SaveValues(self, e):
        """save value entries from Namelist"""
        if (self.output_type is None):
            msg = "The quantities are not associated with an output type. Choose one and re-save."
            ShowMessage(msg, kind='warn')
            return
        self.num_values = len(self.selected_values)

        nml = self.mainparent.input_file.namelists[self.mainparent.namelist]
        var_names = [v.name for v in nml.variables]

        name = self.output_types[self.output_type] + "_values"
        values = list(set(self.selected_values))

        if (name in var_names): # name already in namelist, add to old values
            ind = var_names.index(name)
            current_values = nml.variables[ind].value
            values = list(set(current_values + values))

        new_variable = Variable(name, values)
        nml.add_variable(new_variable, modify=True)

        self.mainparent.statusbar.SetStatusText("Added {} {} quantities".format(self.num_values, self.output_type), 0)

    def ReturnToOutput(self, e):
        """go back to the output namelist"""
        names = list(self.mainparent.input_file.namelists.keys()) # all namelist names in the input file
        if ("output_namelist" not in names):
            msg = "The Output_Namelist no longer exists, must be manually added."
            ShowMessage(msg, kind='warn')
            return

        ind = names.index("output_namelist")
        self.mainparent.namelist = names[ind]

        self.mainparent.nmlpanel.update(unset_namelist=False) # display the namelist values

        self.mainparent.reset_statusbar()
        self.mainparent.statusbar.SetStatusText("Namelist: {}".format(self.mainparent.namelist), 1)

class NewVariableDialog(wx.Dialog):
    """
    Get new variable data from the user
    """
    def __init__(self, parent, title):

        wx.Dialog.__init__(self, parent, -1, title)

        self.mainparent = self.GetParent().GetParent()

        # define the entries
        name  = wx.StaticText(self, -1, "Name")
        value = wx.StaticText(self, -1, "Value")
        entry = "Note: character values must include quotes, array entries must include commas"
        note = wx.StaticText(self, -1, entry)

        self.name_entry  = wx.TextCtrl(self, 1, "")
        self.value_entry = wx.TextCtrl(self, 2, "")

        # buttons
        ok = wx.Button(self, wx.ID_OK, 'Add')
        cancel = wx.Button(self, wx.ID_CANCEL, 'Cancel')

        # size managers
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        name_s = wx.BoxSizer(wx.HORIZONTAL)   # name sizer
        value_s = wx.BoxSizer(wx.HORIZONTAL)  # value sizer
        note_s = wx.BoxSizer(wx.HORIZONTAL)   # note sizer
        button_s = wx.BoxSizer(wx.HORIZONTAL) # button sizer

        _border = 5
        opts = wx.EXPAND|wx.ALL|wx.GROW

        # add entries to sizers
        name_s.Add(name, 0, opts, border=_border)            # add lhs of Name, i.e., text entry
        name_s.Add(self.name_entry, 1, opts, border=_border) # add rhs of Name, i.e., user entry
        value_s.Add(value, 0, opts, border=_border)            # text entry
        value_s.Add(self.value_entry, 1, opts, border=_border) # user entry
        note_s.Add(note, 0, opts, border=_border)              # notes
        button_s.Add(cancel, 0, opts, border=_border)          # both buttons
        button_s.Add(ok, 0, opts, border=_border)

        main_sizer.Add(name_s, 0, opts, border=_border) # add individual sizers to main sizer
        main_sizer.Add(value_s, 0, opts, border=_border)
        main_sizer.Add(note_s, 0, opts, border=_border)
        main_sizer.Add(button_s, 0, opts, border=_border)

        self.SetSizer(main_sizer) # apply sizer
        main_sizer.Fit(self)

        self.Center()

    def get_values(self):
        """return user entered values"""
        name = str(self.name_entry.GetValue())   # convert user entries into useful strings
        value = str(self.value_entry.GetValue())
        return name, value

class MyProgressBar(wx.Dialog):
    """
    Popup window showing a progress bar
    """
    def __init__(self, parent, title, start=0, stop=100):

        self.parent = parent

        wx.Dialog.__init__(self, parent, -1, title)

        self.stop = stop

        # initialize the Gauge
        self.gauge = wx.Gauge(self, -1, range=self.stop, style=wx.GA_HORIZONTAL, name="Progress")
        self.gauge.SetValue(start)

        # add some text to left of gauge
        txt = wx.StaticText(self, -1, "Progress:")

        # add button below
        close = wx.Button(self, wx.ID_CLOSE, 'Add')

        sizer = wx.BoxSizer(wx.VERTICAL)
        Hsizer = wx.BoxSizer(wx.HORIZONTAL) # main sizer
        Hsizer.Add(txt, 0, wx.CENTER)
        Hsizer.Add(self.gauge, 1, wx.GROW|wx.EXPAND|wx.ALL, border=5)

        sizer.Add(Hsizer, 1, wx.GROW|wx.EXPAND|wx.ALL, border=5)
        sizer.Add(close, 0, wx.GROW|wx.EXPAND|wx.ALL, border=5)

        self.SetSizer(sizer)
        sizer.Fit(self)

        self.Center()

    def Update(self, step):
        """update the progress bar"""
        self.gauge.SetValue(step)
        if (step == self.stop):
            self.Close()

    def Close(self):
        self.Close()

def main():
    """
    Run the application
    """
    app = wx.App(redirect=False) # build an application

    # build the GUI
    gui = InputGUI(None, "Rayleigh Input File GUI")
    gui.Show()

    # run the main loop to capture events
    app.MainLoop()

if __name__ == "__main__":
    main()

