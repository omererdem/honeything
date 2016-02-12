import os
from setuptools import setup
#from distutils.core import setup

os.makedirs('/opt/honeything/config')
os.makedirs('/opt/honeything/bin/cwmp')

setup(
    name='HoneyThing',
    version='1.0.0',
    packages=['src', 'src.cwmp.dm', 'src.cwmp.tr', 'src.cwmp.tr.vendor.bup.lib', 'src.cwmp.tr.vendor.bup.lib.bup',
              'src.cwmp.tr.vendor.bup.lib.bup.t', 'src.cwmp.tr.vendor.bup.lib.tornado', 'src.cwmp.tr.vendor.pbkdf2',
              'src.cwmp.tr.vendor.curtain', 'src.cwmp.tr.vendor.tornado.maint.scripts.custom_fixers',
              'src.cwmp.tr.vendor.tornado.tornado', 'src.cwmp.tr.vendor.tornado.tornado.test',
              'src.cwmp.tr.vendor.tornado.tornado.platform', 'src.cwmp.tr.vendor.pynetlinux', 'src.cwmp.platform',
              'src.cwmp.platform.fakecpe', 'src.cwmp.platform.gfmedia', 'src.config', 'src.logger'],
    url='https://github.com/omererdem/honeything',
    license='GNU General  Public License Version 3',
    author='omer erdem',
    description='Honeypot for Internet of TR-069 Things',
    long_description=open('README.md').read(),
    install_requires=[
        "pycurl",
    ],
    include_package_data=True,
    data_files=[
        ('/etc/init.d', ['src/honeything']),
        ('/opt/honeything/config', ['src/config/config.ini']),
        ('/opt/honeything/bin', ['src/HoneyThing.py']),
        ('/opt/honeything/bin/cwmp', ['src/cwmp/cwmpd']),
    ],
)

os.mkdir('/var/log/honeything')
os.mkdir('/opt/honeything/download')
os.mkdir('/opt/honeything/run')
os.mkdir('/opt/honeything/spool')
os.rename('/opt/honeything/bin/HoneyThing.py', '/opt/honeything/bin/honeything')
os.chmod('/etc/init.d/honeything', 0755)
os.chmod('/opt/honeything/bin/honeything', 0755)
os.chmod('/opt/honeything/bin/cwmp/cwmpd', 0755)
os.symlink('/var/log/honeything', '/opt/honeything/spool/log')