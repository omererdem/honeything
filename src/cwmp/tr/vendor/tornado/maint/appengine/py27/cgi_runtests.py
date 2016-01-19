import os

os.chdir("..")
os.system(os.path.dirname(os.path.abspath(__file__)) + '/common/cgi_runtests.py')

#../common/cgi_runtests.py