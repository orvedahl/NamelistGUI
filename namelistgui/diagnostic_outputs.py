"""
Classes to read/write/modify Rayleigh output quantities
"""
from __future__ import print_function
import re
import matplotlib
matplotlib.use('WXAgg')
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.pyparsing import ParseFatalException
import os
from collections import OrderedDict

def _detexify(line):
    """
    Make the non-math-mode LaTeX compile by fixing special characters

    Args
    ----
    line : str
        The line that has special characters that need to be fixed

    Returns
    -------
    repaired : str
        The repaired line
    """
    line = line.replace("{", "\{") # fix old brackets first
    line = line.replace("}", "\}")
    line = line.replace("^", "\^{}") # now add in new brackets
    line = line.replace("_", "\_")
    line = line.replace("<", "$<$")
    line = line.replace(">", "$>$")

    return line

def _ensure_texable(line, sep=":tex:", verbose=True):
    """
    Verify that each line will compile with LaTeX

    Args
    ----
    line : str
        The line containing the contents ".... :tex: .... $formula$ ...."
    sep : str, optional
        The string that separates the LaTeX formula from everything else
    verbose : bool, optional
        Print status information

    Returns
    -------
    repaired : str
        The repaired line
    """
    entry = line.split(sep)[1]

    if (entry.count("$") % 2 == 1):
        entry = entry + "$"
        if (verbose):
            print("...fixed a :tex: line (missing '$') = {}".format(entry))

    # line is "......$math$......" and there ar "_" or "{" in the 1st/2nd part
    if (not (entry.lstrip().startswith("$") and entry.rstrip().endswith("$"))):
        lind = entry.find("$")
        rind = entry.rfind("$")
        first = _detexify(entry[:lind])
        second = _detexify(entry[rind+1:])
        entry = first + entry[lind:rind+1] + second
        if (verbose):
            print("...fixed a :tex: line (special characters) = {}".format(entry))

    return entry

class Quantity:
    """
    A Rayleigh output quantity

    Attributes
    ----------
    code : int
        The quantity code
    name : str
        The variable name
    filename : str
        The filename that calculates this quantity
    """

    def __init__(self, code, name, filename=None, tex=None):
        """
        Args
        ----
        code : int
            The quantity code
        name : str
            The variable name
        filename : str, optional
            The filename that calculates this quantity
        tex : str, optional
            The LaTeX formula, including "$" symbols
        """
        self.code = code
        self.name = name.lower()
        self.filename = filename
        self.tex = tex

class OutputQuantities:
    """
    A collection of Rayleigh output quantities

    Attributes
    ----------
    codes : list of int
        The available quantity codes
    """

    def __init__(self, rayleigh_dir):
        """
        Args
        ----
        rayleigh_dir : str
            Path to the top of the Rayleigh source tree
        """
        self.rayleigh_dir = os.path.abspath(rayleigh_dir)
        self.diag_dir = os.path.join(self.rayleigh_dir, "src", "Diagnostics")
        self.diag_base = os.path.join(self.diag_dir, "Diagnostics_Base.F90")

        # main storage structure
        self.quantities = [] # list of available Quantity objects

        # quantity codes organized by where they are defined
        # key = diagnostic_type, value = collection of Quantity objects
        self.diagnostic_types = {}

        # parsing tools
        self.offsets = {} # key=string name, value=integer value

        # parse the various elements
        self._parse_basefile()
        self._parse_diagnostic_files()

    def _parse_quantity_code(self, name, code):
        """evaluate right hand side of "name = offset + value" entries"""

        if (("off" in name) and ("off" not in code)): # case: "offset = number"
            code = int(code)
            if (name not in self.offsets.keys()):
                self.offsets[name] = code # this is an offset definition, save it

        elif (("off" not in name) and ("off" in code): # case: name = offset + number"
            vals = code.split("+")
            off = self.offsets[vals[0].strip()] # existing offset
            val = int(vals[1].strip())

            code = off + val

        elif (("off" in name) and ("off" in code): # case: offset = offset + number"
            vals = code.split("+")
            off = self.offsets[vals[0].strip()] # get existing offset
            val = int(vals[1].strip())

            code = off + val
            if (name not in self.offsets.keys()):
                self.offsets[name] = code # new offset definition, save it

        else: # case: name = number
            code = int(code)

        return code

    def _parse_line(self, Line):
        """parse a line of the form: Integer, parameter :: variable_name = index (! comments)"""
        line = Line.lower()

        result = None

        # ignrore empty lines and comments
        if (line.lstrip().startswith("!") or (line.strip() == "")): return result

        # vlaid lines include all three
        if (("integer" in line) and ("parameter" in line) and ("=" in line)):
            line = line.strip()

            quant = line.split("::")[1] # everything to right of "::"
            inds = quant.split("!")     # split trailing comments, if any
            quantity = inds[0]          # "name = index" part
            if (len(inds) == 1):
                comment = ''
            else:
                comment = inds[1].strip()

            q = quantity.split("=") # parse out the name and index/code
            name = q[0].strip()
            code = q[1].strip()

            code = self._parse_quantity_code(name, code) # convert code to integer

            # parse out LaTeX, if present
            if (("off" not in name) and (":tex:" in comment)):
                comment = _ensure_texable(comment, verbose=False)

            result = (name, code, comment)

        return result

    def _parse_basefile(self):
        """parse the Diagnostic_Base.F90 file for valid quantity codes"""

        with open(self.diag_base, "r") as f:
            base_lines = f.readlines()

        quantities = []

        for Line in base_lines: # loop over base file
            line = Line.lower()

            if (line.lstrip().startswith("include")): # parse the included file
                if ("'" in line):
                    inc_file = line.split("'")[1] # extract the include filename
                elif ('"' in line):
                    inc_file = line.split('"')[1]

                with open(os.path.join(self.diag_dir, inc_file), "r") as mf: # parse file
                    for l in mf:
                        Q = self._parse_line(l)
                        if (Q is not None): quantities.append(Q)

            else:
                Q = self._parse_line(l)
                if (Q is not None): quantities.append(Q)

        quantities.sort(key=lambda x: x[1]) # sort by quantity code
        for q in quantities:
            Q = Quantity(q[1], q[0], tex=q[2])
            self.quantities.append(Q)

    def _parse_diagnostic_files(self)
        """parse the Diagnostic_<type>.F90 files to find where each quantity is defined"""
        #self.diagnostic_types = {name:[]}

        # find all Diagnostis_....F90 files
        files = os.listdir(self.diag_dir)
        files = [f for f in files if "diagnostics" in f.lower()]
        l_files = [f.lower() for f in files]

        # remove some files
        ignore_files = ["diagnostics_base.f90", "diagnostics_interface.f90"]
        for (x in ignore_files):
            if (x in l_files):
                ind = l_files.index(x)
                del files[ind]

        for f in files:
            with open(f, "r") as mf:
                for Line in mf:
                    line = Line.lower()
                    if (line.startswith("!") or (line.strip() == "")): continue

                    quantities = self._find_quantities(line)

    def _find_quantities(self, line):
        """find all instances of "compute_quantity(Q)" in the line"""
        func_name = "compute_quantity"
        if (func_name not in line): return None

        length = len(func_name)

        quants = []
        indices = [m.start() for m in re.finditer(func_name, line)]
        for ind in indices:
            start = ind + length
            open_paren = line[start:].find("(") # find closing parenthesis
            close_paren = line[start:].find(")") # find closing parenthesis

            var_name = line[open_paren+1:close_paren].strip()

            quants.append(var_name)

        return list(set(quants))

