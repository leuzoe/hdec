#!/usr/bin/env python3

import sys
import os
import re
import copy
import json

import logging
from configparser import ConfigParser
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.append(os.path.dirname(__file__))
from heidelberg import wallbox

description = """
Ein Miniserver für die Übersetzung der Modbus Steuerung für die
Wallbox Heidelberg Energy Control
in die go-e API zur Weiternutzung z.B. in openWB
"""

hostName = "0.0.0.0"
serverPort = 8082
logger = None
# Anzahl Modbus-ID's, die wir anbieten wollen.
# Es werden dann die Geräte 1...num_wbs geöffnet
# Achtung: Der Wert wird noch aus der Config-Datei mit
# hdec.maxclientid überschrieben:
num_wbs = 5
wbs = []

class MyServer(BaseHTTPRequestHandler):
    wb = None
    def do_GET(self):
        self.wb = wbs[0]
        u = re.match(r'/(\d+)/(.+)', self.path)
        if u:
            n = int(u.group(1))
            if(n < 1 or n > num_wbs):
                n = 1
            self.wb = wbs[n - 1]
            self.path = u.group(2)
        else:
            self.wb = wbs[0]
            self.path = self.path[1:]
        
        if re.match(r'status', self.path):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            data = self.wb.status_as_goe()
        elif re.match(r'register', self.path):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            data = json.dumps(self.wb.cregs)
        elif re.match(r'mqtt', self.path):
            res = False
            payload = re.sub(r'mqtt\?payload=(.*)', r'\1', self.path)
            cmd = re.split(r'=', payload)
            if(cmd[0] == "amp" or cmd[0] == "amx"):
                self.wb.set_current_preset(int(cmd[1]))
                res = True
            if(cmd[0] == 'alw'):
                self.wb.allowed(cmd[1] == "0")
                res = True
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            data = '{' + \
                '"success": {}, "payload": "{}"'.format(str(res).lower(),
                                                        payload) + \
            '}'
        else:
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            f = os.path.join(os.path.dirname(__file__), self.path)
            if not(os.path.isfile(f)):
                f = os.path.join(os.path.dirname(__file__), 'index.html')
            with open(f, 'r') as fd:
                data = re.sub(r'<\?hdec ([^\?]+)\?>',
                              self._process_pi, fd.read())

        logger.debug("data: {}".format(data))
        self.end_headers()
        self.wfile.write(bytes(data, 'utf-8'))

    def log_message(self, fmt, *args):
        logger.info(fmt % args)

    def _process_pi(self, m):
        m = "self.wb." + m.group(1)
        return(str(eval(m)))

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    cfg = ConfigParser()
    cfg.read(os.path.join(os.path.dirname(__file__), "config.ini"))
    if cfg["webserver"]:
        hostName = cfg["webserver"]["host"]
        serverPort = int(cfg["webserver"]["port"])

    llevels = {"debu": logging.DEBUG,
               "info": logging.INFO,
               "warn": logging.WARNING,
               "erro": logging.ERROR,
               "crit": logging.CRITICAL}
    wlevel = cfg["logging"]["level"][0:4].lower()
    lfile = "/var/log/heidelberg.log"
    if cfg["logging"]["file"]:
        lfile = cfg["logging"]["file"]
    logging.basicConfig(filename=lfile, level=llevels[wlevel])

    num_wbs = int(cfg["hdec"]["maxclientid"])
    for n in range(num_wbs):
        wb = wallbox(cfg["hdec"]["device"], n + 1)
        wbs.append(wb)
    
    webServer = HTTPServer((hostName, serverPort), MyServer)
    logger.debug("Server gestartet http://%s:%s - Ende mit Ctrl-C" %
                 (hostName, serverPort))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    for n in range(num_wbs):
        wbs[n].set_watchdog_timeout(0)
    webServer.server_close()
    logger.debug("Server stopped.")

