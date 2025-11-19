-- Exempel-queries för power_economics views
-- Använd dessa för att analysera produktion, förbrukning och ekonomi

-- ============================================================================
-- 1. Visa dagens ekonomi i realtid
-- ============================================================================
SELECT
    ts_local,
    price_sek_kwh,
    pv_actual_kwh,
    pv_predicted_kwh,
    consumption_kwh,
    pv_actual_value_sek,
    consumption_cost_sek,
    net_result_sek,
    prediction_error_pct
FROM power_economics_summary_vw
WHERE date = CURDATE()
ORDER BY ts_local;

-- ============================================================================
-- 2. Dagens sammanfattning
-- ============================================================================
SELECT
    date,
    ROUND(SUM(pv_actual_kwh), 2) AS total_pv_kwh,
    ROUND(SUM(pv_predicted_kwh), 2) AS predicted_pv_kwh,
    ROUND(SUM(consumption_kwh), 2) AS total_consumption_kwh,
    ROUND(SUM(imported_kwh_q), 2) AS total_import_kwh,
    ROUND(SUM(exported_kwh_q), 2) AS total_export_kwh,
    ROUND(SUM(pv_actual_value_sek), 2) AS pv_value_sek,
    ROUND(SUM(consumption_cost_sek), 2) AS consumption_cost_sek,
    ROUND(SUM(export_revenue_sek), 2) AS export_revenue_sek,
    ROUND(SUM(import_cost_sek), 2) AS import_cost_sek,
    ROUND(SUM(net_result_sek), 2) AS net_result_sek,
    COUNT(*) AS quarters_count
FROM power_economics_summary_vw
WHERE date = CURDATE()
GROUP BY date;

-- ============================================================================
-- 3. Senaste 7 dagarnas sammanfattning
-- ============================================================================
SELECT
    date,
    ROUND(SUM(pv_actual_kwh), 2) AS total_pv_kwh,
    ROUND(SUM(consumption_kwh), 2) AS total_consumption_kwh,
    ROUND(SUM(pv_actual_value_sek), 2) AS pv_value_sek,
    ROUND(SUM(consumption_cost_sek), 2) AS consumption_cost_sek,
    ROUND(SUM(net_result_sek), 2) AS net_result_sek,
    ROUND(AVG(price_sek_kwh), 3) AS avg_price_sek_kwh,
    ROUND(AVG(prediction_error_pct), 1) AS avg_prediction_error_pct
FROM power_economics_summary_vw
WHERE date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
GROUP BY date
ORDER BY date DESC;

-- ============================================================================
-- 4. Bästa och sämsta timmarna för pris idag
-- ============================================================================
-- Bästa timmar (lägst pris) för att ladda batteri
SELECT
    hour,
    ROUND(AVG(price_sek_kwh), 3) AS avg_price_sek_kwh,
    ROUND(AVG(pv_actual_w), 0) AS avg_pv_w,
    'Laddning' AS recommended_action
FROM power_economics_summary_vw
WHERE date = CURDATE()
GROUP BY hour
ORDER BY avg_price_sek_kwh ASC
LIMIT 5;

-- Bästa timmar (högst pris) för att exportera
SELECT
    hour,
    ROUND(AVG(price_sek_kwh), 3) AS avg_price_sek_kwh,
    ROUND(AVG(pv_actual_w), 0) AS avg_pv_w,
    'Export' AS recommended_action
FROM power_economics_summary_vw
WHERE date = CURDATE()
GROUP BY hour
ORDER BY avg_price_sek_kwh DESC
LIMIT 5;

-- ============================================================================
-- 5. Prediction accuracy - dagens prestanda
-- ============================================================================
SELECT
    date,
    COUNT(*) AS total_quarters,
    ROUND(AVG(ABS(prediction_error_w)), 1) AS avg_absolute_error_w,
    ROUND(AVG(prediction_error_pct), 1) AS avg_error_pct,
    ROUND(STDDEV(prediction_error_pct), 1) AS stddev_error_pct,
    ROUND(MIN(prediction_error_pct), 1) AS min_error_pct,
    ROUND(MAX(prediction_error_pct), 1) AS max_error_pct
FROM power_economics_summary_vw
WHERE date = CURDATE()
    AND pv_actual_w IS NOT NULL
    AND pv_predicted_w IS NOT NULL
    AND pv_actual_w > 0  -- Bara när solen lyser
GROUP BY date;

-- ============================================================================
-- 6. Timvis produktion vs prediction för idag
-- ============================================================================
SELECT
    hour,
    ROUND(SUM(pv_actual_kwh), 2) AS actual_kwh,
    ROUND(SUM(pv_predicted_kwh), 2) AS predicted_kwh,
    ROUND(SUM(pv_predicted_kwh) - SUM(pv_actual_kwh), 2) AS diff_kwh,
    ROUND(AVG(price_sek_kwh), 3) AS avg_price,
    ROUND(SUM(pv_actual_value_sek), 2) AS actual_value_sek,
    ROUND(SUM(pv_predicted_value_sek), 2) AS predicted_value_sek
FROM power_economics_summary_vw
WHERE date = CURDATE()
GROUP BY hour
ORDER BY hour;

-- ============================================================================
-- 7. Månadssammanfattning
-- ============================================================================
SELECT
    DATE_FORMAT(date, '%Y-%m') AS month,
    ROUND(SUM(pv_actual_kwh), 2) AS total_pv_kwh,
    ROUND(SUM(consumption_kwh), 2) AS total_consumption_kwh,
    ROUND(SUM(imported_kwh_q), 2) AS total_import_kwh,
    ROUND(SUM(exported_kwh_q), 2) AS total_export_kwh,
    ROUND(SUM(pv_actual_value_sek), 2) AS pv_value_sek,
    ROUND(SUM(consumption_cost_sek), 2) AS consumption_cost_sek,
    ROUND(SUM(export_revenue_sek), 2) AS export_revenue_sek,
    ROUND(SUM(import_cost_sek), 2) AS import_cost_sek,
    ROUND(SUM(net_result_sek), 2) AS net_result_sek,
    ROUND(AVG(price_sek_kwh), 3) AS avg_price_sek_kwh
FROM power_economics_summary_vw
WHERE date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
GROUP BY DATE_FORMAT(date, '%Y-%m')
ORDER BY month DESC;

-- ============================================================================
-- 8. Bästa och sämsta prediction-dagar (senaste 30 dagarna)
-- ============================================================================
SELECT
    date,
    ROUND(SUM(pv_actual_kwh), 2) AS actual_kwh,
    ROUND(SUM(pv_predicted_kwh), 2) AS predicted_kwh,
    ROUND(AVG(ABS(prediction_error_pct)), 1) AS avg_abs_error_pct,
    COUNT(*) AS quarters_with_sun,
    CASE
        WHEN AVG(ABS(prediction_error_pct)) < 10 THEN 'Utmärkt'
        WHEN AVG(ABS(prediction_error_pct)) < 20 THEN 'Bra'
        WHEN AVG(ABS(prediction_error_pct)) < 30 THEN 'OK'
        ELSE 'Dålig'
    END AS accuracy_rating
FROM power_economics_summary_vw
WHERE date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
    AND pv_actual_w > 0
    AND pv_predicted_w IS NOT NULL
GROUP BY date
ORDER BY avg_abs_error_pct ASC;

-- ============================================================================
-- 9. Export/Import balans per dag
-- ============================================================================
SELECT
    date,
    ROUND(SUM(exported_kwh_q), 2) AS exported_kwh,
    ROUND(SUM(imported_kwh_q), 2) AS imported_kwh,
    ROUND(SUM(exported_kwh_q) - SUM(imported_kwh_q), 2) AS net_export_kwh,
    ROUND(SUM(export_revenue_sek), 2) AS export_revenue,
    ROUND(SUM(import_cost_sek), 2) AS import_cost,
    ROUND(SUM(export_revenue_sek) - SUM(import_cost_sek), 2) AS net_revenue,
    CASE
        WHEN SUM(exported_kwh_q) > SUM(imported_kwh_q) THEN 'Net Exporter'
        WHEN SUM(exported_kwh_q) < SUM(imported_kwh_q) THEN 'Net Importer'
        ELSE 'Balanced'
    END AS status
FROM power_economics_summary_vw
WHERE date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY date
ORDER BY date DESC;

-- ============================================================================
-- 10. Väder-påverkan på produktion
-- ============================================================================
SELECT
    date,
    ROUND(AVG(outdoor_temp), 1) AS avg_outdoor_temp,
    ROUND(SUM(pv_actual_kwh), 2) AS total_pv_kwh,
    ROUND(SUM(consumption_kwh), 2) AS total_consumption_kwh,
    SUM(CASE WHEN heating_was_on = 1 THEN 1 ELSE 0 END) AS quarters_heating_on,
    ROUND(AVG(price_sek_kwh), 3) AS avg_price
FROM power_economics_summary_vw
WHERE date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
    AND outdoor_temp IS NOT NULL
GROUP BY date
ORDER BY date DESC;
