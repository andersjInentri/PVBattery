# PVBattery
## Purpose
For each quarter of an hour the coming day predict how many Watt the solar panel will produce.

Solar Panel Production is predicted on each quarter of an hour. The thought in the long run is to be able to control when to save energy to the battery and when to sell energy to the net. This also depends on when the battery might be fully loaded and when it is, according to price, better to sell energy directly without first filling up the battery.

## Description
Once every day, Home Assistant (HA) collects electricity prices for the coming day. The prices are unique for every 15 minutes, that is 4 prices for every hour, 96 unique prices for each day. The prices are stored in a MariaDB-table. HA also collects next day weather, unique for every hour. To that
HA stores sun position for each hour, in elevation and azimuth. A view, to make it easy to read, is made on top of the tables. As important values are collected once every hour, the solar panel production will also be for a complete hour, but the result is for every quarter. Note the difference between watt and kWh. Solar panels are producing momentarily watt, so it will be an estimation how many watts. It is though possible to collect the predicted momentarily production and summarize how many kWh solar panels are producing for each hour and each day.

By knowing the suns position, how cloudy it is supposed to be and the previous production from solar panels due to conditions, it should be possible to estimate how much the solar panels are going to produce the coming day, both in watt and kWh. In the database Azimuth is in degree but the app is recalculating to sinus and cosinus.

**Summary of existing values for the project**  
Between 14:00 and 15:00 the day before, HA is preparing the following data for each 15 min, the coming day:
- **Timestamp** Date and time for the row.
- **Price / kWh in SEK** Quarterly value. The variable price and does not include price for the net. Price can be negative but mostly positive. 
- **Cloudiness in percent** Hourly value. 0 = clear sky, 100 = most cloudy. High impact on PV Power.
- **Pressure HPA** Hourly value. Barometric pressure in Hecto Pascal.
- **Rain / Snow precipation in mm** Hourly value. How much rain or snow will fall, in mm.
- **Temperature** Hourly value. Outdoor temperature precipiation in Celcius. Lower impact on PV Power.
- **Condition** Hourly value. Precipation of an overall weather condition. This value is taken from the symbol, used on the html, and translated in to a number.
- **Sun elevation** Hourly value. The suns vertical elevation from my address. Has a significant impact of PV Power.
- **Sun azimuth** Hourly value. The suns horizontal direction from my hous, think compass direction. Has a significant impact of PV Power. This is an issue because it goes from 360 to 1 in south, it is re-calculated to cosinus and sinus in order to be useable.              
- **Is daylight** Quarterly Value (another source than Sun Position!). Can be 0 or 1.
- **Power from Solar Panels** Quaterly value that HA writes at the actual time it has happened. This means that the value is 0 when the row is created but filled in at the actual date and time it has occured.

**Uncertainty**  
Note that the **cloudiness** is in it self a predicated value. It will probably not be the same cloudiness a whole hour and it might change from weather forecast to actual value.

## Restriction
**Note that this file can only be executed between 15:00 and 23:59!** This because next days weather is retrieved 14:00.

## Installation
Install requirements.txt. See the file requirements.txt for installation details, what is needed to be installed.
```bash
pip install -r requirements.txt
```

## How to run
Create an .env file and add the following parameters.

```bash
DB_HOST=inentriqdb.tallas.se
DB_PORT=3306
DB_NAME=ha_db
DB_USER=[username]
DB_PASSWORD=[password]
```

The prediction, executed by main.py, is for how many watt the solar panels will generate tomorrow. It checks if the needed pre-requisite data has been fetched in the database before predicting next days PV. It writes the values to an Excel-file, prediction.xlsx, in the sheet Pred_<tomorrow date>. Run the file with

```bash
python main.py
```

Alternative, if you do not use a .env file then execute with

```bash
python main.py DB_HOST=inentriqdb.tallas.se DB_PORT=3306 DB_NAME=ha_db DB_USER=[username] DB_PASSWORD=[password]
```

The file data_io, reads the today data from the database which would be the actual value of how many watt the solar panels have generated today. The file writes the values to the Excel-file prediction.xlsx in the sheet Utfall_<today date>.
```bash
python data_io.py 
or
python data_io.py DB_HOST=inentriqdb.tallas.se DB_PORT=3306 DB_NAME=ha_db DB_USER=[username] DB_PASSWORD=[password]
```

## Final thoughts
Unsure if to use AI to estimate coming PV Generation or to makes use of home assistant sensors to calculate how best to utilize a solar battery.

## Model Evaluation: Check and Act (After Plan and Do)
### Holdout validation
80%: 
20%: 

### Cross-Validation (K-Fold)
Avoid that the model is to specialized on the testdata
I think it is an issue that I have data only from October. First I run this with these Features
```bash
FEATURES  = ["weather_cloud_pct", "weather_temperature", "weather_precip_mm", "weather_pressure_hpa", "weather_condition_text", "sun_azimuth_deg", "sun_elevation_deg", "is_daylight"]
```
though I think some values have more influence than others, that is more weight. The sun position is the first and then weather_cloud_pct together with weather_condition_text

### Performance measure
Classification: Accuracy, how precise is the model
Regression: 

