import time
import minimalmodbus
import serial
import logging
import json

class wallbox():
    def __init__(self, device, clientid, logger="hdec"):
        """
        creates an object for a Wallbox Instrument 
        "Heidelberg Energy Control"
        on serial device <device> with modbus id <clientid>.
        A logger name "hdec" is used for logging events with this wallbox.
        """
        self.logger = logging.getLogger(logger)
        self.logger.debug("opening device {} and calling "
                          "clientid {}".format(device, clientid))
        self.device = device
        self.clientid = clientid
        self.bus_timeout = 500    # bus timeout in ms
        self.cache_timeout = 3000  # cache timeout in ms
        self.bus_retry_timeout = 120  # bus reconnect timeout in s

        self._bustime = 0
        self._cachetime = 0
        
        self.hw_min_current = 0
        self.hw_max_current = 0
        self.modbusversion = 0
        self.cregs = [0 for i in range(820)]

        self._reInitialize()

    def get_clientid(self):
        return(self.clientid)
            
    def get_state(self):
        """
        get charging state, values:
         2: No vehicle plugged, wallbox doesn't allow charging
         3: No vehicle plugged, wallbox allows charging
         4: Vehicle plugged, no charging request, wallbox doesn't allow charging
         5: Vehicle plugged, no charging request, wallbox allows charging
         6: Vehicle plugged, charging request, wallbox doesn't allow charging
         7: Vehicle plugged, charging request, wallbox allows charging
         8: derating
         9: E
        10: F
        11: Err
        """
        return(self._get_client_register(5))

    def get_temperature(self):
        """
        get internal temperature of the box; unit: [°C]
        """
        return(self._get_client_register(9) / 10)

    def get_locked_state(self):
        """
        get remote lock state of the box
        lock == True: box is locked
        lock == False: box is unlocked
        """
        self._get_client_registers()
        return(not(self.cregs[13] * self.cregs[259]))

    def set_locked_state(self, lock):
        """
        set remote lock state of the box
        lock == True: box get locked
        lock == False: box get unlocked
        """
        l = 0 if lock else 1
        if self._read_hold_register(259) != l:
            self._write_register(259, l)

    def allow(self, state=True):
        """
        fake command: just remember that box state should be "allow charging"
        """
        self._allowed = state

    def is_allowed(self):
        """
        fake command: return box state "allow charging"
        """
        return(self._allowed)

    def get_max_hw_current(self):
        """
        get the maximum charging current the box is switched to. Unit: [A]
        """
        return(self.hw_max_current)

    def get_min_hw_current(self):
        """
        get the minimum charging current the box is switched to. Unit: [A]
        """
        return(self.hw_min_current)

    def get_voltage(self, phase):
        """
        get actual voltage of phase 1/2/3, unit: [V]
        """
        self._get_client_registers()
        pr = 9 + phase
        if(pr < 10 or pr > 12):
            return(None)
        return(self.cregs[pr])
        
    def get_current(self, phase):
        """
        get actual current of phase 1/2/3, unit: [A]
        """
        self._get_client_registers()
        pr = 5 + phase
        if(pr < 6 or pr > 8):
            return(None)
        return(self.cregs[pr] / 10)

    def get_dest_energy(self):
        """
        not yet implemented
        """
        return(0)

    def get_total_energy(self):
        """
        get total energy, unit: [kWh]
        """
        self._get_client_registers()
        r17 = self.cregs[17]
        r18 = self.cregs[18]
        return((r17 * 2**16 + r18) / 1000)

    def get_actual_energy(self):
        """
        get energy since power-on, unit: [kWh]
        """
        self._get_client_registers()
        r15 = self.cregs[15]
        r16 = self.cregs[16]
        return((r15 * 2**16 + r16) / 1000)

    def get_power(self):
        """
        get actual power demanded by car, unit: [kW]
        """
        return(self._get_client_register(14) / 1000)

    def get_current_preset(self):
        """
        get actual current preset of the wallbox, unit: [A]
        """
        return(self._get_client_register(261, force=True) / 10)

    def set_current_preset(self, current=0):
        """
        set current preset of the wallbox, unit: [A]
        valid values: 0; minimum hardware current...maximum hardware current
        """
        if not(self.wb):
            return
        if current < self.hw_min_current:
            current = 0
        if current > self.hw_max_current:
            current = self.hw_max_current
        self._write_register(261, current * 10)
        
    def get_logistic_string(self):
        """
        return the "logistic" string of the wallbox
        """
        self._get_client_registers()
        s = ""
        for i in range(102, 134):
            r = self.cregs[i]
            s += chr(int(r % 2**8))
            s += chr(int(r / 2**8))
        return(s)

    def get_diagnostic_data(self):
        """
        return diagnostic data from the box (register 300..318)
        """
        self._get_client_registers(force=True, all=True)
        return(self.cregs[300:319])
    
    def get_error_memory(self):
        """
        return data from error memory of the box (register 500..819)
        """
        self._get_client_registers(force=True, all=True)
        return(self.cregs[500:820])

    def get_standby_status(self):
        self._get_client_registers()
        if self.modbusversion < 0x108:
            return(-1)
        return(self.cregs[258])

    def get_watchdog_timeout(self):
        """
        get Modbus watchdog timeout in [ms]
        """
        return(self._get_client_registers(257))

    def set_watchdog_timeout(self, timeout):
        """
        set Modbus watchdog timeout
        <timeout> in [ms]
        """
        if(timeout >= 0 and timeout < 65536):
            self._write_register(257, timeout)
    
    def status_as_goe(self):
        """
        build a JSON status message like go-e charger does
        """
        self._get_client_registers(force=True)
        state = self.get_state()
        car = (0, 0, 1, 1, 3, 3, 2, 2, 0, 0, 0, 0)[state]
        err = (0, 0, 0, 0, 0, 0, 0, 0, 0,10, 0, 0)[state]
        pha = 0
        if self.get_voltage(1) > 200:
            pha += 9 	# 0000 1001
        if self.get_voltage(2) > 200:
            pha += 18 	# 0001 0010
        if self.get_voltage(3) > 200:
            pha += 36 	# 0010 0100
        s = {
            "version": "B",
            "car": "{}".format(car),
            "amp": "{}".format(int(self.get_current_preset())),
            "amx": "{}".format(int(self.get_current_preset())),
            "err": "{}".format(err),
            "ast": "0",
            "alw": "{}".format(1 if self.is_allowed() else 0),
            "stp": "0",
            "cbl": "16",
            "tmp": "{}".format(self.get_temperature()),
            "dws": "{}".format(int(self.get_actual_energy() * 360000)),
            "dwo": "{}".format(self.get_dest_energy()),
            "eto": "{:.2f}".format(self.get_total_energy() * 10),
            "uby": "0",
            "ust": "2",
            "adi": "0",
            "al1": "0",
            "al2": "0",
            "al3": "0",
            "al4": "0",
            "al5": "0",
            "fwv": "040",
            "sse": "hdec-{}".format(hex(self.modbusversion)),
            "ama": "{}".format(self.hw_max_current),
            "pha": "{}".format(pha),
            "hdec_mbusid": "{}".format(self.clientid),
            "nrg": (
                "{}".format(self.get_voltage(1)),
                "{}".format(self.get_voltage(2)),
                "{}".format(self.get_voltage(3)),
                "0",
                "{}".format(self.get_current(1) * 10),
                "{}".format(self.get_current(2) * 10),
                "{}".format(self.get_current(3) * 10),
                "{:.1f}".format(self.get_voltage(1) * self.get_current(1) / 100),
                "{:.1f}".format(self.get_voltage(2) * self.get_current(2) / 100),
                "{:.1f}".format(self.get_voltage(3) * self.get_current(3) / 100),
                "0",
                "{:.1f}".format(self.get_power() * 100),
                "1",
                "1",
                "1",
                "1",
                )
            }
        return(json.dumps(s))

    
    #### private
    def _get_client_register(self, num, force=False):
        """
        read a single value from register <num> of the instrument
        if force=True force reading, otherwise take value from cache
        """
        self._get_client_registers(force=force)
        return(self.cregs[num])
    
    def _get_client_registers(self, force=False, all=False):
        """
        read registers from instrument into array cregs
        if all=True read all known registers, otherwise just some interesting
        if force=True force reading registers instead of taking them from cache
        """
        if(time.time() < self._cachetime + self.cache_timeout / 1000
           and not(force)):
            return
        r = self.cregs
        self._upd_registers(r,   1, 18)
        self._upd_registers(r, 100, 34)
        if all:
            self._upd_registers(r, 300,  19)
            self._upd_registers(r, 500, 100)
            self._upd_registers(r, 600, 100)
            self._upd_registers(r, 700, 100)
            self._upd_registers(r, 800,  20)
        # Register 258: Standby Function Control
        # Read/Write is only possible with Modbus Register-Layouts Version 1.0.8
        # In 1.0.7, it can only be written. Trying to read will lead to a timeout.
        # Register 259: Remote Lock
        # Read/Write is only possible with Modbus Register-Layouts Version 1.0.8
        # In 1.0.7, it can only be written. Trying to read will lead to a timeout.
        if r[4] > 0x107:
            self._upd_registers(r, 257, 3, functioncode=3)
        else:
            self._upd_registers(r, 257, 1, functioncode=3)
        self._upd_registers(r, 261, 2, functioncode=3)
        self._cachetime = time.time()
        self.cregs = r
        
    def _upd_registers(self, l, start, num, functioncode=4):
        if(not(self.wb) and not(self._reInitialize())):
            return
        a = self.wb.read_registers(start, num, functioncode)
        for i in range(start, start + num):
            l[i] = a[i - start]

    def _read_register(self, reg, decimals=0):
        if(not(self.wb) and not(self._reInitialize())):
            return(0)
        ret = 0
        try:
            ret = self.wb.read_register(registeraddress=reg,
                                        number_of_decimals=decimals,
                                        functioncode=4,
                                        signed=False)
        except:
            self.wb = None
        return(ret)

    def _read_hold_register(self, reg, decimals=0):
        if(not(self.wb) and not(self._reInitialize())):
            return(0)
        ret = 0
        try:
            ret = self.wb.read_register(registeraddress=reg,
                                        number_of_decimals=decimals,
                                        functioncode=3,
                                        signed=False)
        except:
            self.wb = None
        return(ret)

    def _write_register(self, reg, value, decimals=0):
        if(not(self.wb) and not(self._reInitialize())):
            return
        try:
            self.wb.write_register(reg, value,
                                   number_of_decimals=decimals,
                                   functioncode=6,
                                   signed=False)
        except:
            self.logger.warn("Error writing into register {}".format(reg))
            self.wb = None
        
    def _reInitialize(self):
        if time.time() < self._bustime + self.bus_retry_timeout:
            return

        self._bustime = time.time()
        self._allowed = False
        try:
            self.wb = minimalmodbus.Instrument(self.device, self.clientid)
            self.wb.serial.baudrate = 19200
            self.wb.serial.bytesize = serial.EIGHTBITS
            self.wb.serial.parity   = serial.PARITY_EVEN
            self.wb.serial.stopbits = serial.STOPBITS_ONE
            self.wb.serial.timeout = self.bus_timeout / 1000
            self.wb.debug = False
            self.wb.mode = minimalmodbus.MODE_RTU
            self._get_client_registers()
            if self.cregs[1] != self.clientid:
                self.logger.info("This may or may not be a Heidelberg "
                                 "Energy Control Wallbox - it does not "
                                 "answer in the expected manner. So, be "
                                 "prepared that things may go wrong.")
            self.modbusversion = self.cregs[4]
            if self.cregs[258] != 4:
                self._write_register(258, 4)
            self.set_watchdog_timeout(0)
            self._get_client_registers()
            self.hw_min_current = self.cregs[101]
            self.hw_max_current = self.cregs[100]
            self._allowed = not(self.get_locked_state())
        except:
            self.logger.warn("Could not establish modbus connection "
                             "to id {}; subsequent calls to the device "
                             "will silently fail - at least next {} "
                             "seconds".format(self.clientid,
                                              self.bus_retry_timeout))
            self.wb = None
        return(not(not(self.wb)))
