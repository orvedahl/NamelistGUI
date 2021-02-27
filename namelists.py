"""
Classes to read/write/modify Rayleigh input files
"""
from __future__ import print_function
import os
from collections import OrderedDict

class Variable:
    """
    A Fortran variable that appears in a namelist. Data type information is not recorded

    Attributes
    ----------
    name : str
        The variable name
    value : list of str
        The value of the variable as a string
    """

    def __init__(self, name, value):
        """
        Args
        ----
        name : str
            The variable name
        value : list of str
            The value of the variable as a string
        """
        self.name = name.lower()

        if (not isinstance(value,list)):
            self.value = [value]
        else:
            self.value = value

    def write(self, filename, indent="  "):
        """
        Write the variable to the namelist file, formatted as
            name = value
        or
            name = value0,value1,value2,...

        Args
        ----
        filename : file
            The namelist file object where the variable will be written
        indent : str, optional
            The indentation to use when writing variable entry
        """
        if (self.value is None):
            print("ERROR: variable \"{}\" was not given a value, skipping".format(self.name))
            return

        if (indent.strip() != ""):
            raise ValueError("Indent must only include empty space: indent = \"{}\"".format(indent))

        rhs = ",".join(self.value)
        entry = "{}{} = {}".format(indent, self.name, rhs)

        # write variable to file
        filename.write(entry + "\n")

class Namelist:
    """
    A single Fortran namelist, i.e., a collection of variables

    Attributes
    ----------
    name : str
        The name of the namelist
    variables : list
        Collection of Variable objects
    """

    def __init__(self, name):
        """
        Args
        ----
        name : str
            The name of the namelist
        """
        self.name = name.lower()
        self.variables = []

    def add_variable(self, variable, modify=True):
        """
        Add variables to the namelist

        Args
        ----
        variable : Variable object
            The variable to add
        modify : bool
            If true, update the entry if it already exists. If false, just append variable
        """
        var_name = variable.name
        names = [v.name for v in self.variables]

        # overwrite existing value
        if (modify and (var_name in names)):
            ind = names.index(var_name)
            self.variables[ind] = variable
        else:
            self.variables.append(variable)

    def add_variables(self, variables, modify=True):
        """
        Add multiple variables to the namelist

        Args
        ----
        variables : list of Variable objects
            The variables to add
        modify : bool
            If true, update the entry if it already exists. If false, just append variable
        """
        if (not isinstance(variables,list)):
            variables = [variables]
        for var in variables:
            self.add_variable(var, modify=modify)

    def write(self, filename, indent="  ", verbose=False):
        """
        Write the namelist to the file, formatted as
            &namelist_name
               name = value
               ...
               name = value0,value1,value2,...
            /

        Args
        ----
        filename : file
            The file object where the namelist will be written
        indent : str, optional
            The indentation to use when writing variable entry
        verbose : bool
            Print more information
        """
        if (indent.strip() != ""):
            raise ValueError("Indent must only include empty space: indent = \"{}\"".format(indent))

        if (verbose):
            print("Writing namelist = {}".format(self.name))
        filename.write("&{}".format(self.name) + "\n")

        for var in self.variables:
            var.write(filename, indent=indent)

        filename.write("/" + "\n")

class InputFile:
    """
    An input file consisting of multiple Fortran namelists, does not preserve comments

    Attributes
    ----------
    filename : str
        The filename of the input list
    namelists : dict
        Collection of Namelist objects
    """

    def __init__(self, filename, read=True, verbose=False):
        """
        Args
        ----
        filename : str
            The filename of the input file
        read : bool
            Open the file and process the contents
        verbose : bool
            Print more information
        """
        self.filename = filename
        self.verbose = verbose
        self.namelists = OrderedDict()
        if (read):
            self.read()

    def write(self, output=None, overwrite=False, indent="  "):
        """
        Write out the input file

        Args
        ----
        output : str, optional
            Where to write the namelist, default is filename given at initialization
        overwrite : bool, optional
            Is it safe to overwrite the existing file
        indent : str, optional
            The indentation to use when writing variable entries
        """
        if (output is not None):
            if (os.path.isfile(output) and (not overwrite)):
                raise ValueError("file = {} already exists and overwrite=False".format(output))
        else:
            output = self.filename

        if (self.verbose):
            print("Writing input file to: {}".format(output))
        with open(output, "w") as mf:
            for nml in self.namelists.keys():
                self.namelists[nml].write(mf, indent=indent, verbose=False)
                mf.write("\n")

    def read(self):
        """
        Read the input file and parse the namelist information
        """
        store_entry = False
        name = None

        if (self.verbose):
            print("Reading input file from: {}".format(self.filename))
        with open(self.filename, "r") as mf:
            for Line in mf:
                if (Line.strip() == ""): continue # skip empty lines and comments
                if (Line.lstrip().startswith("!")): continue

                line = Line.lstrip().lower()

                # strip trailing comments
                if ("!" in line):
                    ind = line.find("!")
                    line = line[:ind]

                line = line.strip() # strip whitespace

                if (line.startswith("&")): # this is the start of a namelist
                    store_entry = True
                    name = (line[1:]).strip()
                    self.namelists[name] = Namelist(name) # initialize the namelist

                elif (line.startswith("/")): # this is the end of the namelist
                    store_entry = False
                    name = None

                elif (store_entry): # store this variable entry in the proper namelist
                    fields = line.split("=", 1)

                    var_name = fields[0].strip() # extract name and value(s)
                    vals = fields[1].strip()

                    if ("," in vals): # split array entries
                        _vals = vals.split(",")
                        values = [v.strip() for v in _vals]
                    else:
                        values = [vals]

                    var = Variable(var_name, values) # build Variable object and add to namelist
                    self.namelists[name].add_variable(var)

