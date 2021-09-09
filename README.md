# hdec -- Python module for the "Heidelberg Energy Control" Wallbox 

This python module aims at controlling the "Heidelberg Energy Control" Wallbox 
via its Modbus interface. A special goal is providing a module for the 
openWB software.

You may install this python module on your openWB Raspi, connect your 
Heidelberg via a cheap RS485/USB adapter, apply some configuration and then use 
the Wallbox as charging point in openWB.

The concept of this module is as follows:
- use the python module `heidelberg` 
- start a minimal webserver 
- control the wallbox by its modbus interface
- provide a "go-e"-like interface
- use it as openWB charging point(s)
- (yes, it's untested but reasonable that more than one box can be controlled)
- as a human interface, this module simply shows a status display 
  

## Pictures
The type of RS485/USB adapter that I use:

<p align="center"> 
  <img src="images/rs485usb.jpg"> 
</p>

## Installation
### Prerequisites
Check, whether `minimalmodbus` is installed, as with
`echo "import minimalmodbus;print('Ok')" | python3`
If not, have a look at its [project page](https://pypi.org/project/minimalmodbus/).

### Install the module
```
cd /tmp
git clone https://github.com/leuzoe/hdec
cd /var/www
mkdir hdec
cd hdec
cp -ra /tmp/hdec/src/* .

cd /etc/systemd/system
sudo cp /tmp/hdec/service/hdec.service .
sudo systemctl enable hdec
sudo service hdec start
```

### Configuration
Have a look at `/var/www/hdec/config.ini` and change parameters, if needed:

- standard log file is placed within the openWB ramdisk
- webserver host is set to `0.0.0.0` which makes it accessible on all interfaces, you can restrict this to localhost by setting `host=127.0.0.1`
- `maxclientid` is the maximum modbus ID addressed: the module makes all boxes for ID 1 up to `maxclientid` accessible


## See also
- [openWB](https://openwb.de/main/)
- Steffs [wbec](https://github.com/steff393/wbec)
- [go-e API](https://github.com/goecharger/go-eCharger-API-v1/blob/master/go-eCharger%20API%20v1%20DE.md)
- [minimalmodbus](https://pypi.org/project/minimalmodbus/)

## Credits
Fruitful discussion with openWB user "raspi-buechel" is worth being mentioned.

