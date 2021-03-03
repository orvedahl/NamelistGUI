"""
Configure script for GUI: user/machine specific default values
"""
import os

#-------
# access to environment variables
#-------
HOME = os.getenv("HOME")

#-------
# directory where Rayleigh is installed
#-------
rayleigh_dir = os.path.join(HOME, "Programs", "Rayleigh-Fork")

#-------
# set path that contains the Diagnostics_Base.F90 file and all its "include"-ed files
#-------
# If set to None, then <rayleigh_dir>/src/Diagnostics/ will be used. This will not
# parse any files that were included using the "--with-custom=<CUSTOM ROOT>" configure flag.
diagnostics_dir = None
#diagnostics_dir = os.path.join(rayleigh_dir, "src", "build") # include custom outputs, Rayleigh must be compiled first

#-------
# include support for LaTeX
#-------
use_tex = True

# path to find the quantity code PNG files
quantity_code_image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quantity_code_formulas")

# when making new images, is it okay to overwrite existing files
tex_overwrite = True

tex_padding = 1.5 # add extra space to formula window, 1.0=no change
tex_fontsize = 'xx-large' # xx-small, x-small, small, medium, large, x-large, xx-large, larger

# these are not currently used, but could be in the future
tex_height = 20   # height of the LaTeX formula window in pixels
tex_width = 150   # width

#-------
# set default application size
#     if screen size is xs wide and ys tall,
#     then the application will be
#         ysize = y_fact*ys
#         xsize = aspect*ysize
#-------
y_fact = 0.75
aspect_ratio = 1.25

#-------
# namelist formatting
#-------
# a namelist appears as
#   &namelist_name
#   <indent>name = value(s)
#   ...
#   /
# <indent> character is how much white space to include before the "name = value(s)" lines
indent = " "

