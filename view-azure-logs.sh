#!/bin/bash
# Script för att visa Azure Container Apps loggar

echo "=== Azure Container Apps Logs ==="
echo "Container: pvbattery-api"
echo "Resource Group: rg-inentriq-aca"
echo ""
echo "Välj ett alternativ:"
echo "1) Visa de senaste 100 raderna"
echo "2) Följ loggar live (Ctrl+C för att avsluta)"
echo "3) Visa de senaste 500 raderna"
echo ""
read -p "Ditt val (1-3): " choice

case $choice in
  1)
    echo "Hämtar senaste 100 raderna..."
    az containerapp logs show \
      --name pvbattery-api \
      --resource-group rg-inentriq-aca \
      --tail 100
    ;;
  2)
    echo "Följer loggar live (tryck Ctrl+C för att avsluta)..."
    az containerapp logs show \
      --name pvbattery-api \
      --resource-group rg-inentriq-aca \
      --follow
    ;;
  3)
    echo "Hämtar senaste 500 raderna..."
    az containerapp logs show \
      --name pvbattery-api \
      --resource-group rg-inentriq-aca \
      --tail 500
    ;;
  *)
    echo "Ogiltigt val"
    exit 1
    ;;
esac
