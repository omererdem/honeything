# HoneyThing
HoneyThing is a honeypot for internet of TR-069 things. It's designed to act as completely a modem/router that has RomPager embedded web server and supports [TR-069 (CWMP)](https://www.broadband-forum.org/technical/download/TR-069_Amendment-5.pdf) protocol.

Project idea was created by [Ali Ikinci](https://github.com/aikinci) and offered as [Honeynet GSoC](https://honeynet.org/gsoc/ideas#project15) project in 2015.

## Features
Basic features:

 - Emulates some popular vulnerabilities for RomPager as [Misfortune Cookie](http://mis.fortunecook.ie/), [Rom-0](https://ripe69.ripe.net/presentations/61-rom0-vuln.pdf) etc.
 - TR-069 protocol support. Implements mostly used TR-069 CPE commands. e.g: GetRPCMethods, Get/Set ParameterValues, Download...
 - Modem web interface to increase the interaction with attacker.
 - All communication with services (http.log, cwmp.log) and state of honeypot (started/stopped, error etc. to honeything.log) are logged in parsable text format.
 
## Download
Debian and RPM packages will be available soon.

## Installation
There're 2 ways to install HoneyThing:

For all of them, your system must have Python 2.7 (or above) and [PycURL](https://pypi.python.org/pypi/pycurl) package.

 - **Setup Script:** Using setup script requires [python setuptools](https://pypi.python.org/pypi/setuptools) package installed on the system. After downloading and extracting HoneyThing, you can simply go to extracted directory and run; 
> python setup.py install

 - **Pre-Built Packages:** HoneyThing can be installed by using pre-built packages for Ubuntu and CentOS. Packages can be downloaded from [download section](#download) and will be added for any stable release.
 
 For Ubuntu;
> dpkg -i honeything_x.y.z.deb
 
 For CentOS;
> rpm -i honeything_x.y.z.rpm

## Configuration
After installation, some parameters can be changed optional by using [configuration file](https://github.com/omererdem/honeything/blob/master/src/config/config.ini). There're 4 section in config file:

 - **http:** HTTP listen address/port can be edited in this section.
 - **cwmp:** Some TR-069 parameters as listen address/port, ACS url, download directory for *"download"* CPE command, connection request path etc. can be edited.
 - **cpe:** In cpe section, there're lots of variables related to modem/router device like manufacturer, serial number, model name etc. They can be edited to provide device variety in ACS communication.
 - **logging:** Log file paths, log level and some protocol specific parameters can be changed in this section.

## Run
If you installed HoneyThing with setup script or pre-built packages, honeything can be run by using following commands:

> service honeything {start|stop|restart|status}

or
> /etc/init.d/honeything {start|stop|restart|status}

## Documentation
A paper about this project is published (in TURKISH) at International Conference on Information Security and Cryptology [[ISCTurkey 2015]](http://www.iscturkey.org/en). It is accessible online from [here](http://www.iscturkey.org/s/2226/i/HoneyThing_Revised_Last.pdf).

## Credits
The project:

 - Developed by [Ömer Erdem](https://github.com/omererdem)
 - Idea by [Ali Ikinci](https://github.com/aikinci)
 - Advisor [Dr. Mehmet Kara](https://tr.linkedin.com/in/mehmet-kara-b2335947)

and special thanks to [Bâkır Emre](https://github.com/bemre) for taking the first step.


**Note:** This project is also being developed as Istanbul Sehir University master's thesis.