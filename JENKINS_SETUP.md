# Jenkins Setup Guide för PVBattery Azure Deployment

## Förutsättningar

1. **Azure Resources:**
   - Azure Container Apps Environment
   - Azure Service Principal med rätt behörigheter
   - ⚠️ INGEN Azure Container Registry behövs - Docker image byggs på Jenkins och laddas upp direkt

2. **Jenkins Requirements:**
   - Docker installerat på Jenkins agent
   - Azure CLI installerat på Jenkins agent
   - Git plugin

## Steg 1: Skapa Azure Resources

### 1.1 Skapa Resource Group (om den inte finns)
```bash
az group create --name <your-rg> --location westeurope
```

### 1.2 Skapa Container Apps Environment
```bash
az containerapp env create \
  --name <your-env-name> \
  --resource-group <your-rg> \
  --location westeurope
```

### 1.3 Skapa Service Principal för Jenkins
```bash
az ad sp create-for-rbac --name jenkins-pvbattery --role contributor \
  --scopes /subscriptions/<subscription-id>/resourceGroups/<your-rg>

# Spara output:
# {
#   "appId": "xxx",      <- AZURE_CREDENTIALS_USR
#   "password": "xxx",   <- AZURE_CREDENTIALS_PSW
#   "tenant": "xxx"      <- AZURE_TENANT_ID
# }
```

## Steg 2: Konfigurera Jenkins Credentials

Gå till Jenkins > Manage Jenkins > Credentials > Add Credentials

### 2.1 Azure Service Principal Credentials
- **Kind:** Username with password
- **ID:** `azure-service-principal`
- **Username:** `appId` (från Service Principal)
- **Password:** `password` (från Service Principal)

## Steg 3: Uppdatera Jenkinsfile

Redigera `Jenkinsfile` och ändra följande variabler:

```groovy
RESOURCE_GROUP = 'your-resource-group'      // Din resource group
CONTAINER_APP_NAME = 'pvbattery-api'        // Namnet på din Container App
CONTAINER_APP_ENV = 'your-container-env'    // Din container app environment namn
AZURE_LOCATION = 'westeurope'               // Din Azure region
AZURE_TENANT_ID = 'your-tenant-id'          // Din Azure AD tenant ID (från Service Principal)
```

## Steg 4: Skapa Multibranch Pipeline i Jenkins

1. **New Item** > **Multibranch Pipeline**
2. **Branch Sources:**
   - Add source: Git/GitHub
   - Repository URL: `https://github.com/andersjInentri/PVBattery.git`
   - Credentials: (lägg till GitHub credentials om privat repo)
3. **Build Configuration:**
   - Mode: by Jenkinsfile
   - Script Path: `Jenkinsfile`
4. **Scan Multibranch Pipeline Triggers:**
   - ✅ Periodically if not otherwise run
   - Interval: 1 hour (eller efter behov)
5. **Branch Discovery:**
   - Strategy: All branches
   - Property strategy: All branches get the same properties
6. **Filter by name (with wildcards):**
   - Include: `azure-api`
   - Exclude: `main`

## Steg 5: Sätt Environment Variables i Container App (VIKTIGT!)

Efter första deploy från Jenkins, lägg till environment variables och secrets:

```bash
# Lägg till secrets
az containerapp secret set \
  --name pvbattery-api \
  --resource-group <your-rg> \
  --secrets \
    api-key=<din-säkra-api-key> \
    db-host=<din-db-host> \
    db-user=<din-db-user> \
    db-password=<din-db-password>

# Uppdatera med environment variables som refererar till secrets
az containerapp update \
  --name pvbattery-api \
  --resource-group <your-rg> \
  --set-env-vars \
    API_KEY=secretref:api-key \
    DB_HOST=secretref:db-host \
    DB_USER=secretref:db-user \
    DB_PASSWORD=secretref:db-password \
    DB_NAME=ha_db \
    DB_PORT=3306
```

## Steg 6: Testa Pipeline

1. Gå till din Multibranch Pipeline
2. Du bör se branchen `azure-api` automatiskt upptäckt
3. Klicka på `azure-api` branch
4. Klicka **Build Now**
5. Observera att första deploy kan ta 5-10 minuter

## Steg 7: Verifiera Deployment

Efter lyckad build, testa ditt API:

```bash
# Hämta Container App URL
az containerapp show --name pvbattery-api --resource-group <your-rg> --query properties.configuration.ingress.fqdn -o tsv

# Testa endpoints (byt ut URL och API-key)
curl https://pvbattery-api.westeurope.azurecontainerapps.io/health
curl -H "X-API-Key: <your-api-key>" https://pvbattery-api.westeurope.azurecontainerapps.io/ping
```

## Troubleshooting

### Build fails at Docker build
- Kontrollera att Docker är installerat och körs på Jenkins agent
- Verifiera att Jenkins-användaren har behörighet att köra Docker-kommandon
- Testa: `docker ps` från Jenkins agent

### Deploy fails med "az containerapp up"
- Kontrollera Service Principal har rätt behörigheter
- Verifiera att Azure CLI är installerat på Jenkins agent
- Kör `az login` test i Jenkins Shell

### Container app startar inte
- Kontrollera logs: `az containerapp logs show --name pvbattery-api --resource-group <your-rg> --tail 100`
- Verifiera environment variables och secrets

### Health check fails
- Kontrollera att port 8000 är korrekt i Container App
- Verifiera att `/health` endpoint fungerar lokalt först

## Nästa steg

1. **Automatisk triggering:** Lägg till GitHub webhook för automatisk build vid push
2. **Notifications:** Konfigurera email/Slack notifieringar vid build failure
3. **Staging environment:** Skapa en staging Container App för test
4. **Monitoring:** Lägg till Application Insights för monitoring

## Säkerhet

- ⚠️ Committa ALDRIG `.env` filen
- ⚠️ Använd alltid secrets för känslig data i Container Apps
- ⚠️ Rotera API keys och credentials regelbundet
- ⚠️ Begränsa Service Principal till minsta nödvändiga behörigheter
