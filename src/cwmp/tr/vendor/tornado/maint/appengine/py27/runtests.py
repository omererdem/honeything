import os

os.chdir("..")
os.system(os.path.dirname(os.path.abspath(__file__)) + '/common/runtests.py')

#../common/runtests.py