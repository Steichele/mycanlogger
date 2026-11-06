#!/usr/bin/python


"""!Canlogger mit zusätzlichem NMT für Canopen  

   The information regarding usage of the script can be found in the readme.md in this folder.
   Information regarding installation and usage of Python 3 and the virtual environment can be found here:
   https://novo-wiki/xwiki/bin/view/Wissens-Db/Entwicklung/Tools/Python/

   Copycw Novotechnik Messwertaufnehmer OHG - All cws Reserved, June 2023
   Unauthorized copying of this file, via any medium is strictly prohibited.
   Proprietary and confidential.
 @file changePara.py
 @section libs Librairies / Modules

    - plotly
    - cantools
    - pprint
    - doctest
    - xmlrpc.client
    - flask
    - can
    - os
    - waitress
    - xml.etree.ElementTree
    - threading
    - datetime
    - time
    - getdata
    - pandas
    - subprocess
    - asammdf
    - psutil
    - tempfile
    - flask_caching
    - gc
    - pandas

 @section authors Author(s)
 - Created by %auteur% on %date%.
 @section Copyright 
   Copyright Novotechnik Messwertaufnehmer OHG - All Rights Reserved, February 2023
   Unauthorized copying of this file, via any medium is strictly prohibited.
   Proprietary and confidential. 
"""





from ast import While
import string
from asammdf.blocks.v4_blocks import COMPRESSION_LEVEL
from canopen.objectdictionary.eds import NoOptionError
import plotly.graph_objects as go
import cantools
from pprint import pprint
from doctest import debug
from xmlrpc.client import boolean
from flask import Flask, render_template, request
from flask import Flask, send_file
from flask import Flask, make_response
from flask_socketio import SocketIO
from flask_caching import Cache
from waitress import serve
import can
import can.interfaces.virtual
from can import Message
import os
import xml.etree.ElementTree as ET
import threading 
from datetime import datetime, timedelta, timezone
import time
from getdata import *
import pandas as pd
import plotly.express as px
import plotly.io as pio
import subprocess
from asammdf import MDF, Signal
import psutil
import tempfile
import gc
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import signal
from threading import Thread
import json
from matplotlib.figure import Figure
import io
import canopen
import MotorDrv
import struct
from cantools.database.can import Message as DbcMessage, Signal
from collections import deque
from flask import jsonify
import serial
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import sys
import copy



__author__ = "Markus Steichele"
__credits__ = ["Markus Steichele"]
__version__ = "0.11.5"
__maintainer__ = "QE "
__email__ = "markus.steichele@novotechnik.de"
__status__ = "WIP"

class CANTracer:
    ''' Loggerclass für blf und mdf Daten '''
    # def __init__(self, bus):
    def __init__(self):
        self.bus = None
        self.notifier = None
        self.log = None
        self.mdffile = None
        self.msg = None
        self.sc = Settingchanger()
        self.mdfflag = False
        self.logmessage = None
        self.header = {}
        self.log_message_list = []
        self.blfFile = None
        self.arithmetikupdater = None
        self.settingchangerupdater = None

    def __del__(self):
        self.cleanup()
    
    def enable_arithmetik(self, listener):
        self.arithmetikupdater = listener
    
    def enable_settingchangerupdater(self, listener):
        self.settingchangerupdater = listener

    def mesg_updater(self, msg):
        '''pipes data from Tracer to mdf writer'''
        self.msg = msg
        self.listupdater(msg)
        if not self.arithmetikupdater == None:
            self.arithmetikupdater(msg)
        if not self.settingchangerupdater == None:
            self.settingchangerupdater(msg)

    def logger(self):
        ''' handling filename and path '''
        if self.blfFile == None or self.blfFile == "":
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            blfFile = f"{timestamp}_bus_log.blf"  # ":" ist in Dateinamen nicht erlaubt
        else:
            blfFile = self.blfFile
        mdffilename = str(blfFile)
        self.startmdfwriter(mdffilename)
        self.startblf(self.blfFile)
        self.dict_to_xml('HDcomment', self.header)
        
    def startmdfwriter(self, filename):
        ''' starts writing mdf file '''
        path = "uploads/"
        self.blfFile = f"{path}{filename}"
        self.sc.blfFile = filename[:-4]
        self.sc.getstatus(f"{filename} wird aufgezeichnet")
        

    def dict_to_xml(self, tag, d):
        ''' converts testdata in xml '''
        """Convert a dictionary to an XML string."""
        elem = ET.Element(tag)
        for key, val in d.items():
            if isinstance(val, dict):
                for sub_key, sub_val in val.items():
                    child = ET.SubElement(elem, 'e')
                    child.set('name', f"{sub_key}")
                    child.text = f"{sub_val}"
            else:
                child = ET.SubElement(elem, key)
                child.text = f"{val}"   
        tree = ET.ElementTree(elem)
        # Nur XML-Struktur als String, ohne Header
        xml_string = ET.tostring(elem, encoding='unicode')
        # Direkt als Text speichern
        with open(self.blfFile[:-4] + '.xml', 'w', encoding='utf-8') as f:
            f.write(xml_string)
        return elem

    
    def listupdater(self, msg):
        self.log_message_list.append(msg)
        self.log_message_list = self.log_message_list[-50:]

    def viewer(self,bus):
        '''update livedata'''
        if not bus == self.bus:
            self.bus = bus
        if self.notifier:
            if self.notifier.running == True:
                self.sc.getstatus("Bitte die Laufende Messung beenden um einen neuen Viever anzulegen")
            else:
                self.notifier.stop()
        else:
            self.notifier = CANNotifier(self.bus, [self.mesg_updater])
            notifierThread = Thread(target=self.notifier.run, daemon=True)
            notifierThread.start()
            self.mdfflag = True


    def flush_cache(self):
        ''' Flushes the cache to ensure it doesn't consume too much RAM '''
        try:
            if self.log:
                self.log.flush()
                print("Cache flushed")
            else:
                print("Logger is not initialized")
        except Exception as e:
            self.logmessage = e

    def startblf(self, filename):
        ''' starts and stop logging '''
        self.log = can.Logger(filename)
        if not self.notifier:
            self.notifier = CANNotifier(self.bus, [self.log, self.mesg_updater])
            notifierThread = Thread(target=self.notifier.run, daemon=True)
            notifierThread.start()
        else:
            if self.notifier:
                self.notifier.listeners.append(self.log)
        print("Logger started and writing to " + str(filename))
        self.header['starttime'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logmessage = "Logger started and writing to " + str(filename)
        self.copy_dbc()
    
    def copy_dbc(self):
        ''' copies the dbc file to the uploads folder '''
                # Quelle und Ziel definieren
        source_path = 'config/config.dbc'
        destination_path = f"{self.blfFile[:-4]}.dbc"
        # Datei im Binärmodus lesen und schreiben
        with open(source_path, 'rb') as src, open(destination_path, 'wb') as dst:
            dst.write(src.read())
        #ready file anlegen
        open(f"{self.blfFile[:-4]}.ready", 'a').close()

 

    def savemdf(self):
        ''' stores signals in mdf file '''
        # self.mdfw.blf_to_mdf4()
        open(f"{self.blfFile[:-4]}.stop", 'a').close()

    def cleanup(self):
        ''' stop logging '''
        try:
            if self.log:
                self.log.stop()
                self.log = None
                print("Logger stopped")
                if self.notifier:
                    self.notifier.stop()
                    self.notifier = None
                    # self.mdfw.stop()
            self.mdfflag = False
            print("Resources cleaned up.")
            self.logmessage = "Resources cleaned up."
            self.blfFile = None
        except Exception as e:
            print(e)
            self.logmessage = e

class CANNotifier():
    ''' recives the cantraffic '''
    def __init__(self, bus, listeners):
        super().__init__()
        self.bus = bus
        self.listeners = listeners
        self.running = True
        self.msg = None
    
    def run(self):
        while self.running == True:
            try: 
                msg = self.bus.recv(timeout=1)  # Achtung als einzigen Reciver verwenden, da sonst bei Verwendung eines zweiten masseges geklaut werden 
                if msg:
                    for listener in self.listeners:
                        listener(msg)
            except Exception as e:
                print(e)
                pass

    def stop(self):
        self.running = False
        # self.join()  # Warten Sie, bis der Thread beendet ist


class uploader:
    def __init__(self):
        self.filename=None
        self.filepath = None
        self.server="pi@datastorage"
        self.remoteDir="/home/pi/incomming"
        self.localDir="/home/pi/mycanlogger/uploads"
        self.uploadFilePath="/home/pi/upload.sh"
        self.rsaUser = "pi"
        self.rsaPW = "pi"
        self.rsaUser, self.rsaServer = self.server.split("@")
        self.scriptpath = "static/autorsa.sh"
        
    
    def upload(self, retry = 0, forceUpload = False):
        uploadflag = False
        while uploadflag == False:
            if not self.filename == None:
                print(f"self.filepath{self.filepath} self.filename{self.filename}")
                if os.path.isfile(f"{self.filepath}{self.filename}.blf") and os.path.getsize(f"{self.filepath}{self.filename}.blf") >= 1:
                    try:
                        result = subprocess.run(["bash", self.uploadFilePath, self.filename, self.server, self.remoteDir, self.localDir], capture_output=True, text=True, check=True )
                        print("✅ Upload erfolgreich:")
                        uploadflag = True
                        return(f"Upload von {self.filename} erfolgreich")
                    except subprocess.CalledProcessError as e:
                        retry = retry + 1
                        if retry > 5:
                            print("❌ Fehler beim Upload:")
                            return(f"{self.filepath}{self.filename}.blf wurde nicht hochgeladen, altes blf wurde nicht ausgewertet")
                    if forceUpload == True:
                        uploadflag = False
                        retry = 0
                else:
                    print("retry upload")
                    retry = retry + 1
                    if retry > 5:
                        return(f"Blf zu klein, {self.filepath}{self.filename}.blf konnte nicht hochgeladen werden")
                time.sleep(5)

    def updateRSA(self):
        subprocess.run(["bash", self.scriptpath, self.rsaServer, self.rsaUser, self.rsaPW], capture_output=True, text=True, check=True)
        return(self.scriptpath, self.rsaServer, self.rsaUser, self.rsaPW)     
    


class signalcalc():
    def __init__(self):
        # self.cmd_to_init(cmds)
        self.dbcfile = "CANsend.dbc"
        self.decodedMessages= {}
        self.calcedSignals = {}
        self.db = None
        self.signalnames = None
        self.canBus = None
        self.halfword = 2147418112 # 32bit signed
        self.kommastellen = 100
        self.cyclic_constants = []
        # self.ops=['+', '-', '*', '/', '(', ')', '%']
        self.ops = ['+', '-', '*', '/', '//', '%', '**','(', ')','and', 'or', 'not','==', '!=', '>', '<', '>=', '<=',]
        self.start_threads()


    def start_threads(self):
        sendthread = Thread(target=self.cyclic_constant_send, daemon=True, args=()) 
        sendthread.start()

    def cmd_to_init(self,cmds):
        self.dbcfile = cmds['self.dbcfile']
        self.canBus = cmds['self.canBus']
        self.db = cmds['self.db']
        

    def formula_from_string(self, inputstring = "DummySignal = FromSignal + SourceSignal * 10"):
        try:
            print(f"inputstring: {inputstring}")
            formulalist = inputstring.split()
            formulalist.pop(1)
            formulaRaw = formulalist 
            self.calcedSignals[formulaRaw[0]]=formulaRaw[1:]
            self.add_new_message_to_dbc(formulaRaw[0],formulaRaw[1:])
        except:
            pass


    def save_dbc(self):
        with open(self.dbcfile, 'w', encoding='latin-1') as f:
            f.write(self.db.as_dbc_string())
        print(f"Datenbank erfolgreich gespeichert unter: {self.dbcfile}")


    def add_new_message_to_dbc(self, signalName, formula):
        try:
            namelist = []
            for sig, msg in self.signalnames:
                namelist.append(sig)
            if not signalName in namelist:
                standard_messages = [msg for msg in self.db.messages]
                max_id = max(msg.frame_id for msg in standard_messages)
                
                
                #Neue ID definieren (nächste freie ID, z.B. +1)
                new_id = max_id + 1
                new_dlc = 4 # Datenlänge (Data Length Code)
                
                print(f"Höchste gefundene ID: {hex(max_id)}")
                print(f"Neue ID wird: {hex(new_id)} ({new_id})")
                new_message_name = f"{signalName}"

                new_signal = Signal(
                    name=signalName,
                    start=0,          # Beginnt bei Bit 0
                    length=32,        # 16 Bit lang
                    byte_order='little_endian', # Big-Endian (@1)
                )
                new_signal.scale = 0.01
                new_signal.offset = -21474181.12              
                new_signal.minimum=0
                new_signal.maximum=50000
                new_signal.unit='units'
                # new_signal.is_signed = True
                
                # Nachricht-Definition
                new_message = DbcMessage(
                    frame_id=new_id,
                    name=new_message_name,
                    length=new_dlc,
                    signals=[new_signal],
                    bus_name='Vector__XXX' # Typischer DBC-Standardname
                )
                
                # Kommentar zur Nachricht hinzufügen (optional, aber empfohlen)
                new_message.comment = f"calcFormula={signalName}:{formula}"

                # Nachricht zur Datenbank hinzufügen
                self.db.messages.append(new_message)
            
                print(f"Nachricht '{new_message_name}' ({hex(new_id)}) mit Signal '{signalName}' hinzugefügt.")
                self.save_dbc()
            else:
                print(f"{signalName} bereits in dbc enthalten")
        except:
            pass


    def load_signal_names(self):
        formulaList = []
        DBC_DATEIPFAD = self.dbcfile
        if not os.path.exists(DBC_DATEIPFAD):
            print(f"FEHLER: DBC-Datei nicht gefunden unter '{DBC_DATEIPFAD}'")
        else:
            try:
                if not self.db:
                    self.db = cantools.database.load_file(DBC_DATEIPFAD)
                    print(f"✅ DBC-Datei '{DBC_DATEIPFAD}' erfolgreich geladen.")
                
                # Liste zur Speicherung aller Signalnamen
                alle_signale = []

                for message in self.db.messages:
                    # print(f"\nNachricht: (ID: {hex(message.frame_id)})")
                    if message.comment is not None:
                        if message.comment.startswith("calcFormula"):
                            dbformula = self.formula_from_dbc(message.comment)
                            formulaList.append(dbformula)         
                    for signal in message.signals:
                        signal_name = (signal.name, message.name)
                        # print(signal_name)
                        alle_signale.append(signal_name)
                        # print(f"  - {signal_name}")

            except Exception as e:
                print(f"Ein Fehler ist beim Laden der DBC-Datei aufgetreten: {e}")
            time.sleep(2)
        self.signalnames = alle_signale
        if len(formulaList) >= 1:
            fire = threading.Thread(target=self.fire_formula_in, args=(formulaList,))
            fire.start()

    def fire_formula_in(self, formulas):
        try:
            for formula in formulas:
                self.formula_from_string(formula)
        except Exception as e:
            print(e)
        

    def formula_from_dbc(self, comment):
        try:
            commentElements = comment.split('=')
            formulaRaw = commentElements[1]
            formula = formulaRaw.replace(':', ' = ').replace(',', ' ').replace('[', '').replace(']', '').replace("'", '')
            return formula
        except:
            return None


    def on_message_receive(self, msg):
        """
        Blockiert und wartet auf eine Nachricht vom CAN-Bus.
        
        :param bus: Die initialisierte python-can Bus-Schnittstelle.
        :return: Das empfangene can.Message Objekt oder None, falls Timeout.
        """
        self.decode_message(msg)
            

    def decode_message(self,msg):
        """
        Dekodiert ein rohes can.Message-Objekt mithilfe der DBC-Datenbank.
        
        :param db: Die geladene cantools.database.Database Instanz.
        :param msg: Das empfangene can.Message Objekt.
        :return: Dictionary der Signalnamen und deren physikalische Werte oder None bei Fehler.
        """
        try:
            # Finde die korrekte Nachrichtendefinition anhand der ID
            message_def = self.db.get_message_by_frame_id(msg.arbitration_id)
            
            # Dekodiere die Rohdaten
            decoded_messages = message_def.decode(msg.data)
            self.decodedMessages.update(decoded_messages)
            self.calc_channel(decoded_messages)
           
        except KeyError:
            print(f"FEHLER: Nachricht mit ID {hex(msg.arbitration_id)} nicht in DBC gefunden.")
            return None
        except Exception as e:
            print(f"FEHLER bei der Dekodierung: {e}")
            return None            

   
    def calc_channel(self, decoded_messages):
        decodedSignalNames = list(decoded_messages.keys())
        try:
            for key, li in self.calcedSignals.items():
                for element in li:
                    formula = self.build_formula(key,li)
                    send_id = self.return_id_by_signalname(key)
                    if element in decodedSignalNames:
                        self.bus_send(send_id, formula)
        except Exception as e:
            print(e)     

    def return_id_by_signalname(self, signalname):
        try:     
            for name, id in self.signalnames:
                if name == signalname:
                    message_definition = self.db.get_message_by_name(id)
                    send_id = message_definition.frame_id  
                    return send_id
        except:
            return None       
    
    def cyclic_constant_send(self):
        while True:
            try:
                for send_id, formula in self.cyclic_constants:
                    if not formula == None:
                        print(f"Zyklischer Sendevorgang für {send_id} mit Wert {formula}")
                        self.bus_send(send_id, formula)
            except Exception as e:
                print(e)
            time.sleep(1)

    def bus_send(self,id, value):
        if not value == None:
            value = self.float64_to_hex(value)
            msg = Message(arbitration_id=id,data=value, is_extended_id=False)
            bus = self.canBus 
            bus.send(msg)

    def float64_to_hex(self, float_value):
        try:
            # WICHTIG: Erzwungen, um sicherzustellen, dass es ein 64-Bit Python float ist
            float_value_64bit = int(float_value) 
            # 1. PACKEN der korrekten Input-Zahl
            # packed = struct.pack('<i', float_value_64bit)
            packed = struct.pack('<I', float_value_64bit)
            # packed = struct.pack('<l', float_value_64bit)
            # packed = struct.pack('<f', float_value)
            byte_list = list(packed)
            byte_data = byte_list
            return byte_data
        
        except Exception as e:
            print(f"Fehler {e} in float_to_hex")
            return b'\xff' # Rückgabe von 0.0 im Fehlerfall
    
    def check_number_flexible(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False
    
    def extend_cyclic_const(self, send_id, element):
        if send_id not in [item[0] for item in self.cyclic_constants]:
            string = element.replace("'", ' ').replace(',', '').replace("[","").replace("]","").replace("'","").replace(" ","").replace('"',"").replace(" ","").replace("  ","")
            if self.check_number_flexible(string) == True:
                value = float(string)
                canvalue = round((value * self.kommastellen) + self.halfword)
                self.cyclic_constants.append((send_id, canvalue))


    def build_formula(self, target, formula_elements):
        offset = self.halfword #/ self.kommastellen
        formula = ""
        send_id = self.return_id_by_signalname(target)
        try:
            for element in formula_elements:
                element.replace("'", ' ').replace(',', '').replace("[","").replace("]","").replace("'","").replace(" ","").replace('"',"").replace(" ","").replace("  ","")
                if not element in self.ops and self.check_number_flexible(element) == False:
                    formula = f"{formula}({self.decodedMessages[element]})"
                else:
                    formula = f"{formula}{element}"
            self.extend_cyclic_const(send_id, formula)
            value = eval(formula)
            canvalue = round((value * self.kommastellen) + offset) 
            return canvalue
        except Exception as e:
            print(e)
            return None
        
    def remove_messages_with_signal(self, signal_to_remove):
        try:
            self.cyclic_constants = []
            messages_to_delete = [
                msg for msg in self.db.messages
                if any(sig.name == signal_to_remove for sig in msg.signals)
            ]

            # Entferne die gefundenen Messages aus der internen Liste
            for msg in messages_to_delete:
                self.db._messages.remove(msg)  # interne Liste direkt bearbeiten

            # Speichern
            self.save_dbc()
            print(f"{len(messages_to_delete)} Messages gelöscht.")
        except Exception as e:
            print(f"Fehler beim Löschen: {e}")



class Settingchanger:
    def __init__(self):
        self.app = Flask(__name__)
        self.cs = None
        self.add_routes()
        self.br = {"250kBaud" : 0 , "500kBaud" : 8} # 0 250, 8 500
        self.cycle =  {"Auswahl" : None, "10ms" : 10 , "25ms" : 25 , "50ms" : 50 , "100ms" : 100, "1000ms" : 1000}  # 0, 1, 2, 3
        self.sa = None # 128 - 247
        self.saold = 128 # 128 - 247
        self.received_message = None
        self.hwinit = {"nicht Eingestellt" : False , "Eingestellt" : True }
        # self.function = {"Auswahl" : None, "Sensor suchen / auslesen" : 0,"Reset Plot" : 1, "Starte nodeid im Opmode " : 3, "Messung Start" : 4,"Messung Stop" : 5, "read SDO" : 6, "Digitemp" : 7, "motor" : 8} motorcontroll testing
        self.function = {
            "Auswahl" : None, "Sensor suchen / auslesen" : 0,"Reset Plot" : 1, "Starte nodeid im Opmode " : 3, "Messung Start" : 4,
            "Messung Stop" : 5, "read SDO" : 6, "Digitemp" : 7, "reboot" : 8, "shutdown" : 9, "read_stepper":10, "Schreibe neue NodeID":11,
            "ResetNodeIDtoDefault":12, "NetworkTimeUpdate":13, "reset206":14, "LinMessung":15
            } 
        self.nodeid = []
        self.init = False
        self.canbus = None
        self.bus =None
        self.configlist = []
        self.cmdlist = []
        self.sendtohwflag = 0
        self.readconfig = False
        self.savefile = True
        self.beschreibung = None
        self.datensatz = None
        self.configfile = None
        self.filelist = []
        self.descrtext = {}
        self.caninterface = None
        self.interfacechannel = None
        self.dlfile = "canconfig.xml" 
        self.log_message = []
        self.sensorid = None
        self.startstoptrace = 0
        self.increment = 80
        self.decodedvalue = {} 
        self.dldir = './uploads/'
        self.configdir = './config/'
        self.dlfile = None
        self.plotgraph = io.BytesIO()
        self.plot_path = "static/plot.png"
        self.plotmesg = None
        self.plotmesglist = []
        self.blfloggerrunning = False
        self.df = pd.DataFrame(columns=['timestamp'])  # Initialisiere DataFrame mit der 'timestamp'-Spalte
        self.cg = None
        self.comments = {}
        self.candb = None
        self.myip = None
        self.status = None
        self.osname = self.get_osname()
        self.myip = self.get_myip()
        self.hostname = self.get_myhostname()
        self.canhw = {"Socketcan" : "socketcan", "VirtualCan" : "VirtualCan" } 
        self.knoten = {"Can0":"can0" }
        self.bitrate = {"Unknown": 0,"5kBaud": 5000, "10kBaud": 10000, "20kBaud": 20000, "33kBaud": 33333, "50kBaud": 50000, "83kBaud": 83333, "100kBaud": 100000, "125kBaud": 125000,
        "250kBaud": 250000, "500kBaud": 500000, "666kBaud": 666666, "800kBaud": 800000, "1000kBaud": 1000000 }
        self.msg = None
        self.dbc_file = 'config/config.dbc'
        self.parse_dbc()
        self.header = None 
        self.tracer = None
        self.freeRam = self.get_free_mem()
        self.diskusage = self.get_free_space()
        self.resample = 1
        self.blfFile = None
        self.server_thread = None
        self.stop_event = threading.Event()
        self.running = False
        self.readBlfFlag = False
        self.signal_data = {}
        self.timestamps = []
        self.log = None
        self.signalsFlag = False
        self.findsensor_running = False
        self.log_message_list = []
        self.decodedvalueList = deque(maxlen=10)
        self.decodedDict = {}
        self.plotLength = 6400
        self.decodedvalue = {}
        self.version=__version__
        self.systime = None
        self.uploader = uploader()
        self.css = "static/style.css"
        self.logo = "logo.png"
        self.acticeDevices = []
        self.serial = None
        self.heartbeat()
        self.arithmetik = None
        # self.plotLock = threading.Lock()
        self.queLock = threading.Lock()
        self.interfacebitrate = 0
        self.plotlylist = []
        self.allowed_ip = None
        self.last_access = 0
        self.plotreading = False
        self.lastSensordict = None

        
    def write_heartbeat(self,data):  
        # In Datei speichern
        with open(f"uploads/{data['hostname']}.json", "w") as f:
            json.dump(data, f, indent=4)    

    def heartbeat(self):
        data = {}
        data['hostname'] = self.hostname
        data['ip'] = self.myip
        data['time'] = datetime.now().isoformat()
        data['meassurement'] = self.blfloggerrunning
        data['blf'] = self.blfFile
        data['ampel'] = "blau"
        self.write_heartbeat(data)
        self.systime = data['time'][:-7]
    
    def get_ntp_update(self):
        try:
            command = "sudo ntpdate novo-ads-1.novo.local"
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error executing command: {e}")
            self.getstatus(f"Fehler {e} beim Abrufen der NTP Time")
            return None

    def get_myip(self):
        try:
            command = "ip addr show eth0 | grep 'inet ' | awk '{print $2}' | cut -d/ -f1 | head -n 1"
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error executing command: {e}")
            self.getstatus(f"Fehler {e} beim Abrufen der IP Adresse")
            self.get_myip()
            return None

    def get_myhostname(self):
        try:
            command = "hostname"
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error executing command: {e}")
            self.getstatus(f"Fehler {e} beim Lesen des Hostnamens")
            return None
        
    def get_osname(self):
        try:
            command = "uname"
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error executing command: {e}")
            self.getstatus(f"Fehler {e} beim Lesen des OS Namens")
            return("Windows")
    
    def get_driver(self):
        if self.osname == "Linux":
            self.canhw = {"Socketcan" : "socketcan" } 
            self.knoten = {"Can0":"can0" }
        else:
            self.canhw = {"Ixxat" : "ixxat" , "Peak" : 'pcan'} 
            self.knoten = {"Channel 0" : "0" }
    
    def clearram(self):
        # gc.collect()
        pass

    def read_blf_and_decode(self):
        try:
            # Lade die DBC-Datei
            db = cantools.database.load_file(self.dbc_file)
        except Exception as e:
            print(f"Error loading DBC file: {e}")
            return None
        try:
            # Erstelle einen CAN-Log-Reader für die BLF-Datei
            log = can.BLFReader(self.blfFile)
        except Exception as e:
            print(f"Error loading BLF file: {e}")
            return None
        # Liste zum Speichern der dekodierten Nachrichten
        decoded_signals = []
        # Lese und dekodiere jede Nachricht
        for msg in log:
            try:
                decoded_msg = db.decode_message(msg.arbitration_id, msg.data)
                decoded_msg['timestamp'] = msg.timestamp
                decoded_signals.append(decoded_msg)
            except Exception as e:
                print(f"Error decoding message: {e}")
                continue
        # Konvertiere die Liste in einen DataFrame
        df = pd.DataFrame(decoded_signals)
        return df
            
    def display_recive_loop(self,msg):
        # t = Thread(target=self.can_logger, args=(msg,))
        # t.start()
        self.can_logger(msg)


    def trace(self):
        ''' Startet den Notifier 
        '''
        # self.log_message = self.tracer.log_message_list[-20:]
        try:
            if not self.tracer:
                self.tracer = CANTracer()
                self.tracer.enable_settingchangerupdater(self.display_recive_loop)
            if self.bus:
                v = Thread(target=self.tracer.viewer, args=(self.bus,), daemon=True)
                v.start()
            # self.makePlotObject()
        except Exception as e:
            self.getstatus(e)
        return render_template('temp.html', cs=self)

    def start_loop(self):
        '''
        Threads
        
        '''
        triggerlist = [20, 40, 60]
        while True:
            try:
                for trigger in triggerlist:
                    if self.increment / trigger == 1:
                        self.clearram()
                    if self.increment / trigger == 2:
                        if not self.blfloggerrunning == False:
                            self.upload_file()
                            if self.tracer:
                                self.tracer.flush_cache()
            except Exception as e:
                print(f"Fehler: {e}")
                self.getstatus(e)
                pass

            try:
                self.heartbeat()
                self.freeRam = self.get_free_mem()
                self.diskusage = self.get_free_space()
                self.listfiles()
            except:
                pass   
            time.sleep(2)
            if self.increment >= 60:
                self.increment = 0
            self.increment = self.increment + 1            
    
    def get_free_space(self):
        disk_usage = psutil.disk_usage('/')
        return(disk_usage.percent)

    def get_free_mem(self):
        mem = psutil.virtual_memory()
        # Freier RAM in Bytes
        free_ram = mem.available
        # Freier RAM in Megabytes
        free_ram_mb = round(free_ram / (1024 * 1024))
        return(free_ram_mb)

    def start_server(self):
        # serve(self.app, host='0.0.0.0', port=8081, threads=30)
        self.app.run( host='0.0.0.0', port=8081, debug=True, use_reloader=False)
        # self.cache = Cache(self.app, config={'CACHE_TYPE': 'simple', 'CACHE_DEFAULT_TIMEOUT': 30})

    def run(self):
        ''' Startet die Webapp '''
        loop_thread = threading.Thread(target=self.start_loop)
        loop_thread.daemon = True  # Damit der Loop-Thread automatisch beendet wird, wenn die Hauptanwendung beendet wird
        loop_thread.start()
        self.server_thread = threading.Thread(target=self.start_server)
        self.server_thread.start()

    def stop_server(self):
        self.stop_event.set()
        os.kill(os.getpid(), signal.SIGINT)
        self.server_thread.join()  # Warte, bis der Server-Thread vollständig beendet ist

    def restart_server(self):
        try:
            self.stop_server()
            # Warte, bis der Server vollständig gestoppt ist
            self.stop_event.clear()
            self.server_thread = threading.Thread(target=self.start_server)
            self.server_thread.start()
        except Exception as e:
            print(f"Error restarting server: {e}")
            self.server_thread = threading.Thread(target=self.start_server)
            self.server_thread.start()


    def limit_to_one_ip(self):

        client_ip = request.remote_addr
        now = time.time()

        # Timeout
        if now - self.last_access > 60:
            self.allowed_ip = None

        # Ersten Client übernehmen
        if self.allowed_ip is None:
            self.allowed_ip = client_ip
            print(f"Aktiver Client: {client_ip}")

        # Andere Clients abweisen
        if client_ip != self.allowed_ip:
            return f"Zugriff gesperrt. Aktiver Client: {self.allowed_ip}", 403

        self.last_access = now


    def add_routes(self):
        ''' legt das Routing der url fest
        '''
        self.app.before_request(self.limit_to_one_ip)
        self.app.add_url_rule('/', view_func=self.index, methods=['GET', 'POST'])
        self.app.add_url_rule('/download', view_func=self.downloadfile, methods=['GET'])
        self.app.add_url_rule('/config', view_func=self.config, methods=['GET', 'POST'])
        self.app.add_url_rule('/writeconfig', view_func=self.writeconfig, methods=['GET', 'POST'])
        self.app.add_url_rule('/trace', view_func=self.trace)
        self.app.add_url_rule('/calc', view_func=self.calc, methods=['POST', 'GET'])
        self.app.add_url_rule('/plot', view_func=self.plot, methods=['POST', 'GET'])
        self.app.add_url_rule('/plotdata', view_func=self.plotdata, methods=['POST', 'GET'])


    def can_logger(self,msg):
        ''' Füllt die Liste der Cannachrichten für das Trace Fenster 
        und Rechnet aus Raw, Value
        '''
        signalcounter = 0
        if msg:
            try:
                decoded = self.candb.decode_message(msg.arbitration_id, msg.data)
                message = self.candb.get_message_by_frame_id(msg.arbitration_id)
                timestamp = msg.timestamp
            except:
                return
    
            try:
                for signal in message.signals:
                    name = signal.name
                    value = decoded.get(name)
                    unit = signal.unit
                    signalcounter += 1
                
                    if value is not None:
                        self.decodedvalue[name] = f"{round(value, 2)} {unit}" if unit else round(value, 2)
                        self.decodedvalueList.append(value)
                        self.appendPlot(timestamp,name,value,unit)
                    self.decodedvalue = dict(sorted(self.decodedvalue.items()))
            except Exception as e:
                self.getstatus(f"Fehler bei der Aktualisierung der Live Daten {e}")


    def appendPlot(self, timestamp, name, value, unit=None):
        if self.plotreading == False:
            try:
                if name not in self.decodedDict:
                    # self.decodedDict[name] = {"unit": unit, "data": deque(maxlen=self.plotLength*100)}
                    self.decodedDict[name] = {"unit": unit, "data": deque(maxlen=self.plotLength*10)}
                else:
                    self.decodedDict[name]["data"].append((timestamp, value))
            except:
                pass

    def getPlotObject(self):
        self.plotreading = True
        decodedDict = self.decodedDict.copy()

        try:
            for signal, sigdata in decodedDict.items():
                new_x = [t for t, v in sigdata["data"]]
                new_y = [v for t, v in sigdata["data"]]
                
                # In der Liste nach dem Eintrag mit dem passenden Namen suchen
                existing_trace = next((trace for trace in self.plotlylist if trace.get("name") == signal), None)
                
                if existing_trace:
                    # Gefunden -> Daten an die existierende Standard-Liste anhängen
                    existing_trace["x"].extend(new_x[-self.plotLength:])
                    existing_trace["y"].extend(new_y[-self.plotLength:])
                    
                    # Begrenzen, um unendliches Wachstum zu verhindern
                    existing_trace["x"] = existing_trace["x"][-self.plotLength:]
                    existing_trace["y"] = existing_trace["y"][-self.plotLength:]
                else:
                    # Nicht gefunden (oder Liste leer) -> Neuen Trace an Liste anhängen
                    self.plotlylist.append({
                        "x": new_x,
                        "y": new_y,
                        "mode": "lines",
                        "name": signal,
                        "unit": sigdata.get("unit")
                    })
        except Exception as e:
            self.getstatus(e)
        self.decodedDict = {}
        self.plotreading = False
        return self.plotlylist

    def makePlotObject(self):
        self.plotreading = True
        try:
            # plotlylist = [{"x": [t for t, v in sigdata["data"]], "y": [v for t, v in sigdata["data"]], "mode": "lines", "name": signal, "unit": sigdata.get("unit") } for signal, sigdata in self.decodedDict.items()]
            plotlylist = [{"x": [], "y": [], "mode": "lines", "name": signal, "unit": sigdata.get("unit") } for signal, sigdata in self.decodedDict.items()]
            self.plotlylist = plotlylist.copy()
        except:
            self.getstatus(f"länge des Plots wird auf {self.plotLength} gekürzt . . ")
        self.plotreading = False
        return None

    def plotdata(self):
        return jsonify(self.getPlotObject())
    
    def plot(self):
        return render_template("index.html", cs=self, plotgraph=self.makePlotObject())

    

    def calc(self):
        ''' Handelt das Arithmetik Modul '''
        if request.method == "POST":
            formelinput = request.form.get('formelinput')
            deleteformel = request.form.get('delete_key')
            init = request.form.get("init")
            if init is not None:
                self.arithmetik = None
                self.init_arithmetik()
            if deleteformel is not None:
                self.arithmetik.calcedSignals.pop(deleteformel, None)
                self.arithmetik.remove_messages_with_signal(deleteformel)
                self.getstatus(f"Formel {deleteformel} gelöscht")
            if formelinput and self.arithmetik is not None:
                self.arithmetik.formula_from_string(formelinput)
                self.arithmetik.load_signal_names()
                self.getstatus(f"Formel {formelinput} hinzugefügt")
                self.parse_dbc()
                try:
                    self.tracer.copy_dbc()
                except:
                    pass
        else:
            self.init_arithmetik()
        # **Wichtig: Immer ein gültiges Response zurückgeben**
        time.sleep(1)
        return render_template('calc.html', cs=self, ari=self.arithmetik)
    
    def init_arithmetik(self):
        self.getstatus("Arithmetik Modul wird initialisiert")
        if self.arithmetik is None and self.tracer is not None and self.canbus is not None:
            cmd = {
                'self.dbcfile': self.dbc_file,
                'self.canBus': self.canbus,
                'self.db': self.candb
            }
            self.arithmetik = signalcalc()
            self.arithmetik.cmd_to_init(cmd)
            self.tracer.enable_arithmetik(self.arithmetik.on_message_receive)
            self.arithmetik.load_signal_names()
        else:
            self.getstatus("Arithmetik Modul geschlossen")
                
    def config(self):
        ''' Handelt die Konfigurationsseite
        '''
        configData = request.form.to_dict()
        if len(configData.keys()) >= 0:
            try: 
                self.uploader.server = configData['user']
                self.uploader.remoteDir = configData['serverdir']
                self.uploader.localDir = configData['loggerdir']
                self.uploader.uploadFilePath = configData['scriptlocation']
                self.colormode = configData['color']
                self.getstatus("Konfigurationsseite aufgerufen: " + str(configData))
                self.saveconfig(configData)   
                self.parse_config()
            except:
                pass
        return render_template('config.html', uploader = self.uploader , cs=self)
    
    def saveconfig(self,configData):
        with open("config/config.json", "w") as f:
            try:
                # json.dump(configData, f, ensure_ascii=False, indent=4)
                json.dump(configData, f)
            except Exception as e:
                print(f"Fehler beim Speichern der Konfiguration: {e}")

    def loadconfig(self):
        try:
            with open("config/config.json", "r") as f:
                configData = json.load(f)
            return configData
        except FileNotFoundError:
            return None
    
    def parse_config(self):
        configData = self.loadconfig()
        if configData:
            try: 
                self.uploader.server = configData['user']
                self.uploader.remoteDir = configData['serverdir']
                self.uploader.localDir = configData['loggerdir']
                self.uploader.uploadFilePath = configData['scriptlocation']
                self.colormode = configData['color']
                self.getstatus("Konfigurationsdatei geladen, die Konfigutaion wurde geändert oder das System wurde gestartet")   
                self.set_colormode(configData)
            except Exception as e:
                self.getstatus(f"Fehler {e} beim parsen der Konfiguration")
            try:
                self.uploader.rsaUser = "pi"
                self.uploader.rsaPW = "pi"
                connection = self.uploader.server.split("@")
                self.uploader.rsaServer = connection[1]
                self.uploader.updateRSA()
            except Exception as e:
                self.getstatus(f"Fehler {e} beim Update der RSA Konfiguration")
        else:
            self.getstatus("Keine Konfigurationsdatei gefunden . . .")
    
    def set_colormode(self, configData):
        try:
            if configData['color'] == "dark":
                self.css = "static/NT-dark-style.css"
                self.logo = "black-logo.png"
            if configData['color'] == "bright":
                self.css = "static/NT-bright-style.css"
                self.logo = "white-logo.png"
            self.getstatus(f"Farbschema auf {configData['color']} gesetzt")
        except Exception as e:
            self.getstatus(f"Fehler beim Setzen des Farbschemas: {e}")

    def listfiles(self):
        try:
            ''' Listet alle Files im Ordner auf '''
            self.filelist = []
            filelist = os.listdir("./uploads")
            for file in filelist:
                if file.endswith((".xml", ".blf", ".dbc", ".ready",".json", ".log", ".mf4", ".pdf",".tex",".aux",".png",".toc")):
                    self.filelist.append(file)
                print(file)
            # Sortieren: zuerst nach Endung, dann nach Name ohne Endung
            self.filelist.sort(key=lambda f: (os.path.splitext(f)[1], os.path.splitext(f)[0]))
        except Exception as e:
            print(f"Fehler beim Auflisten der Dateien: {e}")

    def writeconfig(self):
        ''' Handelt das Dropdown der XML Konfigurationen
        '''
        self.listfiles()
        if request.method == 'POST':
            if 'selection' in request.form:
                filename = str(self.getselection())
                if filename:
                    self.readxml(filename)
                    self.dlfile = filename
                    self.savefile = True
                    self.getstatus(f"Datei {self.dlfile} bereit zum Download")
            if 'writedataset' in request.form:
                self.datasettosensor()
            if 'delete' in request.form:
                self.cleandir()
                print("delete")
        return render_template('index.html', cs=self)
    
    def getselection(self):
        ''' Dateiname des XML zurückgeben
        '''
        file = request.form['file']
        return file

    def readxml(self,filename):
        '''Datensatz XML einlesen
        '''
        print(filename[-4:])
        self.beschreibung = None
        if filename[-4:] == '.xml':
            file = "./uploads/" + filename
            # XML-Datei laden
            if os.path.exists(file):
                self.configfile = filename
                tree = ET.parse(file)
                self.datensatz = tree.getroot()
                self.beschreibung = self.datensatz  # oder setze die Beschreibung hier entsprechend
            else:
                self.beschreibung = None
                self.configfile = None

    def index(self):
        ''' reciving the commands from webinterface'''
        self.signal_data = {}
        self.timestamps = []
        self.log = None
        self.readconfig = False
        self.savefile = False
        self.sendtohwflag = 0
        if 'transmit' in request.form:
            self.read_post_setup()
        if 'file' in request.files:
            self.upload_dbc()
        if 'hwsetup' in request.form:
            self.config_hw()
        if 'write' in request.form:
            self.writeconfig()
        if 'sstrace' in request.form:
            self.sstrace()
        return render_template('index.html', cs=self)
     
    def config_hw(self):
        ''' configure the caninterface '''
        try:    
            hw = request.form['canhw']
            bitrate = request.form['bitrate']
            initlist = [hw, bitrate]
            self.inithw(initlist)
            self.getstatus(f"Treiber {request.form['canhw']} mit der Bitrate {request.form['bitrate']} eingestellt")
        except Exception as e:
            print(e)
            self.getstatus(e)
            pass

    def inithw(self, initlist):
        ''' setup for caninterface '''
        self.caninterface = initlist[0]
        self.interfacebitrate = initlist[1]
        if self.caninterface == "ixxat":
            self.interfacechannel = 0
        if self.caninterface == 'pcan':
            self.interfacechannel = "PCAN_USBBUS1"
        if self.caninterface == 'socketcan':
            self.interfacechannel = "can0"
        if self.caninterface == 'VirtualCan':
            self.interfacechannel = "vcan0"
            self.caninterface = 'socketcan'
            self.getstatus(f"interface{self.interfacechannel}") 

        self.canbus = can.interface.Bus(interface= self.caninterface , channel=self.interfacechannel, bitrate=self.interfacebitrate , err_reporting=True, receive_own_messages=True)
        self.bus = self.canbus
        self.bash_set_can_interface(self.interfacechannel, self.interfacebitrate)
        self.cg = CanOpenGames( self.caninterface, self.interfacechannel, self.interfacebitrate ) 
        self.hwinit = True
        self.init = True

    def bash_set_can_interface(self, interface, bitrate):
        ''' configure the caninterface in Linux '''
        if interface == "vcan0":
            try:
                # Setze das Interface herunter
                subprocess.run(f"sudo ip link set {interface} down", shell=True, check=True, capture_output=True, text=True)
                try:
                    #virtuelles Device anlegen
                    subprocess.run("sudo ip link add dev vcan0 type vcan",  shell=True, check=True, capture_output=True, text=True)
                except:
                    pass
                # Setze das interface
                subprocess.run("sudo ip link set up vcan0" , shell=True, check=True, capture_output=True, text=True)
                
                # Überprüfen, ob die Baudrate richtig gesetzt wurde
                result = subprocess.run(f"ip -details link show {interface}", shell=True, check=True, capture_output=True, text=True)
                print(result.stdout)
                
            except subprocess.CalledProcessError as e:
                print(f"An error occurred while setting the CAN interface: {e.stderr}")
                raise
        else:

            try:
                # Setze das Interface herunter
                subprocess.run(f"sudo ip link set {interface} down", shell=True, check=True, capture_output=True, text=True)
                
                # Setze die Baudrate
                # subprocess.run(f"sudo ip link set {interface} up type can bitrate {bitrate} loopback on", shell=True, check=True, capture_output=True, text=True)
                subprocess.run(f"sudo ip link set {interface} up type can bitrate {bitrate}", shell=True, check=True, capture_output=True, text=True)
                
                # Überprüfen, ob die Baudrate richtig gesetzt wurde
                result = subprocess.run(f"ip -details link show {interface}", shell=True, check=True, capture_output=True, text=True)
                print(result.stdout)
                
            except subprocess.CalledProcessError as e:
                print(f"An error occurred while setting the CAN interface: {e.stderr}")
                raise


    def cleandir(self):
        if self.blfloggerrunning == False:
            for file in self.filelist:
                os.remove(f"{self.dldir}{file}")               
                print(f"remove {file}")
                self.getstatus(f"{file} gelöscht")
            self.listfiles()
        self.getstatus( "Verzeichnis löschen erfolgreich" )
    
    def read_post_setup(self):
            ''' recives the headerdata for mdf '''
            header = {}
            cmddict = {}
            try:
                nodeid_input = request.form['nodeid']
                nodeid_list = nodeid_input.strip('[]').split(',')# Entferne Klammern, falls vorhanden, und teile die Eingabe bei Kommata
                nodeid_list = [int(id.strip()) for id in nodeid_list if id.strip().isdigit()] # Konvertiere die geteilten Strings in eine Liste von Integern
                cmddict = {'nodeid': nodeid_list}
            except:
                pass    
            try:
                cmddict['cycle'] = int(request.form['cycle'])
            except:
                pass
            try:
                cmddict['function'] = int(request.form['function'])
            except:
                pass
            try:
                header['bearbeiter'] = request.form['bearbeiter']
            except:
                pass
            try:
                header['batch'] = request.form['batch']
            except:
                pass
            try:
                header['Material'] = request.form['material']
            except:
                pass
            try:
                header['Messbereich'] = int(request.form['messbereich'])
            except:
                pass
            try:
                header['Einheit'] = request.form['einheit']
            except:
                pass
            try:
                header['produkt'] = request.form['produkt']
            except:
                pass
            try:
                header['test'] = request.form['test']
            except:
                pass
            try:
                header['Auftrag'] = request.form['Auftrag']
            except:
                pass
            try:
                header['hostip'] = self.myip
            except:
                pass
            try:
                header['hostname'] = self.hostname
            except:
                pass
            try:
                cmddict['header'] = header
                self.header = header
                self.tracer.header = header
            except:
                pass   
            try:
                findsensor_running = request.form.get("findsensor_running")
                if findsensor_running == "False":
                    self.findsensor_running = False
            except:
                pass
            try:
                self.blfFile = request.form.get("blfFile") or None
            except Exception as e:
                self.getstatus(f"Filename: {e}")
            if 'function' in cmddict: 
                self.ex(cmddict)

    def sstrace(self):
        ''' starting and stop trace'''
        if self.init == True:
            self.startstoptrace = self.startstoptrace + 1
            if self.startstoptrace == 2:
                self.log_message = []
                self.tracer.log_message_list = []
                self.startstoptrace = 0
                self.decodedvalue = {}
                self.decodedDict = {}
            self.trace()
            
    def downloadfile(self):
        ''' filedownload selection '''
        filename = request.args.get('filename')
        self.dldir ="uploads/"
        self.dlfile = filename
        if self.dlfile[-4:] == '.dbc':
            response = make_response(send_file(self.dldir + self.dlfile, as_attachment=True, download_name=self.dlfile))
            response.headers["Content-Type"] = "application/xml"
            response.headers["Content-Disposition"] = "attachment; filename=" +  str(self.dlfile)
            self.getstatus(str(self.dlfile) + " wurde runter geladen")
        if self.dlfile[-4:] == '.xml':
            response = make_response(send_file(self.dldir + self.dlfile, as_attachment=True, download_name=self.dlfile))
            response.headers["Content-Type"] = "application/xml"
            response.headers["Content-Disposition"] = "attachment; filename=" +  str(self.dlfile)
            self.getstatus(str(self.dlfile) + " wurde runter geladen")
        if self.dlfile[-4:] == '.log':
            response = make_response(send_file(self.dldir + self.dlfile, as_attachment=True, download_name=self.dlfile))
            response.headers["Content-Type"] = "text/plain; charset=utf-8"
            response.headers["Content-Disposition"] = "attachment; filename=" +  str(self.dlfile)
            self.getstatus(str(self.dlfile) + " wurde runter geladen")
        if self.dlfile[-4:] == '.blf':
            response = make_response(send_file(self.dldir + self.dlfile, as_attachment=True, download_name=self.dlfile))
            response.headers["Content-Type"] = "application/octet-stream"
            response.headers["Content-Disposition"] = f'attachment; filename="{self.dlfile}"'
            self.getstatus(str(self.dlfile) + " wurde runter geladen")
        if self.dlfile[-4:] == '.mdf':
            response = make_response(send_file(self.dldir + self.dlfile, as_attachment=True, download_name=self.dlfile))
            response.headers["Content-Type"] = "application/octet-stream"
            response.headers["Content-Disposition"] = f'attachment; filename="{self.dlfile}"'
            self.getstatus(str(self.dlfile) + " wurde runter geladen")
        if self.dlfile[-4:] == '.mf4':
            response = make_response(send_file(self.dldir + self.dlfile, as_attachment=True, download_name=self.dlfile))
            response.headers["Content-Type"] = "application/octet-stream"
            response.headers["Content-Disposition"] = f'attachment; filename="{self.dlfile}"'
            self.getstatus(str(self.dlfile) + " wurde runter geladen")
        if self.dlfile[-4:] == '.pdf':
            response = make_response(send_file(self.dldir + self.dlfile, as_attachment=True, download_name=self.dlfile))
            response.headers["Content-Type"] = "application/pdf"
            response.headers["Content-Disposition"] = f'attachment; filename="{self.dlfile}"'
            self.getstatus(str(self.dlfile) + " wurde runter geladen")
        self.listfiles()
        return response
    
    # def rechw(self,msg):
    #     if self.savefile == True:
    #         self.writexml(msg)
    
    def update_baudrate_list(self):
        baudrates = [250000, 500000, 125000, 10000, 20000, 50000, 800000, 1000000] # Die Reihenfolge der Baudraten ist nach der Häufigkeit bei NT Produkten sortiert 
        for bitrate in self.bitrate.values():
            if not bitrate in baudrates:
                baudrates.append(bitrate)

        if self.interfacebitrate == "0":
            self.getstatus("Keine Baudrate eingestellt, die Suche geht über alle Baudraten.")
        else:
            self.getstatus("Scan wird mit eingestellter Baudrate gestartet.")
            if self.interfacebitrate in baudrates:
                baudrates.remove(self.interfacebitrate)
            baudrates.insert(0, self.interfacebitrate)
        self.getstatus(f"baudrates: {baudrates}")
        return baudrates

    def device_identification(self, node_id = 127):
        device = None
        try:
            if not self.cg.connection:
                self.cg.network_connect(node_id)  # Verbindung zum Netzwerk herstellen
                self.cg.set_preopmode()          # Knoten in Pre-Operational-Modus versetzen
        except Exception as e:
            print(f"Verbindungsfehler: {e}")
            self.cg.network_disconnect()
            return False

        try:
            device = self.cg.node.sdo[0x1018][2].raw
            self.serial = self.cg.node.sdo[0x1018][4].raw
        except Exception as e:
            print(f"Fehler beim Lesen des Identity Objects: {e}")
        finally:
            if self.cg.connection:
                self.cg.network_disconnect()
        if device is not None:
            self.getstatus(f"Device gefunden: {device} bei Nodeid {node_id}")
            print(f"Device gefunden: {device} bei Nodeid {node_id}")
            time.sleep(0.01)
        return device is not None

    def scan_baudrates(self, cmddict):
        ''' scans the baudrates and nodeids for sensors
        '''
        baudrates = self.update_baudrate_list()
        success = None
        successlist = []
        abort = False
        for bitrate in baudrates:
            self.getstatus(f"\n🔍 Teste Baudrate: {bitrate} bit/s")
            self.inithw(['socketcan', bitrate])

            try:
                nodeids = cmddict['nodeid'] if cmddict['nodeid'] else range(128, 0, -1)
                for id in nodeids:
                    self.getstatus(f"Geduld bitte, Nodeid {id}, Bitrate {bitrate} wird gescannt . .")
                    success = self.device_identification(id)
                    if success == True:
                        self.getstatus(f"✅ Sensor gefunden bei Nodeid {id}, Bitrate {bitrate}")
                        successlist.append(id)
                        abort = True
                    if self.findsensor_running == False:
                        abort = True
                        break
                self.acticeDevices = successlist
                if abort:
                    for id in successlist:
                        self.getstatus(f"Starte Auslesen bei Nodeid {id}, Bitrate {bitrate} . .")
                        self.findsensor(id)
                    if len(successlist) == 0:
                        self.getstatus("Auslesen abgeschlossen, Kein Sensor gefunden, Opmode wurde deaktiviert")
                    else:
                        self.getstatus("Auslesen abgeschlossen, Log zum Download hinzugefügt, Opmode wurde deaktiviert")
                    break
            except Exception as e:
                self.getstatus(e) 
        self.findsensor_running = False     

    def write_canopenobject_to_dbc(self, nodeid, xml):
        try:
            ''' writes the canopen object to the dbc file'''
            kommentar = f"{xml['Manufacturer Device Name']}_NODE-ID{xml['Node-ID']}"
            message = self.candb.get_message_by_frame_id(nodeid +384)
            for signal in message.signals:
                    signal.comment = kommentar
                    print(f"Siganl {signal.name} mit Kommentar {signal.comment} aktualisiert.")
            dbc_text = self.candb.as_dbc_string()
            print(dbc_text)
            with open(self.dbc_file, "w", encoding="windows-1252") as f:
                f.write(dbc_text)
            self.parse_dbc()
        except Exception as e:
            print(f"Fehler beim Schreiben der DBC-Datei: {e}")
            self.getstatus(f"Fehler beim Schreiben der DBC-Datei: {e}")

    def findsensor(self, id = None):
        edsDict = self.parse_eds_to_dict()# EDS-Datei in ein Dictionary parsen
        try:
            if self.cg.connection == False:
                self.cg.network_connect(id)  # Verbindung zum Netzwerk herstellen
                self.cg.set_preopmode()  # Knoten in den Pre-Operational-Modus versetzen
        except Exception as e:
            self.getstatus(e)
            self.cg.network_disconnect()
        try:    
            # sensordict = self.cg.readpara(parameter_names)
            sensordict = self.cg.readpara_dict(edsDict)
            if not "Node-ID" in sensordict:
                sensordict['Node-ID'] = id
            self.cg.writexml(sensordict)
            self.lastSensordict = sensordict
            if self.cg.connection == True:
                self.cg.network_disconnect()  # Netzwerkverbindung trennen
        except Exception as e:
            self.getstatus(e)
            if self.cg.connection == True:
                self.cg.network_disconnect()  # Netzwerkverbindung trennen
        self.write_canopenobject_to_dbc(id, sensordict)
        if sensordict: 
            return True
   
    def parse_eds_to_dict(self, eds_path = "config/eds.eds"):
        # Dummy-Netzwerk und Node erstellen
        node = canopen.RemoteNode(1, eds_path)
        param_map = {}

        for index, obj in node.object_dictionary.items():
            # Hauptobjekt
            if hasattr(obj, 'name'):
                param_map[obj.name] = (index, 0)

            # Subobjekte
            if hasattr(obj, 'subindices') and len(obj.subindices) > 1:
                for subidx, subobj in obj.subindices.items():
                    if subidx == 0 and len(obj.subindices) == 1:
                        continue  # Kein echtes Subobjekt
                    if hasattr(subobj, 'name'):
                        param_map[subobj.name] = (index, subidx)
        return param_map

    def firethread(self, searchdict):
        searchthread = Thread(target=self.execute_find, args=(searchdict,))
        searchthread.daemon = True
        searchthread.start()

    def set_nodeID(self, cmddict):
        storepage = [4]
        self.acticeDevices = []
        dummydict = cmddict.copy()
        if len(cmddict['nodeid']) == 4:
            dummydict['nodeid'] = dummydict['nodeid'][:2]#Oldid
            newid = cmddict.get('nodeid', [])[-2:]
        else:
            dummydict['nodeid']=[127,126] #DefaultID Werkssetting
            newid = cmddict.get('nodeid', [])
        try:
            self.firethread(dummydict)
            while self.findsensor_running == True:
                time.sleep(0.2)
            if not newid:
                serial = int(str(self.serial)[-2:]) or 1
                newid = [serial, serial + 60 ]
            self.acticeDevices = list(set(self.acticeDevices))
            if len(newid) == len(self.acticeDevices):
                counter = 0
                for device in self.acticeDevices:
                    self.cg.network_connect(int(device))
                    self.cg.node.sdo['Node-ID'].raw = int(newid[counter])
                    self.cg.store(storepage)
                    self.cg.reboot_device()
                    self.cg.network_disconnect()
                    counter = counter + 1
                    # time.sleep(0.01) wenn ohne pause keine probleme dann entfernen
                dummydict['nodeid']=newid
                self.firethread(dummydict)
            else:
                self.getstatus(f"Abbruch, Zahl der gefundenen NodeIDs{self.acticeDevices} passt nicht zur Eingabe neu {newid}")
        except Exception as e:
            self.getstatus(f"Fehler {e} beim schreiben der NodeID")
    
    def reset_device(self, cmddict, load = 0x64616F6C):
        storepage = [4]
        self.acticeDevices = []
        newid = cmddict.get('nodeid', [])
        dummydict = {}
        dummydict['nodeid'] = newid
        if not newid:
            self.getstatus(f"Bitte NodeIDs angeben, die zurück gesetzt werden sollen")
            return
        try:
            self.firethread(dummydict)
            while self.findsensor_running:
                time.sleep(0.2)
            for device in self.acticeDevices:
                self.cg.network_connect(int(device))
                self.cg.node.sdo['Node-ID'].raw = int(device)
                # 1011:01 = "load"
                # self.cg.node.sdo[0x1011][4].raw = load
                # self.cg.node.sdo[0x1011][1].raw = load
                self.cg.node.sdo['Node-ID'].raw = 127 # bis serienfirmware statt load 1011/04
                self.cg.store(storepage)
                self.cg.reboot_device()
                self.cg.network_disconnect()
                time.sleep(0.5)
            dummydict['nodeid'] = [127,126]
            self.firethread(dummydict)
        except Exception as e:
            self.getstatus(f"Fehler {e} beim Reset auf Werkseinstellungen. newid:{newid}, device:{device}")

    def execute_set_nodeID(self,cmddict):
        self.set_nodeID(cmddict)

    def execute_reset_device(self, cmddict):
        self.reset_device(cmddict)

    def execute_find(self,cmddict):
        self.findsensor_running = True
        self.acticeDevices = []
        self.scan_baudrates(cmddict)        
        self.listfiles()
       
    def execute_plot(self):
        self.df = pd.DataFrame()
        self.getstatus('Plot zurückgesetzt')

    def execute_opmode(self,cmddict):
        if not cmddict['nodeid']:
            cmddict['nodeid'] = self.acticeDevices.copy()
        if not cmddict['cycle']:
            cmddict['cycle'] = "1000"
        try:
            self.getstatus("Schalte das CanNetzwerk in den Opmode")
            self.cg.startup_all(cmddict['nodeid'], cmddict['cycle'])
            self.getstatus("das CanNetzwerk wurde in den Opmode geschaltet")
        except:
            self.getstatus("Opmode nicht möglich. Sendecycle und Baudrate korrekt eingestellt?")

    def execute_startlogger(self, header, fn=None):
        if self.blfloggerrunning == False:
            try:
                self.init == True
                self.startstoptrace = 1
                self.getstatus("Aufzeichnung mit BLF - Logger wird gestartet . .")
                self.header = header
                self.tracer.header = self.header
                if self.blfFile:
                    self.tracer.blfFile = self.blfFile + '.blf'
                if fn:
                      self.tracer.blfFile = fn + '.blf'
                self.tracer.logger()
                self.blfloggerrunning = True
                t = Thread(target=self.upload_file, args=())
                t.start()
                self.listfiles()
                psu = Thread(target=self.run_psu, args=())
                psu.daemon = False
                psu.start()
            except Exception as e:
                self.getstatus(e)
                self.blfloggerrunning = False
        else:
            self.getstatus("Es wird bereits eine Messung aufgezeichnet . .")

    def execute_stoplogger(self):
        def setLoggerrunning():
            self.blfloggerrunning = False
            return

        if self.blfloggerrunning == True:
            try:
                self.startstoptrace = 0
                self.tracer.header = self.header
                self.getstatus("Messung gestopt, MDF wird erstellt...")
                self.log_message = self.tracer.logmessage
                setflag = Thread(target=setLoggerrunning, args=())
                setflag.start()
                # setLoggerrunning()
                self.tracer.cleanup()
                self.getstatus(self.tracer.logmessage)
                self.listfiles()
                self.heartbeat()#enables Autoeinlagern im Datastorage
                t = Thread(target=self.upload_file, args=())
                t.start()
            except Exception as e:
                self.getstatus(e)
                self.blfloggerrunning = True
        else:
            self.getstatus("Es ist keine Messung aktiv . .")

    def execute_read_sdo(self, ids):
        exit = False
        while exit == False:
            for id in ids:
                try:
                    self.cg.read_sdo_values(id)
                except Exception as e:
                    print(f"Fehler beim Lesen der SDO-Werte von ID {id}: {e} {ids}")
                    ids.remove(id)
                    if not ids:
                        exit = True
            time.sleep(60)
    
    def execute_ntp_update(self):
        if not self.blfloggerrunning:
            self.get_ntp_update()
            self.getstatus(f"NTP Update durchgeführt")
        else:
            self.getstatus(f"für ein NTP Update bitte erst die Messung beenden")
        return

    def execute_reset206(self):
        self.reset206()
        return


    def excecute_lin(self, cmddict=None):
        try:
            self.init_lin_environment(cmddict)
            mot = self.init_motor()
            mot.run()
            autostart, filename = self.prepare_measurement(cmddict)
            self.run_measurement(mot)
            self.getstatus(f"Autoauswertung = {autostart}, Filename = {filename}")
            if autostart:
                self.handle_measurement_result(filename, str(mot.kabelabgang))
        except Exception as e:
            self.getstatus(f"Fehler beim Starten des LIN-Tests: {e}")


    def init_lin_environment(self, cmddict):
        # self.getstatus("Caninterface wird initialisiert")
        # self.inithw(["socketcan", "250000"])
        # self.trace()
        time.sleep(1)
        if not cmddict:
            return
        cmddict["cycle"] = 10
        self.execute_find(cmddict)
        while self.findsensor_running:
            time.sleep(1)
        self.startstoptrace = 1
        opmode = Thread(target=self.execute_opmode,args=(cmddict,))
        opmode.start()


    def init_motor(self):
        self.getstatus("Stepper wurde gestartet . . .")
        uart = self.setup_serial()
        stepper = Thread(target=self.read_stepper, args=())
        stepper.start()
        time.sleep(3)
        sensornames = sorted(key for key in self.decodedvalue  if key != "StepperPos" )
        mot = MotorController(uart, self, posname="StepperPos", sensorname=sensornames[0])
        self.getstatus("Motorsteuerung initialisiert . . .")
        return mot


    def prepare_measurement(self, cmddict):
        measure = True
        for key, value in cmddict["header"].items():
            if value == "":
                self.getstatus(
                    f"Header: {key} ist leer, "
                    f"bitte füllen Sie für eine Messung alle Felder aus. "
                    f"Linschrieb wird als Demo gestartet"
                )
                measure = False
                time.sleep(1)
        autostart = False
        filename = None
        if self.serial:
            self.blfFile = f"Sn_{self.serial}"
        if measure:
            self.execute_startlogger(cmddict["header"],self.blfFile)
            autostart = True
            time.sleep(3)
            filename = self.blfFile
        self.getstatus(f"file {filename} wird aufgezeichnet")
        return autostart, filename


    def run_measurement(self, mot):
        mot.messung()
        # motmeasure = Thread(target=mot.messung, daemon=True)
        # motmeasure.start()
        # motmeasure.join()


    def handle_measurement_result(self, filename, kabelabgang):
        while not self.upload_file():
            pass
        self.execute_stoplogger()
        dl = Thread(target=self.download_mf4, args=(filename, kabelabgang))
        dl.start()

    def download_mf4(self,filter_name, kabelabgang):
        dl = False
        url = f"http://datastorage.novo.local:81/view?filter={filter_name}"
        while not dl == True:
            try:
                soup = BeautifulSoup( requests.get(url).text, "html.parser")
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    if ".mf4" in href.lower():
                        mf4_url = urljoin(url, href)
                        self.getstatus(f"Download: {mf4_url}")
                        with requests.get(mf4_url, stream=True) as r:
                            r.raise_for_status()
                            filename = mf4_url.split("/")[-1]
                            filepath = os.path.join("uploads", filename)
                            with open(filepath, "wb") as fp:
                                for chunk in r.iter_content(8192):
                                    fp.write(chunk)
                                dl = True
                self.getstatus(f"Datei: {filename} wurde runtergeladen Auswertung wird gestartet")
                try: 
                    subprocess.run(["python", "linschrieb.py", "-f", filepath, "-e", "-k", kabelabgang],check=True, cwd="/home/pi/mycanlogger")
                    self.getstatus(f"Auswertung {filename} beendet.")
                except Exception as e:
                    self.getstatus(f"Fehler {e} beim Auswerten")
            except:
                self.getstatus(f"Warte auf eingelagertes MF4 {filter_name}")



    def ex(self,cmddict):
        if cmddict['function'] == 0:
            searchthread = Thread(target=self.execute_find, args=(cmddict,))
            searchthread.daemon = True
            searchthread.start()

        if cmddict['function'] == 1:
            self.execute_plot()

        if cmddict['function'] == 3:
            self.execute_opmode(cmddict)

        if cmddict['function'] == 4:
            self.execute_startlogger(cmddict['header'])

        if cmddict['function'] == 5:
            # Thread erstellen
            stoplogger_thread = Thread(target=self.execute_stoplogger)
            # Sicherstellen, dass der Thread kein Daemon-Thread ist
            stoplogger_thread.daemon = False
            # Thread starten
            stoplogger_thread.start()
        
        if cmddict['function'] == 6:
            ids = list(cmddict['nodeid'])
            # Thread erstellen
            sdo_thread = Thread(target=self.execute_read_sdo, args=(ids,))
            # Sicherstellen, dass der Thread kein Daemon-Thread ist
            sdo_thread.daemon = False
            # Thread starten
            sdo_thread.start()
            self.getstatus("Starte SDO wurden gestartet")
        
        if cmddict['function'] == 7:
            # Thread erstellen
            digitemp = Thread(target=self.read_digitemp, args=())
            # Sicherstellen, dass der Thread kein Daemon-Thread ist
            digitemp.daemon = False
            # Thread starten
            digitemp.start()
            self.getstatus("Digitemp wurde gestartet")

        if cmddict['function'] == 8:
            if not self.blfloggerrunning == True:
                self.reboot()
            else:
                self.getstatus(f"reboot nicht möglich, Messung {self.blfFile} wird aufgezeichnet")
        
        if cmddict['function'] == 9:
            if not self.blfloggerrunning == True:
                self.shutdown()
            else:
                self.getstatus(f"shutdown nicht möglich, Messung {self.blfFile} wird aufgezeichnet")
        
        if cmddict['function'] == 10:
            # Thread erstellen
            stepper = Thread(target=self.read_stepper, args=())
            # Sicherstellen, dass der Thread kein Daemon-Thread ist
            stepper.daemon = True
            # Thread starten
            stepper.start()
            self.getstatus("Encoder Stepper wurde gestartet")

        if cmddict['function'] == 11:
            self.set_nodeID(cmddict)
        
        if cmddict['function'] == 12:
            self.execute_reset_device(cmddict)
        
        if cmddict['function'] == 13:
            self.execute_ntp_update()

        if cmddict['function'] == 14:
            self.execute_reset206()

        if cmddict['function'] == 15:
            self.getstatus("LIN - Test gestartet")
            time.sleep(5)
            lin_thread = Thread(target=self.excecute_lin, args=(cmddict,), daemon=True)
            lin_thread.start()
    
        
    def upload_dbc(self):
        file = request.files['file']
        if file.filename == None:
            pass
        else:
            if file.filename.endswith(".dbc"):
                file.save('config/' + 'config.dbc')
                self.parse_dbc()
                self.getstatus( "dbc hochgeladen" )
                if self.blfloggerrunning == True:
                    self.tracer.copy_dbc()
            if file.filename.endswith(".eds"):
                file.save('config/' + 'eds.eds')
                self.getstatus( "eds hochgeladen" )
        return render_template('index.html', cs=self)
    
    def parse_dbc(self):
        try:
            self.candb = cantools.database.load_file(self.dbc_file)
            for message in self.candb.messages:
                for signal in message.signals:
                    self.comments[signal.name] = signal.comment if signal.comment else 'None'
            self.getstatus("das DBC - File wurde geparst . .")
        except:
            self.getstatus("Keine DBC vorhanden")
    
    def setup_serial(self):
        dev_files = os.listdir('/dev')
        ttyUSB = [f"/dev/{file}" for file in dev_files if file.startswith('ttyUSB')]

        if not ttyUSB:
            self.getstatus("Kein ttyUSB-Gerät gefunden.")
            return None

        ttyUSB_device = ttyUSB[0]

        try:
            command = f"stty -F {ttyUSB_device} raw -echo clocal 115200 cs8 -cstopb -parenb"
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            print(f"{ttyUSB_device} wurde initialisiert.")
            return ttyUSB_device
        except subprocess.CalledProcessError as e:
            print(f"Fehler bei Init Serial: {e}")
            return None

    def read_digitemp(self):
        dev = self.setup_serial()
        with open(f"{dev}", 'rb', buffering=0) as ser:
            while True:
                try:
                    line = ser.readline()
                    print(line)
                    decoded = line.decode('utf-8').strip()
                    if not decoded:
                        continue
                    data = json.loads(decoded)
                    self.send_to_can(data['id'],(round(data['temp'] *100 ) + 4000),round(data['humi'] * 100))
                except json.JSONDecodeError as e:
                    print(f"JSON-Fehler: {e} | Zeile: {line}")
                except Exception as e:
                    print(f"Fehler in digitemp: {e}")
    
    def read_stepper(self):
        dev = self.setup_serial()
        HEADER = b"\x12\x34\x56\x78"
        poslist = [0,1,0,0,0]
        pos = 0
        with open("log.log", "a") as log:
            with open(dev, "rb", buffering=0) as ser:
                last = -1
                buf = bytearray()
                while True:
                    try:
                        chunk = ser.read(64)
                        if not chunk:
                            continue
                        buf.extend(chunk)
                        while True:
                            idx1 = buf.find(HEADER)
                            if idx1 < 0:
                                buf = buf[-3:]
                                break
                            idx2 = buf.find(HEADER, idx1 + len(HEADER))
                            if idx2 < 0:
                                break
                            payload = buf[idx1 + len(HEADER):idx2]
                            #
                            # Normales Format:
                            # LOW HIGH
                            #
                            if len(payload) == 2:
                                pos = payload[0] | (payload[1] << 8)             
                            elif len(payload) == 3: # Sonderfall:LOW FILLER HIGH
                                pos = payload[0] | (payload[2] << 8)

                            #     del buf[:idx2]
                            #     continue
                            #
                            # Bekannten Störer ignorieren
                            #
                            if pos == 2573:
                                del buf[:idx2]
                                continue
                            if abs(pos - last) > 10   or min(poslist) == max(poslist):
                                self.send_to_can(100, pos)
                                last = pos
                            poslist.append(int(pos))
                            poslist = poslist[-20:]
                            # if last >= 0 and pos < last:
                            del buf[:idx2]
                    except Exception as e:
                        self.getstatus(f"Fehler {e} beim lesen des Steppers")
        
    def send_to_can(self,id,temp, humi = None):
        tbytes = temp.to_bytes(2,byteorder='little')
        if humi:
            hbytes = humi.to_bytes(2,byteorder='little')
            data = tbytes + hbytes
        else:
            data = tbytes
        msg = can.Message(arbitration_id=id,data=data ,is_extended_id=False)
        self.bus.send(msg)

    def upload_file(self):
        try:
            if self.blfloggerrunning == True:
                self.uploader.filename = self.blfFile
                self.uploader.filepath = self.dldir
                state = self.uploader.upload()
                self.getstatus(state)
                if self.tracer.blfFile == None:
                    self.getstatus(f"Fehler self.tracer.blfFile = {self.tracer.blfFile}, Reparatur wird durchgeführt")
                    self.tracer.blfFile = self.blfFile
                if "erfolgreich" in state:
                    return True
                else:
                    return False
        except Exception as e:
            print(f"Fehler beim Upload: {e}")
            self.getstatus(f"Fehler beim Upload: {e}")
            return False   


    def shutdown(self):
        try:
            command = f"sudo halt"
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            self.getstatus(f"System wird herunter gefahren.")
        except subprocess.CalledProcessError as e:
            self.getstatus(f"Fehler {e} beim shutdown")
            return None
        
    def reboot(self):
        try:
            command = f"sudo reboot"
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            self.getstatus(f"System wird neu gestartet")
        except subprocess.CalledProcessError as e:
            self.getstatus(f"Fehler {e} beim shutdown")
            return None    
        
    def run_psu(self):
        psu_proc = subprocess.Popen(["python", "-u",  "./PowerPi.py", self.blfFile, self.interfacechannel], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
        out = "Es versucht wird eine Verbindung zur PSU aufzubauen . . \n"
        oldline = ""
        while True:
            line = psu_proc.stdout.readline().strip()
            if not line == oldline:
                out = f"{out}{line}\n"
                self.getstatus(out)
                oldline = line
            if "PSU_True" in line:
                self.getstatus("PSU erfolgreich gestartet")
                return True
            if "PSU_False" in line:
                self.getstatus("Messung wird ohne PSU fortgesetzt")
                return False

    def getstatus(self, status):
        self.status = status

    def reset206(self):
        try:
            for cmd in (
                "cansend can0 7E5#0401000000000000",
                "cansend can0 7E5#117F000000000000",
                "cansend can0 7E5#1300030000000000",
                "cansend can0 7E5#1700000000000000",
                "cansend can0 7E5#0400000000000000",
            ):
                subprocess.run(cmd.split(), check=True)
                time.sleep(0.5)
            subprocess.run(
                "bash -c 'printf \"OP1 0\\r\\n\" >/dev/tcp/192.168.1.20/9221'",
                shell=True,
                check=True,
            )
            time.sleep(2)
            subprocess.run(
                "bash -c 'printf \"OP1 1\\r\\n\" >/dev/tcp/192.168.1.20/9221'",
                shell=True,
                check=True,
            )
            exit()
        except Exception as e:
            self.getstatus(f"Fehler {e} bei zurücksetzen von 206")


class MotorController:
    def __init__(self, uart, parent, posname = "StepperPos", sensorname = "RFC_RFE_RSA_127_deg" , dir = None):
        self.uart = serial.Serial(uart, baudrate=115200, timeout=1)
        self.parent = parent
        self.decoded = None
        self.kabelabgang = None
        self.maxpos = 365.0
        self.minpos = 0.0
        self.rmp = 1
        self.movetime = None
        self.pos = None
        self.sensorpos = None
        self.posname = posname
        self.sensorname = sensorname
        self.dir = dir

    def angle_to_float(self, value):
        if value is None:
            return None
        return float(str(value).replace("°", "").strip())

    def get_pos_from_decoded(self):
        self.pos = self.angle_to_float(self.parent.decodedvalue[self.posname])
        return self.pos

    def get_sensor_pos_from_decoded(self):
        positions = []
        for _ in range(10):
            positions.append(self.angle_to_float(self.parent.decodedvalue[self.sensorname]))
            time.sleep(0.05)
        self.sensorpos = np.mean(positions)
        return float(self.sensorpos)

    def build_command(self, cmd = "move_degrees", degrees = None, dir = "ccw", speedRPM = 1): 
        try:
            command = {}
            if cmd == "move_degrees":
                command['cmd'] = cmd
            if cmd == "stepper0":
                command['cmd'] = cmd  
            if cmd == "pause":
                command["cmd"] = cmd
                command['time'] = 5  
            if degrees is not None:
                command['degrees'] = degrees
                self.calculate_move_time(degrees=degrees, speedRPM=speedRPM)
            if dir is not None:
                command['dir'] = dir
            if speedRPM is not None:
                command['speedRPM'] = speedRPM
            self.getstatus(f"Motorcommand: {cmd}, degrees: {degrees}, dir: {dir}, speedRPM: {speedRPM} , Laufzeit: {self.movetime} wird ausgeführt")
            return command
        except: 
            return None


    def calculate_move_time(self, degrees, speedRPM):
        movetime = (degrees / 360) * (60 / speedRPM)
        safety = movetime * 0.1
        if safety < 1:
            safety = 1
        self.movetime = movetime + safety
        return self.movetime 


    def get_move_dir(self):
        try:
            posA = self.get_sensor_pos_from_decoded()
            moveA = self.build_command("move_degrees", degrees=10, dir="ccw", speedRPM=10)
            self.send_to_motor(moveA)
            posB = self.get_sensor_pos_from_decoded()
            moveB = self.build_command("move_degrees", degrees=10, dir="cw", speedRPM=10)
            self.send_to_motor(moveB)
            print(f"posA: {posA}, posB: {posB}")
            if posA <= posB:
                self.dir = "ccw"
            else:
                self.dir = "cw"
        except Exception as e:
            self.getstatus(f"Fehler beim Bestimmen der Bewegungsrichtung: {e}")
            self.dir = None        
            

    def updir(self):
        return self.dir

    def downdir(self):
        if self.updir() == "ccw":
            return "cw"
        if self.updir() == "cw":
            return "ccw"

    def goto_zero(self, degrees, dir, speedRPM = 1):
        try:
            command = self.build_command("move_degrees", degrees=degrees, dir=dir, speedRPM=speedRPM)
            self.send_to_motor(command)
        except Exception as e:
            self.getstatus(f"Fehler beim Goto_Zero: {e}")   
        

    def send_to_motor(self, cmd):
        if self.uart is None:
            return False
        try:
            msg = json.dumps(cmd) + "\n"
            self.uart.write(msg.encode("utf-8"))
            self.pause()
        except Exception as e:
            self.getstatus(f"Fehler beim Senden an den Motor:{e} , CMD: {cmd}")
            return False

        
    def set0(self):
        try:
            cmd = self.build_command("stepper0")
            self.send_to_motor(cmd)
            time.sleep(0.5)
        except Exception as e:
            self.getstatus(f"Fehler beim Setzen auf 0: {e}")

    def set_timer(self):
        try: 
            cmd = self.build_command("pause")
            self.send_to_motor(cmd)
            time.sleep(0.5)
        except Exception as e:
            self.getstatus(f"Fehler beim Setzen auf 0: {e}")

    def pause(self):
        time.sleep(self.movetime + 0.5)

    def messung(self):
        try:
            self.getstatus(f"Stepper wird genullt")
            self.getstatus(f"Sensor wird auf Position {self.maxpos} gefahren")
            cmd = self.build_command("move_degrees", degrees=self.maxpos, dir=self.updir(), speedRPM=1)
            self.send_to_motor(cmd)
            cmd = self.build_command("move_degrees", degrees=self.maxpos, dir=self.downdir(), speedRPM=10)
            self.send_to_motor(cmd)
            self.getstatus(f"Sensor wird auf Start-Position gefahren")
            self.goto_kabelabgang()
        except Exception as e:
            self.getstatus(f"Fehler bei der Messung: {e}")
            exit()

    def getstatus(self, status):
        self.parent.status = status

    def goto_kabelabgang(self):
        self.getstatus(f"Sensor wird zurück auf den Kabelabgang gedreht")
        try:
            self.goto_zero(degrees=self.kabelabgang - 0.6, dir=self.updir(), speedRPM=10)
        except Exception as e:
            self.getstatus(f"Fehler beim Goto_Kabelabgang: {e}")

    def run(self):
        self.getstatus("LIN - Antrieb wird vorbereitet . .")
        try:
            self.kabelabgang = self.get_sensor_pos_from_decoded()
            self.getstatus(f"Kabelabgang: {self.kabelabgang}°")
            self.get_move_dir()
            time.sleep(1)
            self.getstatus(f"Startposition: {self.pos}°, Sensorposition: {self.sensorpos}°, Kabelabgang: {self.kabelabgang}°, Richtung: {self.dir} Linmessung wird vorbereitet . . ")
            self.goto_zero(degrees=self.kabelabgang-0.6, dir=self.downdir(), speedRPM=20)
            while self.get_sensor_pos_from_decoded() > 1:
                self.goto_zero(degrees=self.sensorpos - 0.6, dir=self.downdir(), speedRPM=10)
            self.set0()
            self.set_timer()
        except Exception as e:
            self.getstatus(f"Fehler im MotorController: {e} System wird neu gestartet")
            sys.exit()

def main():
    pass
    # webbrowser.get('firefox').open("http://127.0.0.1:5000")

if __name__ == '__main__':
    my_settingchanger = Settingchanger()
    my_settingchanger.parse_dbc()
    my_settingchanger.parse_config()
    my_settingchanger.run()

    



