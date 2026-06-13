# poolcontrol

ESPHome-gebaseerde poolautomatisering voor een 10m³ hexagonaal zwembad, gebouwd rond een ESP32 met Dingtian relay board, Atlas Scientific EZO probes, peristaltische doseerpompen en een W'Eau warmtepomp.

---

## Hardware overzicht

| Component | Model | Interface |
|---|---|---|
| Microcontroller | ESP32 (esp32dev) | — |
| Relay/IO board | Dingtian DTR0xx | SPI (GPIO13/14/15/16/32) |
| pH probe | Atlas Scientific EZO-pH | I2C 0x63 |
| ORP probe | Atlas Scientific EZO-ORP | I2C 0x62 |
| Temperatuur dak | Atlas Scientific EZO-RTD | I2C 0x66 |
| Temperatuur pool | Atlas Scientific EZO-RTD | I2C 0x67 |
| Flowmeter | Atlas Scientific EZO-FLO | I2C 0x68 |
| Chloor doseerpompe | Atlas Scientific EZO-PMP | I2C 0x64 |
| Omgevingstemp. | Dallas DS18B20 | 1-Wire GPIO0 |
| Warmtepomp | W'Eau WFI-005 | Local Tuya / HA |
| Circulatiepomp | Aquaforte Vario iSaver+ | Relais (3 snelheden) |
| Pool display | ACT1025 64×16 LED matrix | BLE (0D:D0:1E:CD:2F:D2) |

### I2C bus (SDA: GPIO4, SCL: GPIO5, 400kHz)

| Adres | Component |
|---|---|
| 0x62 | EZO-ORP |
| 0x63 | EZO-pH |
| 0x64 | EZO-PMP (chloor doseerpompe) |
| 0x66 | EZO-RTD (daktemperatuur) |
| 0x67 | EZO-RTD (pooltemperatuur) |
| 0x68 | EZO-FLO (flowmeter) |

### Relais indeling (Dingtian)

| Relais | Functie |
|---|---|
| R1 | Niet gebruikt |
| R2 | Circulatiepomp UIT |
| R3 | Circulatiepomp LOW |
| R4 | Circulatiepomp MED |
| R5 | Circulatiepomp HIGH |
| R6 | Niet gebruikt |
| R7 | 3-weg klep bypass dak |
| R8 | Niet gebruikt |

### Ingangen (Dingtian)

| Ingang | Functie |
|---|---|
| I1 | 3-weg klep positie DAK |
| I2 | 3-weg klep positie POOL |
| I3 | Waterstand HOOG |
| I4 | Waterstand NORMAAL |
| I5 | Waterstand LAAG |
| I6 | ACK 6-weg klep |
| I7 | ACK skimmer |
| I8 | Niet gebruikt |

---

## Package structuur

De configuratie is opgesplitst in packages voor overzichtelijkheid:

```
poolcontrol.yaml              # Hoofdconfiguratie
poolcontrol_files/
  core.yaml                   # WiFi info, uptime, hostname, restart
  heatpump.yaml               # Warmtepomp logica, PV/batterij sturing
  dingtian.yaml               # Relay board, ingangen, pompsturing
  display.yaml                # BLE LED display (ACT1025)
  components/                 # Lokale ESPHome externe componenten
```

### Globals gedefinieerd in poolcontrol.yaml

De volgende globals worden door de packages gebruikt en moeten in `poolcontrol.yaml` staan:

| ID | Type | Gebruik |
|---|---|---|
| `flow_reference` | float | Referentieflow voor trend detectie |
| `flow_low_since` | uint32_t | Tijdstempel lage flow detectie |
| `water_level_high_notified` | bool | Waterstand hoog notificatie status |

---

## Functies

### Circulatiepomp
- **Auto modus**: pompsnelheid gestuurd op basis van deltaTemp (dak−pool) en omgevingstemperatuur
- **Manual modus**: manuele snelheidsinstelling via HA
- **Vacuum modus**: forceert HIGH snelheid + klep op Pool gedurende 60 minuten, daarna terug naar auto
- **Flow bescherming**: bij flow < 0.5 L/min worden 3 herstartpogingen gedaan; na 3 mislukte pogingen → emergency shutdown met HA-notificatie

### Warmtepomp
- **Auto sturing**: warmtepomp AAN bij voldoende PV-overschot (>1.5 kW export) of volle batterij (SOC >80%)
- **Minimum runtime**: 30 minuten voor uitschakeling toegelaten
- **Batterijbeveiliging**: bij SOC-daling ≥3% zonder PV → warmtepomp UIT, pomp naar LOW
- **Forced heating**: manuele override via HA-schakelaar

### 3-weg klep
- Automatisch aangestuurd op basis van deltaTemp (dak−pool)
- Bij delta > 5°C → bypass DAK (water via dakpanelen)
- Bij delta < 1°C → bypass POOL (water omzeilt dakpanelen)

### Waterstand
- Drie niveausensoren: HOOG, NORMAAL, LAAG
- Bij HOOG: herhalende HA-notificatie elke 5 minuten zolang hoog

### Chloor dosering (EZO-PMP)
- **Automatisch**: doseert op basis van ORP-waarde
  - Drempelwaarden instelbaar via HA (standaard: doseer onder 650 mV, stop boven 750 mV)
  - Minimum wachttijd tussen doses instelbaar (standaard: 30 min)
  - Maximum dagvolume instelbaar (standaard: 500 mL)
- **Manueel**: doseer een instelbaar volume via HA-knop
- **Veiligheid**: dosering stopt automatisch als pomp niet bereikbaar (I2C error)
- **Volume tracking**: persistent totaalvolume (overleeft reboots), dagvolume (reset om middernacht)

### Pool display (ACT1025)
- BLE LED matrix 64×16 pixels
- Toont: pooltemperatuur, pH, ORP
- Instelbare helderheid via HA

---

## Kalibratie

### pH (EZO-pH)

Drievoudige kalibratie (laag/midden/hoog):

1. Druk **Clear pH Calibration** — wis oude kalibratie
2. Dompel probe in pH 7 buffer → druk **pH 7 Calibrate**
3. Dompel probe in pH 10 buffer → druk **pH 10 Calibrate**
4. Dompel probe in pH 4 buffer → druk **pH 4 Calibrate**
5. Optioneel: druk **Query pH slope** om kalibratiekwaliteit te controleren (ideaal: >95%)

### ORP (EZO-ORP)

Enkelvoudige kalibratie:

1. Druk **Clear Orp Calibration** — wis oude kalibratie
2. Dompel probe in 225 mV ORP-standaardoplossing
3. Druk **Orp 225mV Calibrate**

### Chloor doseerpompe (EZO-PMP)

1. **Primen**: stel Manueel Volume in op 200 mL, druk **Chloor Doseer Manueel** — herhaal tot slang vrij is van lucht
2. **Wis kalibratie**: druk **Chloor Wis Kalibratie**
3. **Kalibreren**:
   - Stel Manueel Volume in op 10 mL
   - Houd maatcilinder onder de uitgang
   - Druk **Chloor Doseer Manueel**
   - Meet het werkelijk gepompte volume
   - Vul gemeten volume in bij **Chloor Kalibratie Volume (gemeten)**
   - Druk **Chloor Stel Kalibratie In**
4. **Verifiëren**: doe een tweede run van 10 mL en controleer of het volume klopt

> ⚠️ Kalibreer met water voor je de chloorlijn aansluit. Water en natriumhypochloriet hebben een vergelijkbare viscositeit, de afwijking is verwaarloosbaar.

---

## Installatie

### Vereisten
- Home Assistant met ESPHome add-on
- Secrets in `/config/esphome/secrets.yaml`:

```yaml
wifi_ssid: "jouw_ssid"
wifi_password: "jouw_wachtwoord"
ap_password: "fallback_wachtwoord"
api_key: "jouw_api_key"
```

### Flashen

**Eerste keer** (via USB):
```bash
esphome run poolcontrol.yaml
```

**Daarna via OTA** vanuit ESPHome Dashboard → **Install** → **Wirelessly**

### I2C adres wijzigen (EZO modules)

Om een EZO-module naar een nieuw adres te verhuizen:

1. Koppel alle andere modules los van de I2C bus (enkel de te wijzigen module aangesloten)
2. Voeg tijdelijk een button toe in de YAML:
```yaml
button:
  - platform: template
    name: "Wijzig I2C adres"
    on_press:
      - lambda: id(ezo_sensor_id).send_custom("I2C,<decimaal_adres>");
```
3. Flash, druk de knop in, verwijder de button en flash opnieuw
4. Pas het `address:` veld aan in de YAML

> Het EZO-commando gebruikt **decimaal** adressen: 0x64 = 100, 0x67 = 103, enz.

---

## Home Assistant entiteiten

### Sensoren
| Entiteit | Eenheid | Beschrijving |
|---|---|---|
| pH | pH | Zuurtegraad pool |
| ORP | mV | Redoxpotentiaal |
| pool temp | °C | Poolwatertemperatuur (EZO-RTD) |
| Roof temp | °C | Daktemperatuur (EZO-RTD) |
| Delta temperature | °C | Dak − Pool temperatuur |
| Pump Flow Rate | L/min | Berekende flowsnelheid |
| Vrije Chloor (met temp) | ppm | Berekend vrij chloor (ORP/pH/temp) |
| Omgeving | °C | Omgevingstemperatuur (DS18B20) |
| Chloor Gedoseerd Vandaag | mL | Dagvolume chloor |
| Chloor Totaal Volume Gedoseerd (persistent) | mL | Totaalvolume (reboot-bestendig) |

### Schakelaars
| Entiteit | Beschrijving |
|---|---|
| Automatisch Doseren | Chloor auto-dosering aan/uit |
| Forced heating | Warmtepomp manueel forceren |

### Selecties
| Entiteit | Opties |
|---|---|
| Pump Mode | auto / manual / vacuum |
| Pump speed | off / low / med / high |

---

## Verwante repositories

- [poolcontrol](https://github.com/FirelightLokeren/poolcontrol) — deze repository
- [esphome-pool-display](https://github.com/FirelightLokeren/esphome-pool-display) — ACT1025 BLE display component
