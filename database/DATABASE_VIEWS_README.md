# Database Views - Power Economics

Två MariaDB views för att analysera solcellsproduktion, förbrukning och ekonomi tillsammans med Nordpool-priser.

## Views

### 1. `power_economics_quarter_vw` (Detaljerad)

Komplett view med alla kolumner från alla tabeller plus beräknade ekonomiska värden.

**Tabeller som kombineras:**
- `power_quarter_avg` (bas) - Faktisk aggregerad data per kvartstimme
- `prediction` (LEFT JOIN) - Predikterad PV-produktion
- `nordpool_quarter_local` (LEFT JOIN) - Elpriser per kvartstimme

**Viktiga beräknade kolumner:**
- `pv_value_actual_sek` - Värdet av faktisk PV-produktion i SEK
- `pv_value_predicted_sek` - Värdet av predikterad PV-produktion i SEK
- `consumption_cost_sek` - Kostnad för förbrukning i SEK
- `export_revenue_sek` - Intäkt från exporterad el i SEK
- `import_cost_sek` - Kostnad för importerad el i SEK
- `prediction_error_w` - Skillnad mellan prediction och faktiskt (W)
- `prediction_error_pct` - Prediction-fel i procent

### 2. `power_economics_summary_vw` (Förenklad)

Enklare view med fokus på ekonomi och nyckeltal. Perfekt för dashboards och rapporter.

**Samma datakällor som ovan, men med:**
- Färre kolumner (endast de viktigaste)
- Rundade värden för bättre läsbarhet
- Extra tidsfält (date, hour) för enklare gruppering
- Nettoresultat per kvartstimme

## Installation

Kör SQL-filerna i din MariaDB-databas:

```bash
# Detaljerad view
mysql -u username -p database_name < create_power_economics_view.sql

# Förenklad view
mysql -u username -p database_name < create_power_economics_summary_view.sql
```

Eller direkt i MySQL/MariaDB:

```sql
SOURCE /path/to/create_power_economics_view.sql;
SOURCE /path/to/create_power_economics_summary_view.sql;
```

## Användning

### Exempel 1: Dagens ekonomi

```sql
SELECT
    ts_local,
    price_sek_kwh,
    pv_actual_kwh,
    consumption_kwh,
    pv_actual_value_sek,
    consumption_cost_sek,
    net_result_sek
FROM power_economics_summary_vw
WHERE date = CURDATE()
ORDER BY ts_local;
```

### Exempel 2: Dagens sammanfattning

```sql
SELECT
    date,
    ROUND(SUM(pv_actual_kwh), 2) AS total_pv_kwh,
    ROUND(SUM(consumption_kwh), 2) AS total_consumption_kwh,
    ROUND(SUM(net_result_sek), 2) AS net_result_sek
FROM power_economics_summary_vw
WHERE date = CURDATE();
```

### Exempel 3: Prediction accuracy

```sql
SELECT
    date,
    ROUND(AVG(ABS(prediction_error_pct)), 1) AS avg_error_pct
FROM power_economics_summary_vw
WHERE date = CURDATE()
    AND pv_actual_w > 0
GROUP BY date;
```

Se [power_economics_example_queries.sql](power_economics_example_queries.sql) för fler exempel!

## Beräkningar

### Energi (kWh per kvartstimme)

```
kWh = (Watt × 0.25 timmar) / 1000
```

Exempel: 2000W × 0.25h / 1000 = 0.5 kWh

### Pris (SEK)

Nordpool-priset är i öre/kWh, så:

```
SEK = kWh × (öre/kWh / 100)
```

Exempel: 0.5 kWh × (50 öre/kWh / 100) = 0.25 SEK

### Ekonomiska formler

**PV-värde (faktiskt):**
```sql
(pv_power_w_avg * 0.25 / 1000) * (value_ore_kwh / 100)
```

**Förbrukningskostnad:**
```sql
(consumption_w_avg * 0.25 / 1000) * (value_ore_kwh / 100)
```

**Export-intäkt:**
```sql
exported_kwh_q * (value_ore_kwh / 100)
```

**Import-kostnad:**
```sql
imported_kwh_q * (value_ore_kwh / 100)
```

**Nettoresultat:**
```sql
export_revenue_sek - import_cost_sek
```

### Prediction Error

**Absolut fel (W):**
```sql
pv_power_predicted_w - pv_power_actual_w
```

**Relativt fel (%):**
```sql
((pv_power_predicted_w - pv_power_actual_w) / pv_power_actual_w) * 100
```

## JOIN-logik

Views använder **LEFT JOIN** från `power_quarter_avg` som bas:

```sql
FROM power_quarter_avg pq
LEFT JOIN prediction p ON pq.ts_local = p.ts
LEFT JOIN nordpool_quarter_local np ON pq.ts_local = np.start_local
```

Detta betyder:
- Alla historiska rader från `power_quarter_avg` inkluderas
- Prediction-data läggs till om det finns (NULL annars)
- Nordpool-priser läggs till om det finns (NULL annars)

### Tidsmatchning

Eftersom `power_quarter_avg` redan har normaliserade timestamps (`ts_local`) kan vi matcha direkt:

```sql
ON pq.ts_local = p.ts
```

Mycket enklare än att använda `DATE_FORMAT`!

## Kolumnbeskrivningar

### Tidsrelaterade
- `ts_local` - Lokal tidsstämpel (från power_quarter_local eller prediction)
- `date` - Datum (endast summary-view)
- `hour` - Timme 0-23 (endast summary-view)

### Produktion
- `pv_actual_w` / `pv_power_actual_w` - Faktisk PV-produktion (W)
- `pv_predicted_w` / `pv_power_predicted_w` - Predikterad PV-produktion (W)
- `pv_actual_kwh` - Faktisk produktion för kvartalet (kWh)
- `pv_predicted_kwh` - Predikterad produktion för kvartalet (kWh)

### Förbrukning
- `consumption_w` / `consumption_w_avg` - Förbrukning (W)
- `consumption_kwh` - Förbrukning för kvartalet (kWh)
- `household_load_power_w_avg` - Hushållsförbrukning (W)

### Batteri
- `battery_level_pct_avg` - Batterinivå (%)
- `battery_power_w_avg` - Batterieffekt, + = laddning, - = urladdning (W)

### Import/Export
- `imported_kwh_q` - Importerad el detta kvartal (kWh)
- `exported_kwh_q` - Exporterad el detta kvartal (kWh)

### Priser
- `value_ore_kwh` - Nordpool-pris (öre/kWh)
- `price_sek_kwh` - Nordpool-pris (SEK/kWh)
- `currency` - Valuta (vanligtvis SEK)

### Ekonomiska värden
- `pv_actual_value_sek` - Värde av faktisk PV-produktion (SEK)
- `pv_predicted_value_sek` - Värde av predikterad PV-produktion (SEK)
- `consumption_cost_sek` - Kostnad för förbrukning (SEK)
- `export_revenue_sek` - Intäkt från export (SEK)
- `import_cost_sek` - Kostnad för import (SEK)
- `net_result_sek` - Nettoresultat: export - import (SEK)

### Prediction Accuracy
- `prediction_error_w` - Fel i W (predicted - actual)
- `prediction_error_pct` - Fel i % ((predicted - actual) / actual * 100)

### Väder och system
- `outdoor_temp` / `kitchen_outdoor_temp_avg` - Utomhustemperatur (°C)
- `heating_was_on` - Uppvärmning aktiv (0/1)
- `acktank_switch_was_on` - Varmvattenberedare aktiv (0/1)

## Performance tips

### Indexering

För bästa performance, se till att ha index på:

```sql
-- power_quarter_avg
CREATE INDEX idx_ts_local ON power_quarter_avg(ts_local);

-- prediction
CREATE INDEX idx_ts ON prediction(ts);

-- nordpool_quarter_local
CREATE INDEX idx_start_local ON nordpool_quarter_local(start_local);
```

### Datumsökning

Använd alltid `date = CURDATE()` eller `date >= DATE_SUB(...)` istället för att söka på `ts_local` direkt, eftersom `date` är beräknat från `ts_local` och kan dra nytta av index.

**Bra:**
```sql
WHERE date = CURDATE()
```

**Dåligt:**
```sql
WHERE DATE(ts_local) = CURDATE()  -- Kan inte använda index
```

### Materialized Views

Om viewsna blir långsamma med mycket data, överväg att skapa en materialized view (cron-job som skriver till en tabell):

```sql
CREATE TABLE power_economics_cache AS
SELECT * FROM power_economics_summary_vw
WHERE date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY);
```

## Grafana Integration

Använd dessa queries i Grafana:

### Panel 1: Dagens produktion vs prediction

```sql
SELECT
    ts_local AS time,
    pv_actual_w AS "Actual",
    pv_predicted_w AS "Predicted"
FROM power_economics_summary_vw
WHERE date = CURDATE()
ORDER BY ts_local;
```

### Panel 2: Dagens ekonomi

```sql
SELECT
    ts_local AS time,
    COALESCE(pv_actual_value_sek, 0) AS "PV Value",
    COALESCE(consumption_cost_sek, 0) AS "Consumption Cost",
    COALESCE(net_result_sek, 0) AS "Net Result"
FROM power_economics_summary_vw
WHERE date = CURDATE()
ORDER BY ts_local;
```

### Panel 3: Prediction accuracy över tid

```sql
SELECT
    date AS time,
    AVG(ABS(prediction_error_pct)) AS "Avg Error %"
FROM power_economics_summary_vw
WHERE date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
    AND pv_actual_w > 0
GROUP BY date
ORDER BY date;
```

## Troubleshooting

### Problem: NULL-värden i ekonomiska kolumner

**Orsak:** Saknas data i `nordpool_quarter_local` eller `power_quarter_avg`.

**Lösning:** Kontrollera att:
1. Nordpool-data importeras korrekt
2. Timestamps matchar mellan tabellerna (`pq.ts_local = np.start_local`)
3. Timestamps är i samma format och timezone

### Problem: Prediction-data saknas

**Orsak:** Prediction körs endast för framtida dagar.

**Lösning:** Detta är normalt. Gamla dagar har ingen prediction-data.

### Problem: Långsam query

**Orsak:** Stora datamängder utan index eller dålig query.

**Lösning:**
1. Lägg till index (se Performance tips)
2. Begränsa datumintervall
3. Använd summary-view istället för detaljerad view
4. Överväg materialized view för historisk data

## Underhåll

### Rensa gamla data

Om databasen växer för mycket:

```sql
-- Ta bort data äldre än 2 år från power_quarter_avg
DELETE FROM power_quarter_avg
WHERE ts_local < DATE_SUB(CURDATE(), INTERVAL 2 YEAR);

-- Ta bort gamla predictions (behålls vanligtvis kort tid)
DELETE FROM prediction
WHERE ts < DATE_SUB(NOW(), INTERVAL 7 DAY);
```

### Vacuum/Optimize

Efter stora raderingar:

```sql
OPTIMIZE TABLE power_quarter_avg;
OPTIMIZE TABLE prediction;
OPTIMIZE TABLE nordpool_quarter_local;
```
