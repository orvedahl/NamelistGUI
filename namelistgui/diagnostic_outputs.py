"""
Classes to read/write/modify Rayleigh output quantities
"""
from __future__ import print_function
import os

def substring_indices(line, substr):
    """
    Find all indices where the substring is found in the given line

    Args
    ----
    line : str
        The line to search
    substr : str
        The substring to find

    Returns
    -------
    indices : list of int
        The indices of each match
    """
    indices = []
    n = len(line)
    for i in range(n):
        ind = line.find(substr, i) # find 'substr' in line[i:]

        # ind = -1 for no match
        if (ind >= 0 and (ind not in indices)): # avoid double counting substrings
            indices.append(ind)

    return indices

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

        elif (("off" not in name) and ("off" in code)): # case: name = offset + number"
            vals = code.split("+")
            off = self.offsets[vals[0].strip()] # existing offset
            val = int(vals[1].strip())

            code = off + val

        elif (("off" in name) and ("off" in code)): # case: offset = offset + number"
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

        # ignore empty lines and comments
        if (line.lstrip().startswith("!") or (line.strip() == "")): return result

        # vlaid lines include all three
        if (("integer" in line) and ("parameter" in line) and ("=" in line)):
            line = line.strip()
            Line = Line.strip() # to maintain case sensitivity of comments

            quant = line.split("::")[1] # everything to right of "::"
            inds = quant.split("!")     # split trailing comments, if any
            quantity = inds[0]          # "name = index" part
            if (len(inds) == 1):
                comment = ''
            else:
                _q = Line.split("::")[1] # maintain case sensitivity
                comment = (_q.split("!")[1]).strip()

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
                    inc_file = Line.split("'")[1] # extract the include filename
                elif ('"' in line):
                    inc_file = Line.split('"')[1]

                with open(os.path.join(self.diag_dir, inc_file), "r") as mf: # parse file
                    for l in mf:
                        Q = self._parse_line(l)
                        if (Q is not None): quantities.append(Q)

            else:
                Q = self._parse_line(line)
                if (Q is not None): quantities.append(Q)

        quantities.sort(key=lambda x: x[1]) # sort by quantity code
        for q in quantities:
            Q = Quantity(q[1], q[0], tex=q[2])
            self.quantities.append(Q)

    def _parse_diagnostic_files(self):
        """parse the Diagnostic_<type>.F90 files to find where each quantity is defined"""

        # find all Diagnostis_....F90 files, will not include the base directory
        files = os.listdir(self.diag_dir)
        files = [f for f in files if "diagnostics" in f.lower()]
        l_files = [f.lower() for f in files]

        # remove some files
        ignore_files = ["diagnostics_base.f90", "diagnostics_interface.f90",
                        "diagnostics_adotgradb.f90", "diagnostics_mean_correction.f90"]
        for x in ignore_files:
            if (x in l_files):
                ind = l_files.index(x)
                del files[ind]
                del l_files[ind] # required because we search based on l_files to delete from files

        # add parent directory
        files = [os.path.join(self.diag_dir, f) for f in files]

        quantity_names = [q.name for q in self.quantities] # all available quantity names

        for f in files:
            diag_quants = []
            with open(f, "r") as mf:
                for Line in mf:
                    line = Line.lower()
                    if (line.startswith("!") or (line.strip() == "")): continue

                    quantities = self._find_quantities(line)
                    if (quantities is not None):
                        for q in quantities:
                            if (q not in diag_quants):
                                diag_quants.append(q)

            # ensure unique entries
            diag_quants = list(set(diag_quants))

            # get diagnostic type based on filename, strip of ".F90"
            diag_type = (os.path.basename(f).split("_", 1)[1])[:-4]

            # allocate space
            if (diag_type not in self.diagnostic_types.keys()):
                self.diagnostic_types[diag_type] = []

            # get names associated with this diagnostic type
            qnames = [x.name for x in self.diagnostic_types[diag_type]]

            # store data in main data structure
            for q in diag_quants:
                if (q not in quantity_names):
                    #print("ERROR: could not map variable name = {}".format(q))
                    continue

                if (q in qnames): continue # already added

                ind = quantity_names.index(q)
                Q = self.quantities[ind]
                self.diagnostic_types[diag_type].append(Q)

        # remove empty entries
        keys = list(self.diagnostic_types.keys())
        for k in keys:
            if (len(self.diagnostic_types[k]) == 0):
                del self.diagnostic_types[k]

        # sort entries by quantity code
        for k in self.diagnostic_types.keys():
              self.diagnostic_types[k].sort(key=lambda x: x.code)

    def _find_quantities(self, line):
        """find all instances of "compute_quantity(Q)" in the line"""
        func_name = "compute_quantity"
        if (func_name not in line): return None

        length = len(func_name)

        quants = []
        indices = substring_indices(line, func_name)
        for ind in indices:
            start = ind + length
            open_paren = line[start:].find("(") # find opening parenthesis
            close_paren = line[start:].find(")") # find closing parenthesis

            var_name = line[start+open_paren+1:start+close_paren].strip()

            quants.append(var_name)

        return list(set(quants))

