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

