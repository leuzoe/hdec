# hdec -- Ein Python Modul für die Wallbox "Heidelberg Energy Control"
^english version: see below^

Das Ziel dieses Moduls ist es, die Wallbox "Heidelberg Energy Control" über 
deren Modbus zu steuern. Insbesondere geht es darum, ein Lademodul für openWB 
zur Verfügung zu stellen.

Das Modul kann auf dem openWB Raspi installiert werden, die Wallbox wird über
einen billigen RS485/USB Adapter angeschlossen, einige wenige 
Konfigurationsschritte werden durchlaufen und dann kann die "Energy Control" 
als Ladepunkt in openWB genutzt werden.

Das Prinzip des Moduls ist - grob gesprochen - das Folgende:
- mit der Python Library "heidelberg" kann die Wallbox über deren Modbus 
gesteuert werden
- es wird ein einfacher Webserver gestartet
- darüber wird ein Interface wie bei der "Go-e" Wallbox zur Verfügung gestellt
- dann kann überall dort, wo openWB einen "Go-e" Ladepunkt zur Verfügung stellt,
die "Heidelberg verwendet werden
- in der Tat sollte es möglich sein, mehrere "Heidelberg" Wallboxen anzuschließen (was aber aktuell noch ungetestet ist)
- als Ausgabe zur Kontrolle durch den menschlichen Nutzer wird eine sehr 
einfache Status-Anzeige angeboten.

## zu Beachten
Diese Software wird "so wie sie ist" zur Verfügung gestellt. Ob sie was tut,
ob sie das Richtige oder das Erwartete tut, kann nicht garantiert werden.
Insbesondere wird keine Garantie abgegeben, dass die Hardware überlebt.

## Bilder
So sehen typischerweise die RS485/USB Adapter aus, mit denen das Modul 
ausgetestet wurde:

<p align="center"> 
  <img src="images/rs485usb.jpg"> 
</p>

## Installation
### Voraussetzungen
Die Python Library `minimalmodbus` muss installiert sein. Geprüft werden kann
das z.B. mittels  
`echo "import minimalmodbus;print('Ok')" | python3`  
Kommt hier kein "Ok", dann schaue man auf der entsprechenden
[Projektseite](https://pypi.org/project/minimalmodbus/), wie
die Installation erfolgt.

Außerdem wird davon ausgegangen, dass wenigestens eine "Heidelberg Energy 
Control" Wallbox angeschlossen ist, dass deren RS-485/Modbus Verkabelung ok 
ist und dass deren Modbus ID(s) bekannt sind. Bitte nicht vergessen, den 
RS-485/Modbus auf der letzten Box korrekt zu terminieren, wie das in der
Anleitung zur Box beschrieben ist. Die Box muss als "follower" konfiguriert
werden, "leader" ist dann der Raspi.

### Das Modul einrichten
```
cd /tmp
git clone https://github.com/leuzoe/hdec
cd /var/www
sudo mkdir hdec
sudo chown pi hdec
cd hdec
cp -ra /tmp/hdec/src/* .

cd /etc/systemd/system
sudo cp /tmp/hdec/service/hdec.service .
sudo systemctl enable hdec
sudo service hdec start
```

### Konfiguration
Unter `/var/www/hdec/config.ini` können im Bedarfsfall die Parameter des Moduls
angepasst werden, falls das benötigt wird:

- der Standard USB Port des RS485/USB Adapters ist `/dev/ttyUSB0`
- das Standard Log liegt auf der openWB Ramdisk
- der `host` für den eingebauten Webserver steht auf `0.0.0.0`, sodass er auf
allen Netzwerk-Interfaces erreichbar ist. Will man ihn nur unter `localhost`
erreichbar machen, stellt man dies mit `host=127.0.0.1` ein
- `maxclientid` ist die höchste Modbus ID, die angesprochen wird: das Modul
versucht dann alle Boxen von ID 1 bis zur `maxclientid` erreichbar zu machen.

Sollte an der Konfiguration etwas geändert werden, muss der hdec.service neu
gestartet werden:  
`sudo service hdec restart`

### Überprüfen
Surfe die Seite `http://your_raspi:8182/` an.

Wenn man die Website `Kurze Hinweise ...` sieht, sollte das schon mal erledigt 
sein.

Unter `http://your_raspi:8182/1/variables.html` werden ein paar Variable der
Box **mit der ID 1** angezeigt. Sollte es sich bei der Box um die ID 5 handeln,
wird entsprechend `http://your_raspi:8182/5/variables.html` aufgerufen.

### Prüfen im Fehlerfall
- ist der Modbus ordentlich terminiert?
- ist die Modbus Verkabelung ok? Es kommt auf die richtige Polung der Kabel an!
- sind die Modbus Client ID(s) der Box(en) ok?
- Unter `/var/www/html/openWB/ramdisk/hdec.miniserver.log` (oder was auch
immer in `config.ini` fürs Log eingestellt ist) sieht man ggf. weitere Hinweise
auf mögliche Fehler


### openWB Integration
Als erstes fügt man so viele "Go-e" Ladepunkte hinzu, wie man Heidelbergs hat.
Im openWB Einstellungsmenü gibt man diesen dann einfach zu identifizierende
Dummy-IP-Adressen, z.B. 9.9.9.1, 9.9.9.2 usw. Diese openWB Konfiguration wird
gesichert.

Während diese Anleitung geschrieben wird, besteht in der openWB 
Web-Konfiguration keine Möglichkeit, den IP-Adressen der Ladepunkte Ports
oder Pfade auf dem Webserver mitzugeben. Daher muss man
 `/var/www/html/openWB/openwb.conf` manuell editieren:  
9.9.9.1 wird geändert in `127.0.0.1:8182/1` (für die Box mit der Modbus ID 1),  
9.9.9.2 wird geändert in `127.0.0.1:8182/2` (für die Box mit der Modbus ID 2)  
und so weiter.

Auf der Status Seite von openWB sollte nun die erfolgreiche Integration zu
sehen sein. Und dann natürlich auch, wenn man sein Auto zum Laden anschließt.






# hdec -- Python module for the "Heidelberg Energy Control" Wallbox 

This python module aims at controlling the "Heidelberg Energy Control" Wallbox 
via its Modbus interface. A special goal is providing a module for the 
openWB software.

You may install this python module on your openWB Raspi, connect your 
Heidelberg via a cheap RS485/USB adapter, apply some configuration and then use 
the Wallbox as charging point in openWB.

The concept of this module, in principle, is as follows:
- use the python lib `heidelberg` controlling the wallbox by its Modbus interface
- start a minimal webserver 
- provide a "Go-e"-like interface
- use it as openWB charging point(s) (yes, it's untested but reasonable that more than one box can be controlled)
- as interface for humans, this module simply shows a status display 

## Caveats
This software is provided "as is". There is no guarantee that it works as 
expected. There is, in particular, no guarantee that all hardware survives
use of this software.

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

It is assumed that you already have at least one Heidelberg Energy Control Box
installed, that RS-485/Modbus wiring is ok and that you know the Modbus ID(s). 
Don't forget to terminate the RS-485/Modbus on the last box (see manual). The
box must be configured to be a "follower". Modbus "leader" is your raspi.

### Install the module
```
cd /tmp
git clone https://github.com/leuzoe/hdec
cd /var/www
sudo mkdir hdec
sudo chown pi hdec
cd hdec
cp -ra /tmp/hdec/src/* .

cd /etc/systemd/system
sudo cp /tmp/hdec/service/hdec.service .
sudo systemctl enable hdec
sudo service hdec start
```

### Configuration
Have a look at `/var/www/hdec/config.ini` and change parameters, if needed:

- standard USB port of the RS485/USB adapter is `/dev/ttyUSB0`
- standard log file is placed within the openWB ramdisk
- webserver host is set to `0.0.0.0` which makes it accessible on all interfaces, you can restrict this to localhost by setting `host=127.0.0.1`
- `maxclientid` is the maximum Modbus ID addressed: the module makes all boxes accessible, from ID 1 up to `maxclientid`

If you make changes in configuration, you have to restart the hdec.service:  
`sudo service hdec restart`

### Check
Surf to `http://your_raspi:8182/`

If you see a Website `Kurze Hinweise ...`, it seems to work.

Surf to `http://your_raspi:8182/1/variables.html` and you should see some values
of your box **with ID 1**. If client ID of your box is 5, ... ...I think you know what to change...

### Error check
- Modbus terminated?
- Modbus wiring ok? Polarity matters!
- Modbus Client ID of the box(es) ok?
- Have a look at `/var/www/html/openWB/ramdisk/hdec.miniserver.log` (or whatever you set in `config.ini`)


### openWB integration
First, add as many charging points of type "Go-e" as you need, give them dummy IP addresses as 9.9.9.1, 9.9.9.2 or similar. Save this configuration.

As of time of this writing, openWB's web interface does not accept port numbers
of web servers and paths on web servers in its charging point configuration 
page.

Therefore, you have to edit `/var/www/html/openWB/openwb.conf` manually:  
change 9.9.9.1 to `127.0.0.1:8182/1` (for box with Modbus Client ID 1),  
change 9.9.9.2 to `127.0.0.1:8182/2` (for box with Modbus Client ID 2)  
and so on.

To check the successful openWB integration, you may have a look at its status page.


## See also, Credits
- [openWB](https://openwb.de/main/)
- Steffs [wbec](https://github.com/steff393/wbec)
- other HD Energy Control projects on github: [MQTT (homie) Connector](https://github.com/tmsch13/heidelberg-wallbox-connector), [Adapter issues](https://github.com/ioBroker/AdapterRequests/issues/559)
- [go-e API](https://github.com/goecharger/go-eCharger-API-v1/blob/master/go-eCharger%20API%20v1%20DE.md)
- [minimalmodbus](https://pypi.org/project/minimalmodbus/)

Fruitful discussion with openWB user "raspi-buechel" is worth being mentioned.

