# ------------------------------------------------------------
# Imports
# ------------------------------------------------------------
from collections import deque
import socket
import time
import logging
import struct
import re
import subprocess
import sys
import json
import select
from threading import Thread, RLock
from can import Bus, Message, CanError
import os
import signal
import numpy as np


LOGNAME = sys.argv[1] if len(sys.argv) > 1 else "PSU"
NODE = sys.argv[2] if len(sys.argv) > 2 else "vcan0"

try:
    pids = subprocess.check_output(["pgrep", "-f", "PowerPi.py"]).decode().split()

    for pid in pids:
        pid = int(pid)
        if pid != os.getpid():
            print(f"Beende alte Instanz {pid}")
            os.kill(pid, signal.SIGTERM)
except:
    pass

# ------------------------------------------------------------
# Logging (mit Datum!)
# ------------------------------------------------------------
log = logging.getLogger("steuerung")
log.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"   # ✅ Datum + Zeit
)

# Console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# File (nur Warning+)
file_handler = logging.FileHandler(f"./uploads/{LOGNAME}.log", mode="a")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

log.addHandler(console_handler)
log.addHandler(file_handler)

# Ping Logger (auch INFO ins File)
log_ping = logging.getLogger("steuerung.ping")
log_ping.setLevel(logging.INFO)

ping_file_handler = logging.FileHandler(f"./uploads/{LOGNAME}.log", mode="a")
ping_file_handler.setLevel(logging.INFO)
ping_file_handler.setFormatter(formatter)

log_ping.addHandler(ping_file_handler)

log.propagate = False
log_ping.propagate = False


# ------------------------------------------------------------
# Ping Helper
# ------------------------------------------------------------
def ping(ip, init = False):
    cmd = ["ping", "-c", "1", "-W", "1", ip]
    cmdinit = ["ping", "-c", "1", "-W", "0.05", ip]
    if init == False:
        cmdlist = cmd
    else:
        cmdlist = cmdinit 
    try:
        result = subprocess.run(cmdlist, stdout=subprocess.DEVNULL)
        return result.returncode == 0
    except:
        return False


# ------------------------------------------------------------
# Klasse
# ------------------------------------------------------------
class Steuerung:
    def __init__(self):

        # PSU
        self.IP = "192.168.1.20"
        self.PORT = 9221
        self.CHANNEL = 1

        self.SET_VOLTAGE = 28.0
        self.SET_CURRENT = 2.5

        # CAN
        self.CAN_INTERFACE = "socketcan"
        self.CAN_CHANNEL = "vcan0"
        self.BAUDRATE = 250000
        self.CAN_ID_POWER = 0x900

        # Ping Targets
        self.IP_LIST = [self.IP]

        self.psu = None
        self.bus = None
        self.meanerror = False
        self.psu_lock = RLock()

        self.psu_connected = False
        self.psu_alive = False

        self.last_voltage100 = deque(maxlen=100)
        self.last_current100 = deque(maxlen=100)
        self.last_voltage10 = deque(maxlen=10)
        self.last_current10 = deque(maxlen=10)


        self.running = True
        self.connectionrunning = False
        self.mode = "json"
        self.drv = None  # optional


    # --------------------------------------------------------
    # PSU
    # --------------------------------------------------------
    def connect_psu(self):
        try:
            self.connectionrunning = True
            if self.psu:
                self.psu.close()

            self.psu = socket.create_connection(
                (self.IP, self.PORT),
                timeout=1.0
            )

            self.psu_connected = True
            self.psu_alive = True
            log.warning("PSU verbunden")

            self.connectionrunning = False
        except Exception as e:
            self.connectionrunning = False
            self.psu = None
            self.psu_connected = False
            log.warning("PSU nicht erreichbar: %s", e)

    def log_psu_info(self):
        try:
            self.send_psu_cmd("*IDN?")
            idn = self.read_line()

            parts = [p.strip() for p in idn.split(",")]

            if len(parts) >= 4:
                log.warning(
                    "PSU: Hersteller=%s Typ=%s SN=%s Firmware=%s",
                    parts[0], parts[1], parts[2], parts[3]
                )
            else:
                log.warning(f"PSU: {idn}")

        except Exception as e:
            log.warning(f"PSU Identifikation fehlgeschlagen: {e}")

    def send_psu_cmd(self, cmd):
        if not self.psu_connected:
            return
        try:
            self.psu.sendall((cmd + "\r\n").encode("ascii"))
        except:
            self.psu_connected = False


    def read_line(self):
        time.sleep(0.05)
        return self.psu.recv(64).decode().strip()


    def parse_value(self, s):
        try:
            return float(re.findall(r"[-+]?\d*\.\d+|\d+", s)[0])
        except Exception as e:
            log.error(f"Fehler beim parsen der Messwerte {s} --> {e}")
            return 0.0

    def read_psu_values(self):
            try:
                self.send_psu_cmd(f"V{self.CHANNEL}O?")
                voltage = self.parse_value(self.read_line())
                self.send_psu_cmd(f"I{self.CHANNEL}O?")
                current = self.parse_value(self.read_line())


                self.last_voltage100.append(voltage)
                self.last_current100.append(current)
                self.last_voltage10.append(voltage)
                self.last_current10.append(current)

                self.psu_alive = True

                return voltage, current

            except Exception as e:
                log.error("PSU Read Fehler: %s", e)
                self.psu_connected = False
                self.psu_alive = False
                return 0.00, 0.00

        
    # --------------------------------------------------------
    # CAN
    # --------------------------------------------------------
    def send_can(self, voltage, current):
        v = int(max(0, min(0xFFFF, round(voltage * 1000))))
        i = int(max(0, min(0xFFFF, round(current * 1000))))
        data = struct.pack("<HH", v, i)
        try:
            msg = Message(arbitration_id=self.CAN_ID_POWER, data=data, is_extended_id=False)
            self.bus.send(msg)
        except CanError as e:
            log.error("CAN Fehler: %s", e)
            log.error("CAN_Ersatzlog: U=%dmV I=%dmA", v, i)


    # --------------------------------------------------------
    # Replies
    # --------------------------------------------------------
    def reply_ok(self, cmd, extra=None):
        resp = {"status": "ok", "cmd": cmd}
        if extra:
            resp.update(extra)
        print(json.dumps(resp), flush=True)


    def reply_error(self, cmd, msg):
        resp = {"status": "error", "cmd": cmd, "msg": str(msg)}
        print(json.dumps(resp), flush=True)


    # --------------------------------------------------------
    # THREAD Measure
    # --------------------------------------------------------
    def checkque(self):
        def protokoll(name):
            if not self.meanerror:
                log.warning(f"Mittelwert {name} weicht ab → starte Ping")
                self.meanerror = True
                self.last_voltage100.clear()
                self.last_current100.clear()
                self.last_voltage10.clear()
                self.last_current10.clear()

        while self.running:
            try:
                if len(self.last_voltage100) > 98:
                    # minV100 = np.min(self.last_voltage100)
                    # maxV100 = np.max(self.last_voltage100)
                    meanV100 = np.mean(self.last_voltage100)
                    # minV10 = np.min(self.last_voltage10)
                    # maxV10 = np.max(self.last_voltage10)
                    meanV10 = np.mean(self.last_voltage10)

                    # minI100 = np.min(self.last_current100)
                    # maxI100 = np.max(self.last_current100)
                    meanI100 = np.mean(self.last_current100)
                    # minI10 = np.min(self.last_current10)
                    # maxI10 = np.max(self.last_current10)
                    meanI10 = np.mean(self.last_current10)

                    tolmeanV = meanV100 * 0.01
                    tolmeanI = meanI100 * 0.02

                    name = None
                    if meanV10 <= meanV100 - tolmeanV:
                        name = "Voltage"
                        protokoll(name)
                    if meanV10 >= meanV100 + tolmeanV: 
                        name = "Voltage"
                        protokoll(name)
                    if meanI10 <= meanI100 - tolmeanI:
                        name = "Current"
                        protokoll(name)
                    if meanI10 >= meanI100 + tolmeanI: 
                        name = "Current"
                        protokoll(name)
            except Exception as e:
                log.warning(f"Fehler bei Mittelwertsprüfung: {e}")
            time.sleep(0.1)


    def thread_measure(self):
        log.info("Mess-Thread gestartet")
        while self.running:
            try:
                start = time.time()
                if not self.connectionrunning == True:
                    voltage, current = self.read_psu_values()
                    self.send_can(voltage, current)

                time.sleep(max(0.1 - (time.time() - start), 0))
            except:
                self.psu_connected = False
<<<<<<< HEAD:PowerPi.py
=======
                self.psu_alive = False
>>>>>>> 9ad3fef (aufräumen vor umzug nach github):source/PowerPi.py


    # --------------------------------------------------------
    # THREAD Power
    # --------------------------------------------------------
    def thread_power(self):
        log.info("Power-Thread gestartet")

        while self.running:
            if self.psu_connected:
                try:
                    self.send_psu_cmd(f"V{self.CHANNEL} {self.SET_VOLTAGE:.3f}")
                    self.send_psu_cmd(f"I{self.CHANNEL} {self.SET_CURRENT:.3f}")
                    self.send_psu_cmd(f"OP{self.CHANNEL} 1")

                except:
                    self.psu_connected = False
                    self.psu_alive = False

            time.sleep(5)


    # --------------------------------------------------------
    # THREAD Network
    # --------------------------------------------------------
    def thread_network(self):
        log.info("Netzwerk-Thread gestartet")

        while self.running:
            try:
                if not self.psu_connected == True or not self.psu_alive == True or self.meanerror == True:
                    log.warning("PSU Problem erkannt → starte Ping")
                    for ip in self.IP_LIST:
                        ok = ping(ip)
                        if ok:
                            log.info("PING %s -> OK", ip)
                            log_ping.info("PING %s -> OK", ip)
                        else:
                            log.error("PING %s -> FAIL", ip)
                            log_ping.error("PING %s -> FAIL", ip)
                            if ip == self.IP:
                                self.psu_connected = False
                    time.sleep(1)
                    self.meanerror = False
                if self.psu_connected == False:
                    self.connect_psu()
            except Exception as e:
                log.warning(f"Fehler beim Ping: {e}")
            time.sleep(1)


    # --------------------------------------------------------
    # THREAD STDIN
    # --------------------------------------------------------
    def thread_stdin(self):
        log.info("STDIN-Thread gestartet")

        poller = select.poll()
        poller.register(sys.stdin, select.POLLIN)

        while self.running:
            try:
                if poller.poll(100):

                    line = sys.stdin.readline().strip()

                    if self.mode == "json" and "{" in line:
                        cmd = json.loads(line)
                        name = cmd.get("cmd")

                        if name == "power_off":
                            self.send_psu_cmd("OP1 0")
                            self.reply_ok(name)

                        elif name == "power_on":
                            self.send_psu_cmd("OP1 1")
                            self.reply_ok(name)

                        elif name == "status":
                            self.reply_ok(name, {
                                "psu_connected": self.psu_connected,
                                "psu_alive": self.psu_alive,
                                "voltage": self.last_voltage,
                                "current": self.last_current
                            })

                        else:
                            self.reply_error(name, "unknown command")

            except Exception as e:
                log.error("STDIN Fehler: %s", e)

    def init_iplist(self):
        iplist = [self.IP, "datastorage", "10.80.201.254"]
        subnet = "192.168.1."
        log.info(f"Subnet {subnet}1/24 wird gescannt")
        for byte in range(21,256):
            ip = f"{subnet}{str(byte)}"
            if ping(ip, True) == True:
                iplist.append(ip)
                log.info(f"Adresse {ip} gefunden")
            # else:
            #     log.info(f"scanne {ip}")
        return iplist

    # --------------------------------------------------------
    # RUN
    # --------------------------------------------------------
<<<<<<< HEAD:PowerPi.py
    def run(self, NODE = "vcan0", timeout = 30):
=======
    def run(self, NODE = "vcan0", timeout = 10):
>>>>>>> 9ad3fef (aufräumen vor umzug nach github):source/PowerPi.py
        self.CAN_CHANNEL = NODE
        loop = 0
        while not ping(self.IP) and loop <= timeout:
            time.sleep(1)
            if loop >= timeout:
                log.info(f"{timeout - loop} Verbindung zur PSU abgebrochen\n Messung wird ohne Netzteilsteuerung fortgesetzt")
                log.info(f"PSU_False")
                sys.exit()
            log.info(f"es wird {timeout - loop} Sekunden auf eine Verbindung gewartet\n")
            loop = loop + 1
        self.bus = Bus(interface=self.CAN_INTERFACE,channel=self.CAN_CHANNEL, bitrate=self.BAUDRATE)
        log.info("Supply erkannt, Netzwerk wird nach weiteren Teilnehmern gescannt")
        try:
            self.IP_LIST = self.init_iplist()
            self.connect_psu()
            self.log_psu_info()
            log.info(f"Teilnehmer IP Adressen gefunden: {self.IP_LIST}")
            Thread(target=self.thread_power, daemon=False).start()
            Thread(target=self.thread_measure, daemon=False).start()
            Thread(target=self.thread_network, daemon=False).start()
            Thread(target=self.thread_stdin, daemon=False).start()
            Thread(target=self.checkque, daemon=False).start()
            console_handler.setLevel(logging.INFO) # Wichtig! Wenn das Script mit subprocess aufgerufen wird, muss das logging in die Standardausgabe stdout deaktiviert werden, Grund Buffweroverflow 
            log.info("Verbindung hergestellt, logging läuft")
            file_handler.setLevel(logging.WARNING)
            ping_file_handler.setLevel(logging.INFO)
            log.info(f"PSU_True")
            log.removeHandler(console_handler)
            while True:
                time.sleep(1)
        except:
            self.running = False
            if self.psu:
                self.psu.close()
            if self.bus:
                self.bus.shutdown()
            log.error("Beendet")
            


# ------------------------------------------------------------
# START
# ------------------------------------------------------------
if __name__ == "__main__":
    print("START")
    ok = Steuerung().run(NODE)
    print(f"RUN RETURNED: {ok}")

