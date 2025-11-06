# PVBattery
## Purpose
Predict how many Watt the solar panel will produce coming day. Production is predicted on each quarter of an hour. The thought in the long run is to be able to control when to save energy to the battery and when to sell energy to the net. This also depends on when the battery might be fully loaded and when it is, according to price, is better to sell energy directly without saving to battery.

## Description
I'm sending data from Home Assistant (HA). By that data is collected and thus in some extent preprocessed in HA.

## Final thoughts
Unsure if to use AI to estimate coming PV Generation or to makes use of home assistant sensors to calculate how best to utilize a solar battery.

## Model Evaluation: Check and Act (After Plan and Do)
### Holdout validation
80%: 
20%: 

### Cross-Validation (K-Fold)
Avoid that the modle is to specialized on the testdata

### Performance measure
Classification: Accuracy, how precise is the model
Regression: 

## Installation
Install requirements.txt. See the file requirements.txt for installation details, what is going to be installed.
<code>
pip install -r requirements.txt
</code>