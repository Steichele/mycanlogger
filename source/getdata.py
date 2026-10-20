import canopen
import can
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import time
from threading import Thread
import os
import struct
from datetime import datetime, timedelta
from mycanlogger import *



class CanOpenGames:
    def __init__(self,hw, channel, br):
        self.node = ""
        self.eds_file = 'config/eds.eds'
        self.nodeid = 127
        self.hw = hw
        self.channel = channel
        self.bus = None
        # self.boudrate = [ 500,250, 1000, 10, 50, 125]
        self.boudrate = [500]
        self.connection = False
        self.dldir = os.path.abspath(os.getcwd()) + "/uploads/"
        self.save = 0x65766173
        self.save_internal = 0x756e616d  # "manu"
        self.kill = 0x6c6c696b #203?
        self.load = 0x64616f6c
        self.open = 0x6E65706F  # open to jump to bootloader
        self.bitrate = br 
        self.logmessage = None
        self.initdict = {}
        self.readbackdict = {}
        self.nw = None
        self.nodes = {} 
    
    def network_connect(self, id = 127, br=500):
        self.bitrate = br
        self.nodeid = id
        network = canopen.Network()
        self.nw = network.connect(interface = self.hw, channel=self.channel, bitrate=self.bitrate)  
        self.node = canopen.RemoteNode(self.nodeid, 'config/eds.eds')
        network.add_node(self.node)
        self.nw.add_node(self.node)
        self.nodes[id] = self.node
        self.connection = True


    def network_disconnect(self):
        self.nw.disconnect()
        self.connection = False

    def extract_parameter_names(self):
        parameter_names = []
        with open(self.eds_file, 'r') as file:
            eds_content = file.readlines()
            for line in eds_content:
                line = line.strip()
                if line.startswith('ParameterName'):
                    parameter_name = line.split('=')[1].strip()
                    parameter_names.append(parameter_name)
        return parameter_names
    
    def set_reset(self):
        self.node.nmt.state = 'RESET COMMUNICATION'
        self.node.nmt.state = 'RESET'

    
    def set_opmode(self):
        self.node.nmt.state = 'OPERATIONAL'

    def set_preopmode(self):
        self.node.nmt.state = 'PRE-OPERATIONAL'

    def cycletime(self, cycle):
        self.node.sdo['Transmit PDO Communication Parameter 1']['Event Timer'].raw = cycle

    def readnumberofchannels(self):
        noc = self.node.pdo['Offset value for multi-sensor devices']['Offset value Channel 1'].raw
        print(noc)
        return(noc)

    def set_boudrate(self, boudrate = 250):
        '''Kboud'''
        boudrate = boudrate
        self.set_preopmode()
        self.node.sdo['CAN bit rate'].raw = boudrate
        self.killstore([4,1])


    def set_nodeid(self,id,save = False):
        self.nodeid = id  
        self.set_preopmode()
        self.node.sdo['Node-ID'].raw = self.nodeid
        if save == True:
            self.killstore([4,1])


    def readpara(self, parameter_names):
        objlist = parameter_names
        sensordict = {}
        for obj in objlist:
            try:
                sensordict[obj] = self.node.sdo[obj].raw
            except:
                print("Fehler beim Lesen des Objekts " + str(obj))
                try:
                    sensordict[obj] = self.node.pdo[obj].raw
                except:
                    print("Fehler beim Lesen des Objekts " + str(obj))
        return sensordict

    def readpara_dict(self, parameter_names):
        sensordict = {}
        for name, (index, subindex) in parameter_names.items():
            try:
                if subindex == 0:
                    value = self.node.sdo[index].raw
                else:
                    value = self.node.sdo[index][subindex].raw
                sensordict[name] = value
            except Exception as e:
                print(f"Fehler beim Lesen des Objekts{name}: {e}")
        return sensordict
            
    
    def findsensor(self, id = None):
        parameter_names = self.extract_parameter_names()  # Parameter aus der EDS-Datei extrahieren
        sensordict = {}
        idlist = []
        # for br in self.boudrate:
        try:
            if id:
                idlist.append(id)
            else:
                for id in range(127, 1, -1):
                    idlist.append(id)

            for id in idlist:
                try:
                    if self.connection == False:
                        self.network_connect(id , br)  # Verbindung zum Netzwerk herstellen
                        self.set_preopmode()  # Knoten in den Pre-Operational-Modus versetzen
                except Exception as e:
                    print("Fehler bei Boudrate:"+ str(br) + " ID:" + str(id))
                    print(e)
                    self.network_disconnect()
                    pass    

                try:    
                    sensordict = self.readpara(parameter_names)
                    nodeid = self.writexml(sensordict)
                    if self.connection == True:
                        self.network_disconnect()  # Netzwerkverbindung trennen
                    break
                except:
                    if self.connection == True:
                        self.network_disconnect()  # Netzwerkverbindung trennen
            self.network_disconnect()
        except:
            pass
        return(sensordict)
                

    
    def writexml(self, data):
        manufacturer_device_name = data['Manufacturer Device Name']
        node_id = data['Node-ID']
        filename = f"{manufacturer_device_name}_NODE-ID{node_id}.xml"
        root = ET.Element("root")
        for key, value in data.items():
            element = ET.SubElement(root, key.replace("/", "-").replace(" ", "_"))
            element.text = str(value)
            print(str(key) + "||" +str(value))
        tree = ET.ElementTree(root)
        tree.write(self.dldir + filename, encoding='utf-8', xml_declaration=True )
        print(self.dldir + filename)
        print(node_id)
        return(node_id)
    
    def autoreset(self, newid=127):
        newid = newid
        id = self.findsensor()
        nodeid = id
        if self.connection == False:                
            self.network_connect(id, 250)
        time.sleep(2)
        while nodeid == newid:  
            self.set_nodeid(newid)
            nodeid = self.findsensor(nodeid)
        self.set_opmode()
    
    # def increment_can_ID(self):
    #     id = 127
    #     for newid in range(1,100):
    #         try:
    #             self.findsensor(id)
    #             self.network_connect(id,self.boudrate)
    #             self.set_preopmode()
    #             self.set_nodeid(newid)
    #             self.network_disconnect()
    #             time.sleep(2)
    #             self.findsensor(newid)
    #             self.network_connect(newid,self.boudrate)
    #             self.set_preopmode()
    #             self.cycletime(10)
    #             self.set_opmode()
    #             time.sleep(3)
    #             self.set_preopmode()
    #             self.network_disconnect()
    #             input("Nächsten Sensor anschließen und Enter damit es weiter geht . .")
    #         except:
    #             print("Vorgang wird wiederholt . . .")

    def startup_all(self, idlist, cycle):
        print(idlist)
        print(cycle)
        for id in idlist:
            try:
                self.network_connect(id,self.boudrate)
                self.set_opmode()
                self.cycletime(cycle)
            except:
                pass

    def gotobootloader(self):
        dta = self.node.sdo[0x1000].data # Application
        try:
            self.node.sdo[0x1010][5].raw = self.open # geh in Bootloader
        except:
            pass
        time.sleep(1)
        dtb = self.node.sdo[0x1000].data # Application Bootloader
        crc = self.node.sdo[0x2003].data # Bootloader CRC
        # crc = self.node.sdo[0x2003].upload()
        print(dta)
        print(dtb)
        print(crc)

    def restore(self):
        try:
            restore_default_parameters = self.node.sdo[0x1011][3].raw
            print(f'Restore Default Parameters: {restore_default_parameters}')
        except Exception as e:
            print(e)

        try:
            self.node.sdo[0x1011][1].raw = self.kill # Beispielwert zum Zurücksetzen der Parameter
        except Exception as e:
            print(e)
     

    def killer(self):
        # Stellt die Werkseinstellungen wieder her
        try:
            self.node.sdo[0x1010][3].raw = self.kill
        except Exception as e:
            print(e)
        try:
            self.node.sdo[0x1010][4].raw = self.kill
        except Exception as e:
            print(e)
        try:
            self.node.sdo[0x1010][2].raw = self.kill
        except Exception as e:
            print(e)
        try:
            self.node.sdo['Store Parameter Field']['Save all Parameters'].raw = self.kill
        except Exception as e:
            print(e)


    def killstore(self, subindex = None):    
        if not subindex:
            storelist = [4,3,1]
        else:
            storelist = subindex

        for si in storelist:
            try:
                self.node.sdo[0x1010][si].raw = self.save
            except Exception as e:
                print(f"kein store möglich{e}")

            self.node.nmt.state = 'RESET'

    def store(self, subindex = None):    
        if not subindex:
            storelist = [4,3,1]
        else:
            storelist = subindex

        for si in storelist:
            try:
                self.node.sdo[0x1010][si].raw = self.save
            except Exception as e:
                print(e)


    def lss_config_nodeid(self):
        if not self.connection:
            print("Not connected to network")
            return
        self.reboot_device()
        # LSS Slave in den Konfigurationsmodus versetzen
        self.nw.send_message(0x7E5, [0x04, 0x01])
        print("Switched to CONFIGURATION mode")

        # Node-ID setzen
        self.nw.send_message(0x7E5, [0x11, self.nodeid])
        print(f"Configured Node-ID to {self.nodeid}")

        # Konfiguration speichern
        self.nw.send_message(0x7E5, [0x17, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        print("Configuration save command sent")
        self.reboot_device()

    def lss_config_bitrate(self):
            '''
            Übernimmt die settings aus der Node
            '''
            self.network = self.nw
            if not self.connection:
                print("Not connected to network")
                return
            # self.reboot_device()
            # LSS Slave in den Konfigurationsmodus versetzen
            self.network.send_message(0x7E5, [0x04, 0x01])
            print("Switched to CONFIGURATION mode")
            try:
                # Bitrate setzen
                bitrate_bytes = self.bitrate.to_bytes(4, 'little')
                self.network.send_message(0x7E5, [0x13] + [0x00,0x04, 0x00, 0x00, 0x00, 0x00])#list(bitrate_bytes))
                print(f"Configured bitrate to {self.bitrate}")
            except Exception as e:
                print(e)

            # Konfiguration speichern
            self.nw.send_message(0x7E5, [0x17, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            print("Configuration save command sent")
            self.reboot_device()

    # def lss_config_bitrate(self):
    #     if not self.connection:
    #         print("Not connected to network")
    #         return

    #     # LSS Slave in den Konfigurationsmodus versetzen
    #     self.network.send_message(0x7E5, [0x04, 0x01])
    #     print("Switched to CONFIGURATION mode")

    #     # Bitrate setzen
    #     bitrate_bytes = self.bitrate.to_bytes(4, 'little')
    #     self.network.send_message(0x7E5, [0x13] + list(bitrate_bytes))
    #     print(f"Configured bitrate to {self.bitrate}")

    #     # LSS Slave in den Betriebsmodus versetzen
    #     self.network.send_message(0x7E5, [0x04, 0x00])
    #     print("Switched to OPERATIONAL mode")

    #     # Konfiguration speichern
    #     save_command = self.save.to_bytes(4, 'little')
    #     self.network.send_message(0x600 + self.nodeid, [0x23, 0x10, 0x01, 0x00] + list(save_command))
    #     print("Configuration saved")

    def readback(self, index, subindex=0, value=None):
        try:
            # Wert wieder auslesen
            if subindex == 0:
                readback_value = self.node.sdo[index].raw
            else:
                readback_value = self.node.sdo[index][subindex].raw
            print(f"Wieder-ausgelesener Wert bei Index {hex(index)}, Subindex {subindex}: {readback_value}")
            self.readbackdict[(index, subindex)] = readback_value
            
        except canopen.SdoCommunicationError as e:
            print(f"SDO Communication Error: {e}")
        except canopen.SdoAbortedError as e:
            print(f"SDO Aborted Error: {e}")
        except Exception as e:
            print(f"Unexpected Error: {e}")

    def read_write(self, index, subindex=0, value=None):
            try:
                # Initialen Wert auslesen
                if subindex == 0:
                    initial_value = self.node.sdo[index].raw
                else:
                    initial_value = self.node.sdo[index][subindex].raw
                print(f"Initialer Wert bei Index {hex(index)}, Subindex {subindex}: {initial_value}")
                self.initdict[(index, subindex)] = initial_value

                # Neuen Wert schreiben, falls angegeben
                if value is not None:
                    if subindex == 0:
                        self.node.sdo[index].raw = value
                    else:
                        self.node.sdo[index][subindex].raw = value
                    print(f"Geschriebener Wert bei Index {hex(index)}, Subindex {subindex}: {value}")
                self.store([4,1])

            except canopen.SdoCommunicationError as e:
                print(f"SDO Communication Error: {e}")
            except canopen.SdoAbortedError as e:
                print(f"SDO Aborted Error: {e}")
            except Exception as e:
                print(f"Unexpected Error: {e}")
  

    def call_read_write_readback(self, valueType="RFC_good.txt"):
        excluded_objects = [0x2000 , 0x2001]  # Füge hier die Indizes der auszuschließenden Objekte hinzu
        values_dict = self.read_file_to_dict(valueType)
        self.initdict = {}
        self.readbackdict = {}
        for (index, subindex), value in values_dict.items():
            try:
                self.read_write(index, subindex, value)
            except Exception as e:
                print(e)
        self.reboot_device()
        self.network_connect(self.nodeid,250000)
        for (index, subindex), value in values_dict.items():
            try:
                self.readback(index, subindex, value)
            except Exception as e:
                print(e)

    def check_changes(self):
        assertdict = {}
        for key, value in self.initdict.items():
            index = key[0] 
            subindex = key[1]
            try:
                if int(value) == int(self.readbackdict[(index, subindex)]):
                    print(f"{hex(index)} {subindex} wurde nicht verändert. Ausgelesenner Wert {value}")
                    assertdict[(index, subindex)] = False 
                else:
                    print(f"{hex(index)} {subindex} Ausgelesenner Wert {value}, alter Wert {self.initdict[(key)]}") 
                    assertdict[(index, subindex)] = True 
            except Exception as e:
                print(e)
        return assertdict


        

    def read_node_id(self):
        self.set_preopmode()
        nodeid = self.node.sdo['Node-ID'].raw
        return nodeid

    def set_temperatur_min(self,value):
        self.node.sdo[0x235A][1].raw = value
    
    def set_temperatur_max(self,value):
        self.node.sdo[0x235A][2].raw = value

    def read_temperature_warning(self):
        # Alle Subindizes des Objekts 0x235A auslesen
        for subindex in range(3):  # Da der höchste Subindex 2 ist
            try:
                value = self.node.sdo[0x235A][subindex].raw
                print(f"Subindex {subindex}: {value}")
            except canopen.sdo.exceptions.SdoAbortedError as e:
                print(f"Fehler beim Auslesen von Subindex {subindex}: {e}")
            
            try:
                value = self.node.sdo[0x235A].raw
                print(f"Subindex {subindex}: {value}")
            except canopen.sdo.exceptions.SdoAbortedError as e:
                print(f"Fehler beim Auslesen von Subindex {subindex}: {e}")

    def read_warnings(self):
        supWarning = self.node.sdo['Supported Warnings'].raw
        warning = self.node.sdo['Warnings'].raw   
        supAlarms = self.node.sdo['Supported Alarms'].raw
        alarm = self.node.sdo['Alarms'].raw   
        print(f"Warning {warning} von {supWarning}, Alarm {alarm} von {supAlarms} ")
    

    def int_to_bytes(self, values):
        import struct
        if len(values) != 4:
            raise ValueError("Die Liste muss genau vier Werte enthalten.")
        
        # Überprüfen, ob jeder Wert innerhalb des gültigen Bereichs liegt
        for value in values:
            if not (0 <= value < 2**32):
                raise ValueError("Jeder Wert muss zwischen 0 und 2^32-1 liegen.")
        
        # Umwandlung der Werte in Bytes und Hinzufügen zur Liste
        byte_list = []
        for value in values:
            byte_data = struct.pack('<H', value)
            byte_list.extend(byte_data)
        
        return byte_list

    def register_range(self, valuelist, register):
        if register >= 101:
            valuelist = valuelist[0:4]
        else:
            valuelist = [valuelist[0], valuelist[1], valuelist[3], valuelist[5]]
        return valuelist

    def read_sdo_values(self, nodeid, offset = 0x180 + 0x28):
        node = self.nodes[nodeid]  # Zugriff auf den spezifischen Knoten
        i40LotPon = node.sdo[0x2330][1].raw
        i40OdoPon = node.sdo[0x2340][1].raw
        i40TimePon = node.sdo[0x2320][1].raw
        i40OTempActual = node.sdo[0x2350][1].raw
        i40OSupplyActual = node.sdo[0x2360][1].raw
        data = [i40OSupplyActual, i40OTempActual, i40TimePon, i40OdoPon]     
        # Konvertieren der Daten in Bytes und sicherstellen, dass sie im gültigen Bereich liegen
        data_bytes = self.int_to_bytes(data)
        # Erstellen der CAN-Nachricht
        msg = can.Message(arbitration_id= offset + nodeid, data=data_bytes)
        # Nachricht senden
        self.nw.send_message(msg.arbitration_id, msg.data)
        for value in data:
            print(value)


    def reboot_device(self):
    # Senden des NMT-Befehls für Reset Application (129)
        self.nw.send_message(0, [129, self.nodeid])

    def read_file_to_dict(self, file_path = "RFC_good.txt"):
        result_dict = {}
        with open(file_path, 'r') as file:
            for line in file:
                valueline = line.strip().split('# ')
                print(f"eingelesen wird {valueline}")
                key, value = valueline[0].strip().split(': ')
                # Konvertiere den Schlüssel zurück in ein Tupel
                key = eval(key)
                # Konvertiere den Wert in die entsprechende Zahl
                value = int(value, 0)
                result_dict[key] = value
        return result_dict


    def lss_nodeid_test(self):
        try:
            id = 1
            self.network_connect(id, 250000)
            self.lss_config_nodeid()
            if self.findsensor(id):
                return True
        except:
            return False
    


    def test(self):
        caninterface = 'socketcan'
        interfacechannel = "can0"
        boudrate =250
        newboudrate = 250
        id = 127
        newid = 10
        cg = CanOpenGames(caninterface, interfacechannel , 250000)
        cg.network_connect(id,250000)
        cg.set_preopmode()
        # cg.set_offset(0x100)
        # cg.store()
        cg.call_read_write_readback(0)
        assertdict = cg.check_changes()
        cg.killer()
        cg.reboot_device()
        for key, value in assertdict.items():
            index = hex(key[0])
            sub = hex(key[1])
            print(f"{index}:{sub} : {value}")
        print(cg.initdict)
        print(cg.readbackdict)


    def unbrick(self, newid):
        self.node.sdo['Node-ID'].raw = newid
        try:
            self.node.sdo[0x1010][5].raw = self.kill
        except Exception as e:
            print(e)
        try:
            self.node.sdo[0x1010][4].raw = self.save
        except Exception as e:
            print(e)
        try:
            self.node.sdo[0x1010][1].raw = self.save
        except Exception as e:
            print(e)

    
    def read_auto_op(self):
        out = self.node.sdo['NMT Startup'].raw
        print(out)
        out = self.node.sdo['Transmit PDO Communication Parameter 1']['Event Timer'].raw 
        print(out)
        self.node.sdo['NMT Startup'].raw = 8
        self.killstore([1])
        time.sleep(1)
        self.node.sdo['Transmit PDO Communication Parameter 1']['Event Timer'].raw = 100
        self.killstore([4])
    
    # def set_offset(self, deg):
    #     digitPerDeg = 16384 / 360
    #     offset = digitPerDeg * deg
    #     try:
    #         self.node.sdo["Offset value for multi-sensor devices"].raw = offset
    #     except Exception as e:
    #         print(e)
    #     try:
    #         self.node.sdo["Preset value for multi-sensor devices"].raw = offset
    #     except Exception as e:
    #         print(e)
    
    def serial(self):
        # self.node.sdo[0x1011][1].raw = 0x6c6f6164
        sn = self.node.sdo[0x236A][1].raw
        print(sn)

    def writeDiviceName(self):
        name = [0x4D, 0x61, 0x6E, 0x75, 0x66, 0x61, 0x63, 0x74, 0x75, 0x72, 0x65, 0x72, 0x20, 0x44, 0x65, 0x76, 0x69, 0x63, 0x65, 0x20, 0x4E, 0x61, 0x6D, 0x65]
        self.node.sdo['Manufacturer Device Name'].raw = name

    def set_offset(self, deg):
        digitPerDeg = 16384 / 360
        offset = digitPerDeg * deg
        try:
            self.node.sdo['Preset Value for Multi Sensor Devices']['Preset Value Channel 1'].raw = offset
            print(f'set offset {deg} °')
        except Exception as e:
            print(f"Fehler {e} Kanal 1")
        try:
            self.node.sdo['Position Value for Multi Sensor Devices']['Position Value Channel 1'].raw = offset
            print(f'set offset {deg} °')
        except Exception as e:
            print(f"Fehler {e} Kanal 1")
        try:
            self.node.sdo['Preset Value for Multi Sensor Devices']['Preset Value Channel 2'].raw = offset
            print(f'set offset {deg} °')
        except Exception as e:
            print(f"Fehler {e} Kanal 2")
        try:
            self.node.sdo['Position Value for Multi Sensor Devices']['Position Value Channel 2'].raw = offset
            print(f'set offset {deg} °')
        except Exception as e:
            print(f"Fehler {e} Kanal ")
    
    def check_offset(self, deg):
        ergDict = {}
        fs = 16384
        ch1 = []
        ch2 = []
        try:
            ch1.append(360 / fs * self.node.sdo['Position Value for Multi Sensor Devices']['Position Value Channel 1'].raw)
        except:
            pass
        try:
            ch2.append(360 / fs * self.node.sdo['Position Value for Multi Sensor Devices']['Position Value Channel 2'].raw) 
        except:
            pass
        self.set_offset(deg)
        try:
            ch1.append(360 / fs * self.node.sdo['Position Value for Multi Sensor Devices']['Position Value Channel 1'].raw)
        except:
            pass
        try:
            ch2.append(360 / fs * self.node.sdo['Position Value for Multi Sensor Devices']['Position Value Channel 2'].raw) 
        except:
            pass

        if deg == round(ch1[0] - ch1[1],0):
            ergDict['ch1'] = True
        else:
            ergDict['ch1'] = False
        try:
            if deg == round(ch2[0] - ch2[1],0):
                ergDict['ch2'] = True
            else:
                ergDict['ch2'] = False
        except:
            pass
        print(ch1)
        print(deg)
        return ergDict
    
    def set_angle_filter(self,filter = 2):
        self.node.sdo[0x2010][1].raw = filter
        self.node.sdo[0x2010][2].raw = filter
        self.store()


def start_unbrick():
    caninterface = 'socketcan'
    interfacechannel = "can0"
    boudrate =250
    newboudrate = 250
    id = 8
    newid = 127
    cg = CanOpenGames(caninterface, interfacechannel , 250000)
    cg.network_connect(id,250000)
    cg.unbrick(newid)
    try:    
        cg.network_connect(id,250000)
        cg.set_preopmode()
        cg.set_nodeid(newid)
        # cg.killstore()
        time.sleep(4)
        cg.reboot_device()
        time.sleep(3)
        cg.network_connect(newid,250000)
        cg.set_preopmode()
        cg.set_nodeid(id)
        cg.reboot_device()
        time.sleep(4)
        cg.network_connect(id,250000)
        cg.set_preopmode()
        cg.set_nodeid(newid)
        cg.reboot_device()
        time.sleep(4)
        print("unbrick")
    except Exception as e:
        print(f"unbrick hat nicht geklappt : {e}")

def autoop10ms():
    caninterface = 'socketcan'
    interfacechannel = "can0"
    boudrate =250
    newboudrate = 250
    id = 127

    cg = CanOpenGames(caninterface, interfacechannel , 250000)
    cg.network_connect(id,250000)
    cg.set_preopmode()
    cg.node.sdo['NMT Startup'].raw = 8
    cg.killstore([4])
    time.sleep(1)
    cg.node.sdo['Transmit PDO Communication Parameter 1']['Event Timer'].raw = 10
    cg.killstore([1])

def main():
    # test_unbrick()
    caninterface = 'socketcan'
    interfacechannel = "can0"
    boudrate =500
    newboudrate = 250
    id = 5
    newid = 127

    autoop10ms()

#     cg = CanOpenGames(caninterface, interfacechannel, 250000)
#     cg.network_connect(id, boudrate)  
#   #cg.killer()
#     # cg.serial()
#     # cg.set_preopmode()
#     # cg.set_nodeid(newid)
#     # cg.set_angle_filter()
#     cg.store()
#     cg.reboot_device()

    # Liste der Node-IDs, die du abfragen möchtest

    # node_ids = [] 
    # for id in range(2):
    #     node_ids.append(id)
    # # Initialisiere die Verbindung und den Betriebsmodus einmalig für alle IDs
    # for id in node_ids:
    #     try:
    #         cg.network_connect(id, boudrate)
    #         cg.set_opmode()
    #     except Exception as e:
    #         print(f"Fehler bei der Initialisierung von ID {id}: {e}")

    # # Hauptschleife zum Lesen der SDO-Werte
    # while True:
    #     for id in node_ids:
    #         try:
    #             cg.read_sdo_values(id)
    #             time.sleep(1)
    #         except Exception as e:
    #             print(f"Fehler beim Lesen der SDO-Werte von ID {id}: {e}")

    # # cg.serial()
    # # cg.cycletime(10)
    # cg.set_offset(0)
    # cg.killstore([1])
    # for deg in range(20, 350, 15):
    #     cg.reboot_device()
    #     time.sleep(1)
    #     cg.network_connect(id,boudrate)
    #     cg.set_preopmode()
    #     cg.check_offset(deg)
    #     cg.set_opmode()
    # cg.read_auto_op()
    # cg.set_boudrate(newboudrate)
    # cg.reboot_device()
    # cg.read_warnings()

    # cg.killer()




if __name__ == "__main__":
    main()
        
 
