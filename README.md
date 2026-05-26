# ESPHome Poolcontrol

ESPHome configuratie voor het automatiseren van een achthoekige opbouwpool (10m³) met een ESP32.

## Hardware

| Component | Details |
|-----------|---------|
| Controller | ESP32 (esp32dev, Arduino framework) op `192.168.1.48` |
| Relay board | Dingtian (dtr0xx_io via UART GPIO1/3) — 8 relays, 8 inputs |
| pH probe | Atlas Scientific EZO (I2C 0x63) |
| ORP probe | Atlas Scientific EZO (I2C 0x62) |
| Roof temp | Atlas Scientific EZO RTD (I2C 0x66) |
| Pool temp | Atlas Scientific EZO RTD (I2C 0x67) |
| Flow | Atlas Scientific EZO FLO (I2C 0x68) |
| Omgeving temp | DS18B20 (1-wire GPIO0) |
| Warmtepomp | W'Eau WFI-005 (Local Tuya) |
| Poolpomp | Aquaforte Vario iSaver+ (D1-D4 relays) |
| Display | ACT1025 BLE LED matrix (MAC: `0D:D0:1E:CD:2F:D2`) |
| Omvormer | Huawei SUN2000-8KTL + LUNA2000 batterij |
| Fotometer | PoolLab 1.0 |
| Zonnecollectoren | 10.5m² op dak |

## Bestandsstructuur

```
poolcontrol.yaml                 ← hoofdbestand
poolcontrol_files/
├── core.yaml                    ← wifi, logging, api, ota
├── heatpump.yaml                ← energiebeheer + warmtepomp
├── dingtian.yaml                ← relay/input configuratie
├── display.yaml                 ← BLE display package
└── components/
    └── pool_display/
        ├── pool_display.h       ← Arduino BLE component
        └── __init__.py
```

## Relay mapping

| Relay | ID | Functie |
|-------|----|---------|
| 1 | - | vrij |
| 2 | `relay_pump_off` | Pomp uit |
| 3 | `relay_pump_low` | Pomp laag (~1.5 L/min) |
| 4 | `relay_pump_med` | Pomp medium (~2.3 L/min) |
| 5 | `relay_pump_high` | Pomp hoog (~2.75 L/min) |
| 6 | - | vrij |
| 7 | `relay_bypass` | Bypass dak (OFF=Pool, ON=Roof) |
| 8 | - | vrij |

## Pump Mode

| Mode | Beschrijving |
|------|-------------|
| `auto` | Volledig automatisch beheerd |
| `manual` | Manuele controle |
| `vacuum` | High + klep Pool geforceerd, na 60 min terug naar auto |

## Warmtepomp Auto Logica

### Inschakelen verwarmen
```
export > 1.5kW + import < 0.1kW + pv > 200W
OF batterij > 80% + pv > 500W
EN pool < target - 0.5°C
→ heat mode + quick_heat preset
```

### Inschakelen koelen
```
zelfde energieconditie
EN pool > target + 0.5°C
→ cool mode + quiet_cool preset
(max koeltemperatuur warmtepomp: 28°C)
```

### Uitschakelen
```
geen energie OF pool op temp
EN minimum 30 min gelopen
```

### Harde stop (batterij)
```
SOC daalt >= 3% + PV < 200W
→ warmtepomp UIT (ook in manual mode)
→ notificatie
```

## Pompsnelheid Batterijlogica
```
SOC daalt >= 3% + auto mode → pomp naar low
SOC stijgt >= 3% + auto mode → terug naar med
```

## Flow Beveiliging
```
Flow < 0.5 L/min + pomp aan (auto mode):
  Retry 1: pomp 30sec UIT → herstart → 1min wachten
  Retry 2: pomp 30sec UIT → herstart → 1min wachten
  Retry 3: emergency shutdown + push notificatie
```

## Notificaties

| Situatie | Kanaal |
|----------|--------|
| Warmtepomp AAN ☀️ | HA persistent notification |
| Warmtepomp UIT 🌙 | HA persistent notification |
| Manueel gewijzigd 🖐️ | HA persistent notification |
| Fault + auto + low | HA notif (pomp naar med) |
| Fault + auto + med/high | HA notif + push gsm_koen |
| Emergency shutdown | HA notif + push gsm_koen |

## HA Sensoren gebruikt in ESPHome

| Sensor | ESPHome ID |
|--------|-----------|
| `sensor.inverter_active_power` | `pv_power` (W) |
| `sensor.batteries_state_of_capacity` | `battery_soc` (%) |
| `sensor.electricity_meter_power_production` | `grid_export` (kW) |
| `sensor.electricity_meter_power_consumption` | `grid_import` (kW) |
| `climate.w_eau_pool_heatpump` | target temp + mode |
| `binary_sensor.w_eau_pool_heatpump_fault` | fault detectie |

## BLE Display

```
MAC: 0D:D0:1E:CD:2F:D2
Component: pool_display (local, Arduino framework)
Toont: pool temp, pH, ORP
Zie: https://github.com/FirelightLokeren/esphome-pool-display
```

## HA Automatiseringen

- **PoolLab herinnering**: elke dag 20:00 → push als meting >= 3 dagen geleden
- **PoolLab push**: bij nieuwe meting → push met alle waterwaarden

## Pending

- [ ] pH probe bestellen (slope 86.2%, versleten)
- [ ] CYA verlagen via waterwissel
- [ ] Bootloader updaten via USB
- [ ] BLE display debug (placeholders nog niet zichtbaar)
- [ ] Pompsnelheid naar low toevoegen bij harde batterijstop
