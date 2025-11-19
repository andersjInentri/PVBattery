-- View: power_economics_quarter_vw
-- Kombinerar prediction, faktisk förbrukning och Nordpool-priser
-- Beräknar ekonomiskt värde för varje kvartstimme

CREATE OR REPLACE VIEW power_economics_quarter_vw AS
SELECT
    -- Tidsstämpel (från power_quarter_avg som bas, annars prediction)
    COALESCE(pq.ts_local, p.ts) AS ts_local,

    -- Nordpool-priser
    np.start_local AS nordpool_start,
    np.value_ore_kwh,
    np.currency,

    -- PV-produktion (faktisk och prediction)
    pq.pv_power_w_avg AS pv_power_actual_w,
    p.pv_power_w_avg AS pv_power_predicted_w,

    -- Konvertera till kWh för kvarts-perioden (W * 0.25h / 1000)
    (pq.pv_power_w_avg * 0.25 / 1000) AS pv_kwh_actual,
    (p.pv_power_w_avg * 0.25 / 1000) AS pv_kwh_predicted,

    -- Förbrukning
    pq.consumption_w_avg,
    pq.household_load_power_w_avg,
    pq.load_power_w_avg,
    (pq.consumption_w_avg * 0.25 / 1000) AS consumption_kwh,

    -- Batteri
    pq.battery_power_w_avg,
    pq.battery_level_pct_avg,

    -- Import/Export
    pq.export_power_w_avg,
    pq.imported_kwh_q,
    pq.exported_kwh_q,

    -- Ekonomiska värden - Faktisk produktion
    CASE
        WHEN pq.pv_power_w_avg IS NOT NULL AND np.value_ore_kwh IS NOT NULL THEN
            (pq.pv_power_w_avg * 0.25 / 1000) * (np.value_ore_kwh / 100)
        ELSE NULL
    END AS pv_value_actual_sek,

    -- Ekonomiska värden - Predikterad produktion
    CASE
        WHEN p.pv_power_w_avg IS NOT NULL AND np.value_ore_kwh IS NOT NULL THEN
            (p.pv_power_w_avg * 0.25 / 1000) * (np.value_ore_kwh / 100)
        ELSE NULL
    END AS pv_value_predicted_sek,

    -- Kostnad för förbrukning
    CASE
        WHEN pq.consumption_w_avg IS NOT NULL AND np.value_ore_kwh IS NOT NULL THEN
            (pq.consumption_w_avg * 0.25 / 1000) * (np.value_ore_kwh / 100)
        ELSE NULL
    END AS consumption_cost_sek,

    -- Intäkt från export
    CASE
        WHEN pq.exported_kwh_q IS NOT NULL AND np.value_ore_kwh IS NOT NULL THEN
            pq.exported_kwh_q * (np.value_ore_kwh / 100)
        ELSE NULL
    END AS export_revenue_sek,

    -- Kostnad för import
    CASE
        WHEN pq.imported_kwh_q IS NOT NULL AND np.value_ore_kwh IS NOT NULL THEN
            pq.imported_kwh_q * (np.value_ore_kwh / 100)
        ELSE NULL
    END AS import_cost_sek,

    -- Prediction error (endast när både faktisk och prediction finns)
    CASE
        WHEN pq.pv_power_w_avg IS NOT NULL AND p.pv_power_w_avg IS NOT NULL THEN
            p.pv_power_w_avg - pq.pv_power_w_avg
        ELSE NULL
    END AS prediction_error_w,

    -- Prediction error i procent
    CASE
        WHEN pq.pv_power_w_avg IS NOT NULL AND p.pv_power_w_avg IS NOT NULL AND pq.pv_power_w_avg > 0 THEN
            ((p.pv_power_w_avg - pq.pv_power_w_avg) / pq.pv_power_w_avg) * 100
        ELSE NULL
    END AS prediction_error_pct,

    -- Övrig användbar data från power_quarter_local
    pq.daily_imported_kwh,
    pq.daily_exported_kwh,
    pq.cost_ack_daily,
    pq.reward_ack_daily,
    pq.acktank_switch_was_on,
    pq.acktank_topp_temp_avg,
    pq.kitchen_outdoor_temp_avg,
    pq.heating_was_on,
    pq.kitchen_indoor_temp_avg,
    pq.ems_mode_selection_raw_max,
    pq.battery_forced_charge_discharge_cmd_raw_min,
    pq.sample_count,
    pq.source,

    -- Metadata
    pq.created_at AS power_created_at,
    pq.updated_at AS power_updated_at,
    p.updated_ts AS prediction_updated_at

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