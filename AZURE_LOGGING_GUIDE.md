# Azure Container Apps Logging Guide

## Översikt
Den här guiden beskriver hur du sätter upp logging för PVBattery API i Azure Container Apps.

## Alternativ 1: Log Analytics (Enklaste - Rekommenderad)

Azure Container Apps använder redan Log Analytics workspace för att samla in loggar. Du behöver bara aktivera det och sedan kan du visa loggarna.

### Steg 1: Aktivera Log Analytics i Container App

Kör följande Azure CLI-kommando för att se din nuvarande konfiguration:

```bash
az containerapp show \
  --name pvbattery-api \
  --resource-group rg-inentriq-aca \
  --query "properties.configuration.ingress"
```

### Steg 2: Hitta Log Analytics Workspace ID

```bash
# Hitta environment
az containerapp env show \
  --name inentriq-env \
  --resource-group rg-inentriq-aca \
  --query "properties.appLogsConfiguration.logAnalyticsConfiguration.customerId"
```

### Steg 3: Visa loggar i Azure Portal

1. Gå till **Azure Portal** → https://portal.azure.com
2. Sök efter **"Log Analytics workspaces"**
3. Välj workspace som är kopplad till `inentriq-env`
4. Gå till **Logs** i vänstermenyn
5. Kör följande KQL-query:

```kql
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "pvbattery-api"
| project TimeGenerated, Log_s, ContainerName_s
| order by TimeGenerated desc
| take 100
```

### Alternativ: Använd Azure CLI för att visa loggar

```bash
# Visa de senaste loggarna
az containerapp logs show \
  --name pvbattery-api \
  --resource-group rg-inentriq-aca \
  --follow
```

---

## Alternativ 2: Application Insights (Avancerad - För Production)

Application Insights ger dig:
- Detaljerad telemetri
- Request/response tracking
- Performance metrics
- Custom events och metrics
- Dependency tracking (DB queries, HTTP calls)

### Steg 1: Skapa Application Insights Resource

```bash
# Skapa Application Insights
az monitor app-insights component create \
  --app pvbattery-insights \
  --location swedencentral \
  --resource-group rg-inentriq-aca \
  --application-type web

# Hämta instrumentation key
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app pvbattery-insights \
  --resource-group rg-inentriq-aca \
  --query instrumentationKey -o tsv)

echo "Instrumentation Key: $INSTRUMENTATION_KEY"
```

### Steg 2: Uppdatera requirements.txt

Lägg till Application Insights SDK:

```txt
applicationinsights==0.11.10
opencensus-ext-azure==1.1.13
opencensus-ext-flask==0.8.0
```

### Steg 3: Uppdatera api.py

```python
from flask import Flask, request, jsonify
from applicationinsights.flask.ext import AppInsights
import logging
import os

app = Flask(__name__)

# Konfigurera Application Insights
app.config['APPINSIGHTS_INSTRUMENTATIONKEY'] = os.getenv('APPINSIGHTS_INSTRUMENTATIONKEY')
appinsights = AppInsights(app)

# Konfigurera logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.after_request
def after_request(response):
    appinsights.flush()
    return response

# ... resten av koden
```

### Steg 4: Uppdatera Jenkinsfile

Lägg till APPINSIGHTS_INSTRUMENTATIONKEY i environment variables:

```groovy
stage('Deploy to Azure Container Apps') {
    steps {
        script {
            sh """
                az containerapp update \\
                    --name ${CONTAINER_APP_NAME} \\
                    --resource-group ${RESOURCE_GROUP} \\
                    --image ${FULL_IMAGE_NAME}:${IMAGE_TAG} \\
                    --set-env-vars \\
                        "DB_HOST=inentriqdb.tallas.se" \\
                        "DB_PORT=3306" \\
                        "DB_NAME=ha_db" \\
                        "DB_USER=\$DB_CREDENTIALS_USR" \\
                        "DB_PASSWORD=\$DB_CREDENTIALS_PSW" \\
                        "API_KEY=\$API_KEY_SECRET" \\
                        "APPINSIGHTS_INSTRUMENTATIONKEY=\$APPINSIGHTS_KEY"
            """
        }
    }
}
```

### Steg 5: Visa loggar i Application Insights

1. Gå till **Azure Portal** → **Application Insights** → **pvbattery-insights**
2. Välj **Logs** eller **Transaction search**
3. Kör KQL-queries:

```kql
// Visa alla requests
requests
| where timestamp > ago(1h)
| project timestamp, name, url, resultCode, duration
| order by timestamp desc

// Visa alla exceptions
exceptions
| where timestamp > ago(24h)
| project timestamp, type, outerMessage, innermostMessage
| order by timestamp desc

// Visa custom traces
traces
| where timestamp > ago(1h)
| project timestamp, message, severityLevel
| order by timestamp desc
```

---

## Alternativ 3: Förbättra stdout/stderr logging (Snabbast att implementera)

Detta alternativ förbättrar din nuvarande logging utan att lägga till externa tjänster.

### Uppdatera main.py

Lägg till strukturerad logging:

```python
import logging
import sys
from datetime import datetime

# Konfigurera logging för stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Startar PVBattery...")

    try:
        # Step 1: READ DATA
        logger.info("Hämtar data från databas...")
        raw_dataframe = read_ai_features_view()
        logger.info(f"Hämtade {len(raw_dataframe)} rader från databas")

        # ... resten av koden

        logger.info(f"Förväntad produktion imorgon: {total_kWh:.2f} kWh")
        logger.info("PVBattery körning slutförd framgångsrikt")

    except Exception as e:
        logger.error(f"Fel i PVBattery: {e}", exc_info=True)
        raise
```

### Uppdatera api.py

```python
import logging

# Konfigurera logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.route('/predict', methods=['POST'])
def predict():
    logger.info("Received prediction request")
    start_time = time.time()

    try:
        # ... din kod

        logger.info(f"Prediction completed in {time.time() - start_time:.2f}s")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
```

---

## Rekommendation: Steg-för-steg implementation

### Fas 1: Börja med stdout logging (Idag - 15 min)
1. Uppdatera main.py och api.py med strukturerad logging
2. Deploy till Azure
3. Använd `az containerapp logs show --follow` för att se loggar

### Fas 2: Aktivera Log Analytics queries (Nästa vecka - 5 min)
1. Använd Azure Portal för att hitta Log Analytics workspace
2. Testa KQL-queries för att filtrera och analysera loggar

### Fas 3: Lägg till Application Insights (Vid behov - 30 min)
1. Skapa Application Insights resource
2. Lägg till SDK i requirements.txt
3. Uppdatera api.py med AppInsights integration
4. Uppdatera Jenkinsfile med APPINSIGHTS_INSTRUMENTATIONKEY

---

## Snabbreferens: Azure CLI Logging Commands

```bash
# Visa live logs (följ loggarna)
az containerapp logs show \
  --name pvbattery-api \
  --resource-group rg-inentriq-aca \
  --follow

# Visa de senaste 100 raderna
az containerapp logs show \
  --name pvbattery-api \
  --resource-group rg-inentriq-aca \
  --tail 100

# Visa replicas (för att se vilka containers som körs)
az containerapp replica list \
  --name pvbattery-api \
  --resource-group rg-inentriq-aca

# Visa container app status
az containerapp show \
  --name pvbattery-api \
  --resource-group rg-inentriq-aca \
  --query "properties.{status:runningStatus,replicas:template.scale}"
```

---

## Troubleshooting

### Problem: Ser inga loggar

**Lösning 1:** Kontrollera att container startar korrekt
```bash
az containerapp revision list \
  --name pvbattery-api \
  --resource-group rg-inentriq-aca
```

**Lösning 2:** Kontrollera container status
```bash
az containerapp show \
  --name pvbattery-api \
  --resource-group rg-inentriq-aca \
  --query "properties.latestRevisionName"
```

### Problem: Loggar försvinner efter en stund

**Lösning:** Log Analytics workspace har en retention policy. Öka retention period:
```bash
az monitor log-analytics workspace update \
  --resource-group rg-inentriq-aca \
  --workspace-name <workspace-name> \
  --retention-time 30  # dagar
```

---

## Nästa steg

Välj vilket alternativ du vill börja med och jag kan hjälpa dig implementera det!
