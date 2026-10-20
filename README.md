# MyCanlogger

**MyCanlogger** ist ein CAN-Logger mit Webinterface für Raspberry Pi und Linux-Systeme.
Er unterstützt das Mitschneiden von CAN-Traffic, das Dekodieren über DBC-Dateien sowie die Speicherung der Daten im **BLF-Format**.
Zusätzlich ist die Aufzeichnung und Weiterverarbeitung von Zeitdaten im **MDF4-Format** integriert (Work in Progress).

---

## Features

- CAN-Logging über **SocketCAN**, virtuelles CAN oder PEAK-Hardware
- Speicherung im **BLF-Format**
- Dekodierung über **DBC-Dateien**
- Formeleditor
- Signalberechnung zur Laufzeit
- Webinterface (Flask) zur Bedienung und Visualisierung
- Plot-Erzeugung (Plotly / Matplotlib)
- CANopen-Funktionalität inkl. NMT & SDO
- Upload-Funktion für Messreihen
- Raspberry‑Pi‑optimiert

---

## Projektstatus

- **Version:** 0.11.3
- **Status:** WIP (Work in Progress)

---

## Anforderungen

### Hardware
- Raspberry Pi (empfohlen)
- CAN-Interface:
  - SocketCAN
  - PEAK CAN (SPI-basiert)

### Software
- Python ≥ 3.9
- Linux mit SocketCAN
- Git

---

## Installation

```bash
git clone https://git.novo.local/qx/qe/mycanlogger.git
cd mycanlogger
```

---

## ISO-Image (Raspberry Pi)

Ein vorkonfiguriertes Raspberry‑Pi‑Image befindet sich im Ordner:

```
/img
```

### Zugangsdaten

- **User:** pi
- **Initialpassword:** pi  
  ⚠️ Bitte Passwort sofort ändern!

### Netzwerk & Webinterface

- ExampleIP: `192.168.1.1`
- Webinterface: `http://<ExampleIP>:8081`
- IP ändern: `/etc/network/interfaces`

---

## Hinweise

- Benötigte Tools: `cantools`, `candump`, `cansend`, `peakcandriver`
- Bei Nutzung von **PEAK CAN**: SPI in `raspi-config` deaktivieren

---

## Autor

- Markus Steichele


