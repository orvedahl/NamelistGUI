"""
Class to read/write/modify Rayleigh output quantities.

If run directly, this module will parse the Diagnostics_Base.F90 file for all available
quantity codes and then render each LaTeX formula as a separate PNG image. The default
location to search for the Diagnostics_Base.F90 is

    <rayleigh_dir>/src/Diagnostics

where <rayleigh_dir> is specified in the defaults.py file. To directly specify the path
with no appended entries, specify the "diagnostics_dir" entry in defaults.py.

Usage:
    diagnostic_outputs.py [options]

Options:
    --overwrite  Overwrite existing files
"""
from __future__ import print_function
import matplotlib
import matplotlib.pyplot as plt
import defaults
import os

plt.rc('text', usetex=True)
plt.rc('text.latex', preamble=r'\usepackage{amsmath}')

class ProgressBar():
    """
    Print a progress bar to the terminal

    Attributes
    ----------
    total : int
        The total number of iterations to be included
    prefix : str
        What text appears before progress bar
    suffix : str
        What text appears after progress bar
    decimals : int
        How many decimals to display in the percent complete
    length : int
        How many characters are in the progress bar
    fill : str
        What character to fill the bar

    Example:
        P = ProgressBar(256, prefix="Progress:", suffix="Complete", length=50)
        P(0)
        for i in range(256):
            ....
            P(i+1)

    Produces Output:
        Progress: |######################################------| 90.0% Complete
    """
    def __init__(self, total, prefix='\tProgress:', suffix='Complete',
                 decimals=1, length=50, fill='#'):
        """
        Args
        ----
        total : int
            The total number of iterations to be included
        prefix : str, optional
            What text appears before progress bar
        suffix : str, optional
            What text appears after progress bar
        decimals : int, optional
            How many decimals to display in the percent complete
        length : int, optional
            How many characters are in the progress bar
        fill : str, optional
            What character to fill the bar
        """
        self.total = total
        self.prefix = prefix
        self.suffix = suffix
        self.decimals = decimals
        self.length = length
        self.fill = fill

        if (total <= 0):
            e = "\nERROR: length of progress bar must be positive, length = {}".format(total)
            raise ValueError(e)

    def __call__(self, itr):
        percent = ("{0:." + str(self.decimals) + "f}").format(100 * (itr / float(self.total)))
        filledLength = int(self.length * itr // self.total)
        bar = self.fill * filledLength + '-' * (self.length - filledLength)

        # print the progress bar
        print('\r{} |{}| {}% {}'.format(self.prefix, bar, percent, self.suffix), end='')

        # print new line on completion
        if (itr == self.total):
            print()

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
    entry = line.split(sep)[1].strip()

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
    tex : str
        The LaTeX formula, including "$" symbols
    """

    def __init__(self, code, name, tex=None):
        """
        Args
        ----
        code : int
            The quantity code
        name : str
            The variable name
        tex : str, optional
            The LaTeX formula, including "$" symbols
        """
        self.code = code
        self.name = name.lower()
        self.tex = tex

class OutputQuantities:
    """
    A collection of Rayleigh output quantities found by parsing Diagnostic_Base.F90

    Attributes
    ----------
    quantities : list of Quantity objects
        The available quantities
    diagnostic_types : dict
        The available quantities sorted by diagnostic type. The keys are the available
        diagnostic types, e.g., "Velocity_Field", "Energies", etc. The value is a list of
        Quantity objects associated with this type.
    """

    def __init__(self, rayleigh_dir, default_location=True):
        """
        Args
        ----
        rayleigh_dir : str
            Path to the top of the Rayleigh source tree
        default_location : bool, optional
            If True, the search location will be rayleigh_dir/src/Diagnostics/. If False,
            the search location is just rayleigh_dir/
        """
        self.rayleigh_dir = os.path.abspath(rayleigh_dir)
        if (default_location):
            self.diag_dir = os.path.join(self.rayleigh_dir, "src", "Diagnostics")
        else:
            self.diag_dir = self.rayleigh_dir
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
                    inc_file = Line.split("'")[1] # extract the included filename
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

            # get diagnostic type based on filename, strip off ".F90": /path/Diagnostics_<type>.F90
            diag_type = (os.path.basename(f).split("_", 1)[1])[:-4]

            # allocate space
            if (diag_type not in self.diagnostic_types.keys()):
                self.diagnostic_types[diag_type] = []

            # get names already associated with this diagnostic type
            qnames = [x.name for x in self.diagnostic_types[diag_type]]

            for q in diag_quants: # loop over found quantities
                if (q not in quantity_names):
                    #print("ERROR: could not map variable name = {}".format(q))
                    continue

                if (q in qnames): continue # already added

                ind = quantity_names.index(q) # store quantity
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

def render_tex(qcode, formula, image_path, overwrite=False):
    """write quantity formulas to PNG images"""

    fname = os.path.join(image_path, "{}.png".format(qcode)) # build filename and check existence
    if (os.path.isfile(fname) and (not overwrite)):
        print("Skip LaTeX Render: file exists and overwrite=False, file = {}".format(fname))
        return

    if (not os.path.exists(image_path)): # make path if it doesn't exist
        os.mkdir(image_path)

    # get figure parameters
    dpi = 100
    w = defaults.tex_width*defaults.tex_padding/dpi
    h = defaults.tex_height*defaults.tex_padding/dpi

    # build figure object
    fig = plt.figure(figsize=(w,h), clear=True, dpi=dpi)

    # draw the text
    fig.text(0.05, 0.25, formula, fontsize=defaults.tex_fontsize)

    # save the image
    plt.savefig(fname) #, bbox_inches='tight')

    # close figure and free it from memory
    plt.close()

if __name__ == "__main__":
    from docopt import docopt
    args = docopt(__doc__)

    overwrite = args['--overwrite']
    if (overwrite is None):
        overwrite = defaults.tex_overwrite

    if (defaults.diagnostics_dir is None):
        search_path = defaults.rayleigh_dir
        default_loc = True
    else:
        search_path = defaults.diagnostics_dir
        default_loc = False

    image_path = defaults.quantity_code_image_path

    outputQ = OutputQuantities(search_path, default_location=default_loc)
    offsets = list(outputQ.offsets.keys())

    P = ProgressBar(len(outputQ.quantities))

    print("\nBuilding quantity code images ...")
    P(0)
    for i,Q in enumerate(outputQ.quantities):
        if (Q.name in offsets): continue
        render_tex(Q.code, Q.tex, image_path, overwrite=overwrite)
        P(i+1)

    print("\nSaved images to: {}\n".format(image_path))

