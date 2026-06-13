# poolcontrol

ESPHome-based pool automation for a 10m³ hexagonal swimming pool, built around an ESP32 with a Dingtian relay board, Atlas Scientific EZO probes, a peristaltic dosing pump and a W'Eau heat pump.

---

## Hardware overview

| Component | Model | Interface |
|---|---|---|
| Microcontroller | ESP32 (esp32dev) | — |
| Relay/IO board | Dingtian DTR0xx | SPI (GPIO13/14/15/16/32) |
| pH probe | Atlas Scientific EZO-pH | I2C 0x63 |
| ORP probe | Atlas Scientific EZO-ORP | I2C 0x62 |
| Roof temperature | Atlas Scientific EZO-RTD | I2C 0x66 |
| Pool temperature | Atlas Scientific EZO-RTD | I2C 0x67 |
| Flow meter | Atlas Scientific EZO-FLO | I2C 0x68 |
| Chlorine dosing pump | Atlas Scientific EZO-PMP | I2C 0x64 |
| Ambient temperature | Dallas DS18B20 | 1-Wire GPIO0 |
| Heat pump | W'Eau WFI-005 | Local Tuya / HA |
| Circulation pump | Aquaforte Vario iSaver+ | Relay (3 speeds) |
| Pool display | ACT1025 64×16 LED matrix | BLE (0D:D0:1E:CD:2F:D2) |

### I2C bus (SDA: GPIO4, SCL: GPIO5, 400kHz)

| Address | Component |
|---|---|
| 0x62 | EZO-ORP |
| 0x63 | EZO-pH |
| 0x64 | EZO-PMP (chlorine dosing pump) |
| 0x66 | EZO-RTD (roof temperature) |
| 0x67 | EZO-RTD (pool temperature) |
| 0x68 | EZO-FLO (flow meter) |

### Relay layout (Dingtian)

| Relay | Function |
|---|---|
| R1 | Not used |
| R2 | Circulation pump OFF |
| R3 | Circulation pump LOW |
| R4 | Circulation pump MED |
| R5 | Circulation pump HIGH |
| R6 | Not used |
| R7 | 3-way valve bypass roof |
| R8 | Not used |

### Inputs (Dingtian)

| Input | Function |
|---|---|
| I1 | 3-way valve position ROOF |
| I2 | 3-way valve position POOL |
| I3 | Water level HIGH |
| I4 | Water level NORMAL |
| I5 | Water level LOW |
| I6 | ACK 6-way valve |
| I7 | ACK skimmer |
| I8 | Not used |

---

## Package structure

The configuration is split into packages for clarity:

```
poolcontrol.yaml              # Main configuration
poolcontrol_files/
  core.yaml                   # WiFi info, uptime, hostname, restart
  heatpump.yaml               # Heat pump logic, PV/battery control
  dingtian.yaml               # Relay board, inputs, pump control
  display.yaml                # BLE LED display (ACT1025)
  components/                 # Local ESPHome external components
```

### Globals defined in poolcontrol.yaml

The following globals are used by the packages and must be defined in `poolcontrol.yaml`:

| ID | Type | Purpose |
|---|---|---|
| `flow_reference` | float | Reference flow for trend detection |
| `flow_low_since` | uint32_t | Timestamp of low flow detection |
| `water_level_high_notified` | bool | Water level high notification state |

---

## Features

### Circulation pump
- **Auto mode**: pump speed controlled based on deltaTemp (roof−pool) and ambient temperature
- **Manual mode**: manual speed selection via HA
- **Vacuum mode**: forces HIGH speed + valve to Pool position for 60 minutes, then returns to auto
- **Flow protection**: at flow < 0.5 L/min, 3 restart attempts are made; after 3 failed attempts → emergency shutdown with HA notification

### Heat pump
- **Auto control**: heat pump ON when sufficient PV surplus (>1.5 kW export) or full battery (SOC >80%)
- **Minimum runtime**: 30 minutes before shutdown is allowed
- **Battery protection**: if SOC drops ≥3% without PV → heat pump OFF, circulation pump to LOW
- **Forced heating**: manual override via HA switch

### 3-way valve
- Automatically controlled based on deltaTemp (roof−pool)
- delta > 5°C → bypass ROOF (water through solar panels)
- delta < 1°C → bypass POOL (water bypasses solar panels)

### Water level
- Three level sensors: HIGH, NORMAL, LOW
- At HIGH: repeating HA notification every 5 minutes while high

### Chlorine dosing (EZO-PMP)
- **Automatic**: doses based on ORP value
  - Thresholds configurable via HA (default: dose below 650 mV, stop above 750 mV)
  - Minimum wait time between doses configurable (default: 30 min)
  - Maximum daily volume configurable (default: 500 mL)
- **Manual**: dose a configurable volume via HA button
- **Safety**: dosing stops automatically if pump is unreachable (I2C error)
- **Volume tracking**: persistent total volume (survives reboots), daily volume (reset at midnight)

### Pool display (ACT1025)
- BLE LED matrix 64×16 pixels
- Displays: pool temperature, pH, ORP
- Adjustable brightness via HA

---

## Calibration

### pH (EZO-pH)

Three-point calibration (low/mid/high):

1. Press **Clear pH Calibration** — clear old calibration
2. Submerge probe in pH 7 buffer → press **pH 7 Calibrate**
3. Submerge probe in pH 10 buffer → press **pH 10 Calibrate**
4. Submerge probe in pH 4 buffer → press **pH 4 Calibrate**
5. Optional: press **Query pH slope** to check calibration quality (ideal: >95%)

### ORP (EZO-ORP)

Single-point calibration:

1. Press **Clear Orp Calibration** — clear old calibration
2. Submerge probe in 225 mV ORP standard solution
3. Press **Orp 225mV Calibrate**

### Chlorine dosing pump (EZO-PMP)

1. **Prime**: set Manual Volume to 200 mL, press **Chloor Doseer Manueel** — repeat until tube is free of air bubbles
2. **Clear calibration**: press **Chloor Wis Kalibratie**
3. **Calibrate**:
   - Set Manual Volume to 10 mL
   - Hold a measuring cylinder under the outlet
   - Press **Chloor Doseer Manueel**
   - Measure the actual pumped volume
   - Enter the measured volume in **Chloor Kalibratie Volume (gemeten)**
   - Press **Chloor Stel Kalibratie In**
4. **Verify**: run a second 10 mL dose and check that the volume is now accurate

> ⚠️ Calibrate with water before connecting the chlorine line. Water and sodium hypochlorite have a similar viscosity; the deviation is negligible.

---

## Installation

### Requirements
- Home Assistant with ESPHome add-on
- Secrets in `/config/esphome/secrets.yaml`:

```yaml
wifi_ssid: "your_ssid"
wifi_password: "your_password"
ap_password: "fallback_password"
api_key: "your_api_key"
```

### Flashing

**First time** (via USB):
```bash
esphome run poolcontrol.yaml
```

**Subsequent updates via OTA** from ESPHome Dashboard → **Install** → **Wirelessly**

### Changing I2C address (EZO modules)

To move an EZO module to a new address:

1. Disconnect all other modules from the I2C bus (only the module to be changed connected)
2. Temporarily add a button to the YAML:
```yaml
button:
  - platform: template
    name: "Change I2C address"
    on_press:
      - lambda: id(ezo_sensor_id).send_custom("I2C,<decimal_address>");
```
3. Flash, press the button, remove the button and flash again
4. Update the `address:` field in the YAML

> The EZO command uses **decimal** addresses: 0x64 = 100, 0x67 = 103, etc.

---

## Home Assistant entities

### Sensors
| Entity | Unit | Description |
|---|---|---|
| pH | pH | Pool water acidity |
| ORP | mV | Redox potential |
| pool temp | °C | Pool water temperature (EZO-RTD) |
| Roof temp | °C | Roof temperature (EZO-RTD) |
| Delta temperature | °C | Roof − Pool temperature |
| Pump Flow Rate | L/min | Calculated flow rate |
| Vrije Chloor (met temp) | ppm | Calculated free chlorine (ORP/pH/temp) |
| Omgeving | °C | Ambient temperature (DS18B20) |
| Chloor Gedoseerd Vandaag | mL | Daily chlorine volume |
| Chloor Totaal Volume Gedoseerd (persistent) | mL | Total volume (reboot-safe) |

### Switches
| Entity | Description |
|---|---|
| Automatisch Doseren | Chlorine auto-dosing on/off |
| Forced heating | Manual heat pump override |

### Selects
| Entity | Options |
|---|---|
| Pump Mode | auto / manual / vacuum |
| Pump speed | off / low / med / high |

---

## Related repositories

- [poolcontrol](https://github.com/FirelightLokeren/poolcontrol) — this repository
- [esphome-pool-display](https://github.com/FirelightLokeren/esphome-pool-display) — ACT1025 BLE display component
