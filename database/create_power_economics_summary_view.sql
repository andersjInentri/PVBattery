-- View: power_economics_summary_vw
-- Förenklad view med fokus på ekonomiska värden och prediction-jämförelse

CREATE OR REPLACE VIEW power_economics_summary_vw AS
SELECT
    -- Tidsstämpel
    COALESCE(pq.ts_local, p.ts) AS ts_local,
    DATE(COALESCE(pq.ts_local, p.ts)) AS date,
    HOUR(COALESCE(pq.ts_local, p.ts)) AS hour,

    -- Nordpool-pris
    np.value_ore_kwh AS price_ore_kwh,
    (np.value_ore_kwh / 100) AS price_sek_kwh,
    np.currency,

    -- PV-produktion
    pq.pv_power_w_avg AS pv_actual_w,
    p.pv_power_w_avg AS pv_predicted_w,
    (pq.pv_power_w_avg * 0.25 / 1000) AS pv_actual_kwh,
    (p.pv_power_w_avg * 0.25 / 1000) AS pv_predicted_kwh,

    -- PV-värde i SEK
    ROUND((pq.pv_power_w_avg * 0.25 / 1000) * (np.value_ore_kwh / 100), 2) AS pv_actual_value_sek,
    ROUND((p.pv_power_w_avg * 0.25 / 1000) * (np.value_ore_kwh / 100), 2) AS pv_predicted_value_sek,

    -- Förbrukning
    pq.consumption_w_avg AS consumption_w,
    (pq.consumption_w_avg * 0.25 / 1000) AS consumption_kwh,
    ROUND((pq.consumption_w_avg * 0.25 / 1000) * (np.value_ore_kwh / 100), 2) AS consumption_cost_sek,

    -- Import/Export
    pq.imported_kwh_q,
    pq.exported_kwh_q,
    ROUND(pq.exported_kwh_q * (np.value_ore_kwh / 100), 2) AS export_revenue_sek,
    ROUND(pq.imported_kwh_q * (np.value_ore_kwh / 100), 2) AS import_cost_sek,

    -- Batteri
    pq.battery_level_pct_avg,
    pq.battery_power_w_avg,

    -- Prediction accuracy (endast när båda finns)
    CASE
        WHEN pq.pv_power_w_avg IS NOT NULL AND p.pv_power_w_avg IS NOT NULL THEN
            p.pv_power_w_avg - pq.pv_power_w_avg
        ELSE NULL
    END AS prediction_error_w,

    CASE
        WHEN pq.pv_power_w_avg IS NOT NULL AND p.pv_power_w_avg IS NOT NULL AND pq.pv_power_w_avg > 0 THEN
            ROUND(((p.pv_power_w_avg - pq.pv_power_w_avg) / pq.pv_power_w_avg) * 100, 1)
        ELSE NULL
    END AS prediction_error_pct,

    -- Nettoresultat för kvartalet (export - import)
    ROUND(
        COALESCE(pq.exported_kwh_q * (np.value_ore_kwh / 100), 0) -
        COALESCE(pq.imported_kwh_q * (np.value_ore_kwh / 100), 0),
        2
    ) AS net_result_sek,

    -- Väderdata och systemstatus
    pq.kitchen_outdoor_temp_avg AS outdoor_temp,
    pq.heating_was_on,
    pq.acktank_switch_was_on

FROM
    prediction p

    -- LEFT JOIN prediction så vi får alla historiska värden från power_quarter_avg
    LEFT JOIN power_quarter_avg pq
        ON p.ts = pq.ts_local 

    -- LEFT JOIN nordpool_quarter_local för priser
    LEFT JOIN nordpool_quarter_local np
        ON p.ts = np.start_local


ORDER BY
    ts_local DESC;
