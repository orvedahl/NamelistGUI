"""
User/machine specific default values
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
# include support for LaTeX
#-------
use_tex = True
tex_height = 20   # height of the LaTeX formula window in pixels
tex_width = 50    # width
tex_padding = 1.5 # add extra space to formula window, 1.0=no change

#fontsize to use: xx-small, x-small, small, medium, large, x-large, xx-large, larger
tex_fontsize = 'xx-large'

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
#   %namelist_name
#   <indent>name = value(s)
#   ...
#   /
# the <indent> character is how much white space to include before the "name = value(s)" lines
indent = " "

