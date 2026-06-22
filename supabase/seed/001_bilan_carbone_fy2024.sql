-- ============================================================
-- Seed 001: Bilan Carbone / ADEME — FY2024
-- Reference data only. No tenant rows here.
--
-- Sources:
--   Base Carbone ADEME v22 (2024)
--   ONEE rapport annuel 2023 (grid electricity, Morocco)
--   IPCC AR5 (2014) — used by ADEME Base Carbone
--   IPCC AR6 WGI (2021) — stored separately for future use
--   ADEME Méthode Bilan Carbone v8
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- METHODOLOGY
-- ------------------------------------------------------------
INSERT INTO methodologies (id, name, version, region, description)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Bilan Carbone',
    '8.0',
    NULL,
    'Méthode Bilan Carbone® développée par l''ADEME. '
    'Applicable à toute organisation. '
    'Base Carbone® comme source de facteurs d''émission.'
);

-- ------------------------------------------------------------
-- FACTOR SETS
-- ------------------------------------------------------------

-- FY2023 (for effective-dating test: different year → different set)
INSERT INTO factor_sets (id, methodology_id, name, version, effective_from, effective_to,
                         gwp_basis, region, source_url)
VALUES (
    '00000000-0000-0000-0001-000000000001',
    '00000000-0000-0000-0000-000000000001',
    'Base Carbone ADEME FY2023',
    '21.0',
    '2023-01-01',
    '2023-12-31',
    'AR5',
    NULL,
    'https://base-empreinte.ademe.fr'
);

-- FY2024 (current)
INSERT INTO factor_sets (id, methodology_id, name, version, effective_from, effective_to,
                         gwp_basis, region, source_url)
VALUES (
    '00000000-0000-0000-0001-000000000002',
    '00000000-0000-0000-0000-000000000001',
    'Base Carbone ADEME FY2024',
    '22.0',
    '2024-01-01',
    NULL,
    'AR5',
    NULL,
    'https://base-empreinte.ademe.fr'
);

-- Morocco-specific factor set (inherits Bilan Carbone methodology)
INSERT INTO factor_sets (id, methodology_id, name, version, effective_from, effective_to,
                         gwp_basis, region, source_url)
VALUES (
    '00000000-0000-0000-0001-000000000003',
    '00000000-0000-0000-0000-000000000001',
    'Base Carbone ADEME FY2024 — Maroc',
    '22.0-MA',
    '2024-01-01',
    NULL,
    'AR5',
    'MA',
    'https://base-empreinte.ademe.fr'
);

-- ------------------------------------------------------------
-- GWP VALUES
-- AR5 (used by ADEME Base Carbone as of 2024)
-- AR6 (stored for future factor sets)
-- Source: IPCC AR5 WGI Table 8.7; AR6 WGI Table 7.SM.7
-- ------------------------------------------------------------

-- AR5, 100-year
INSERT INTO gwp_values (gas, gwp_basis, value, time_horizon_years, source) VALUES
('CO2',     'AR5', 1,     100, 'IPCC AR5 WGI Table 8.7'),
('CH4',     'AR5', 28,    100, 'IPCC AR5 WGI Table 8.7'),  -- fossil CH4 = 30, biogenic = 28; use 28 as base
('N2O',     'AR5', 265,   100, 'IPCC AR5 WGI Table 8.7'),
('HFC-134a','AR5', 1300,  100, 'IPCC AR5 WGI Table 8.7'),
('HFC-32',  'AR5', 677,   100, 'IPCC AR5 WGI Table 8.7'),
('SF6',     'AR5', 23500, 100, 'IPCC AR5 WGI Table 8.7'),
('NF3',     'AR5', 16100, 100, 'IPCC AR5 WGI Table 8.7'),
('PFC-14',  'AR5', 6630,  100, 'IPCC AR5 WGI Table 8.7');

-- AR6, 100-year
INSERT INTO gwp_values (gas, gwp_basis, value, time_horizon_years, source) VALUES
('CO2',     'AR6', 1,     100, 'IPCC AR6 WGI Table 7.SM.7'),
('CH4',     'AR6', 27.9,  100, 'IPCC AR6 WGI Table 7.SM.7'),  -- non-fossil; fossil = 29.8
('N2O',     'AR6', 273,   100, 'IPCC AR6 WGI Table 7.SM.7'),
('HFC-134a','AR6', 1526,  100, 'IPCC AR6 WGI Table 7.SM.7'),
('HFC-32',  'AR6', 771,   100, 'IPCC AR6 WGI Table 7.SM.7'),
('SF6',     'AR6', 25200, 100, 'IPCC AR6 WGI Table 7.SM.7'),
('NF3',     'AR6', 17400, 100, 'IPCC AR6 WGI Table 7.SM.7'),
('PFC-14',  'AR6', 7380,  100, 'IPCC AR6 WGI Table 7.SM.7');

-- ------------------------------------------------------------
-- CONVERSION FACTORS (unit graph)
-- These are directed edges: from_unit → to_unit via coefficient.
-- The kernel resolver traverses the graph multi-hop.
--
-- Basis: ADEME Base Carbone / IPCC / GREET
-- Units: L (litre), kg, t (tonne), MJ, kWh, m3 (m³ at 15°C 1atm)
-- ------------------------------------------------------------

-- -- DIRECT unit equivalences --------------------------------
INSERT INTO conversion_factors
    (from_unit, to_unit, coefficient, conversion_type, fuel_type, source, effective_from)
VALUES
-- Mass
('t',  'kg',  1000,         'direct', NULL, 'SI', '2020-01-01'),
('kg', 't',   0.001,        'direct', NULL, 'SI', '2020-01-01'),
-- Energy
('MJ', 'kWh', 0.2778,       'direct', NULL, 'SI (1 kWh = 3.6 MJ)', '2020-01-01'),
('kWh','MJ',  3.6,          'direct', NULL, 'SI', '2020-01-01'),
('GJ', 'MJ',  1000,         'direct', NULL, 'SI', '2020-01-01'),
('MJ', 'GJ',  0.001,        'direct', NULL, 'SI', '2020-01-01'),
-- Volume
('m3', 'L',   1000,         'direct', NULL, 'SI', '2020-01-01'),
('L',  'm3',  0.001,        'direct', NULL, 'SI', '2020-01-01');

-- -- NCV (Net Calorific Value): volume/mass → MJ ------------
-- Source: ADEME Base Carbone / PCR by fuel type
INSERT INTO conversion_factors
    (from_unit, to_unit, coefficient, conversion_type, fuel_type, source, effective_from)
VALUES
-- Diesel / Gazole (L → MJ; NCV ≈ 34.93 MJ/L)
('L',  'MJ',  34.93,        'NCV', 'diesel',       'ADEME BC v22 / IPCC 2006', '2024-01-01'),
-- Gasoline / Essence (L → MJ; NCV ≈ 31.82 MJ/L)
('L',  'MJ',  31.82,        'NCV', 'gasoline',     'ADEME BC v22 / IPCC 2006', '2024-01-01'),
-- LPG / GPL (L → MJ; NCV ≈ 23.40 MJ/L)
('L',  'MJ',  23.40,        'NCV', 'lpg',          'ADEME BC v22', '2024-01-01'),
-- Natural gas (m3 → MJ; NCV ≈ 34.02 MJ/m3 at 0°C; use 36.0 MJ/m3 at 15°C)
('m3', 'MJ',  34.02,        'NCV', 'natural_gas',  'ADEME BC v22 / GRTgaz', '2024-01-01'),
-- Heavy fuel oil / Fioul lourd (kg → MJ; NCV ≈ 40.40 MJ/kg)
('kg', 'MJ',  40.40,        'NCV', 'fuel_oil',     'ADEME BC v22', '2024-01-01'),
-- Coal / Charbon vapeur (kg → MJ; NCV ≈ 25.10 MJ/kg)
('kg', 'MJ',  25.10,        'NCV', 'coal',         'ADEME BC v22 / IPCC 2006', '2024-01-01'),
-- Kerosene / Kérosène (L → MJ; NCV ≈ 34.40 MJ/L)
('L',  'MJ',  34.40,        'NCV', 'kerosene',     'ADEME BC v22', '2024-01-01'),
-- Wood pellets / Granulés (kg → MJ; NCV ≈ 17.50 MJ/kg)
('kg', 'MJ',  17.50,        'NCV', 'wood_pellets', 'ADEME BC v22', '2024-01-01');

-- -- DENSITY: volume → mass -----------------------------------
INSERT INTO conversion_factors
    (from_unit, to_unit, coefficient, conversion_type, fuel_type, source, effective_from)
VALUES
-- Diesel (L → kg; density ≈ 0.832 kg/L)
('L',  'kg',  0.832,        'density', 'diesel',    'ADEME BC v22', '2024-01-01'),
-- Gasoline (L → kg; density ≈ 0.745 kg/L)
('L',  'kg',  0.745,        'density', 'gasoline',  'ADEME BC v22', '2024-01-01'),
-- LPG (L → kg; density ≈ 0.540 kg/L)
('L',  'kg',  0.540,        'density', 'lpg',       'ADEME BC v22', '2024-01-01'),
-- Heavy fuel oil (L → kg; density ≈ 0.950 kg/L)
('L',  'kg',  0.950,        'density', 'fuel_oil',  'ADEME BC v22', '2024-01-01'),
-- Kerosene (L → kg; density ≈ 0.800 kg/L)
('L',  'kg',  0.800,        'density', 'kerosene',  'ADEME BC v22', '2024-01-01');

-- -- OXIDATION fraction (fuel → CO2; dimensionless, applied before EF) --
-- These are carbon oxidation fractions — applied to mass of carbon, not activity.
-- Stored here for completeness; kernel uses them via conversion_type='oxidation'.
INSERT INTO conversion_factors
    (from_unit, to_unit, coefficient, conversion_type, fuel_type, source, effective_from)
VALUES
('kg_carbon', 'kg_co2', 3.6642, 'oxidation', NULL, 'stoichiometric (C→CO2)', '2020-01-01');

-- ------------------------------------------------------------
-- EMISSION FACTORS — Bilan Carbone FY2024 (AR5 GWP basis)
-- Using factor_set_id = FY2024 global set (00000000-0000-0000-0001-000000000002)
-- and Morocco set (00000000-0000-0000-0001-000000000003) for ONEE.
--
-- Values: kgCO2e per activity_unit
-- Source: ADEME Base Carbone v22 (2024), ONEE (2023)
-- ------------------------------------------------------------

-- -- Scope 1 — Stationary combustion -------------------------
INSERT INTO emission_factors
    (factor_set_id, category, sub_category, gas, value, unit, activity_unit,
     scope, scope2_type, region, source)
VALUES
-- Natural gas boilers (kgCO2e/MJ)
('00000000-0000-0000-0001-000000000002',
 'scope1_stationary', 'natural_gas_boiler',
 'CO2e', 0.05504, 'kgCO2e/MJ', 'MJ', 1, NULL, NULL,
 'ADEME BC v22 — Gaz naturel combustion stationnaire'),
-- Diesel generators / boilers (kgCO2e/MJ)
('00000000-0000-0000-0001-000000000002',
 'scope1_stationary', 'diesel_boiler',
 'CO2e', 0.07443, 'kgCO2e/MJ', 'MJ', 1, NULL, NULL,
 'ADEME BC v22 — Gazole combustion stationnaire'),
-- Heavy fuel oil (kgCO2e/MJ)
('00000000-0000-0000-0001-000000000002',
 'scope1_stationary', 'fuel_oil_boiler',
 'CO2e', 0.07744, 'kgCO2e/MJ', 'MJ', 1, NULL, NULL,
 'ADEME BC v22 — Fioul lourd combustion stationnaire'),
-- Coal (kgCO2e/MJ)
('00000000-0000-0000-0001-000000000002',
 'scope1_stationary', 'coal_boiler',
 'CO2e', 0.09412, 'kgCO2e/MJ', 'MJ', 1, NULL, NULL,
 'ADEME BC v22 — Charbon vapeur combustion stationnaire'),
-- LPG (kgCO2e/MJ)
('00000000-0000-0000-0001-000000000002',
 'scope1_stationary', 'lpg_boiler',
 'CO2e', 0.06321, 'kgCO2e/MJ', 'MJ', 1, NULL, NULL,
 'ADEME BC v22 — GPL combustion stationnaire');

-- -- Scope 1 — Mobile combustion ------------------------------
INSERT INTO emission_factors
    (factor_set_id, category, sub_category, gas, value, unit, activity_unit,
     scope, scope2_type, region, source)
VALUES
-- Diesel vehicles (kgCO2e/L)
('00000000-0000-0000-0001-000000000002',
 'scope1_mobile', 'diesel_vehicle',
 'CO2e', 2.5760, 'kgCO2e/L', 'L', 1, NULL, NULL,
 'ADEME BC v22 — Gazole transport routier'),
-- Gasoline vehicles (kgCO2e/L)
('00000000-0000-0000-0001-000000000002',
 'scope1_mobile', 'gasoline_vehicle',
 'CO2e', 2.2820, 'kgCO2e/L', 'L', 1, NULL, NULL,
 'ADEME BC v22 — Essence SP95 transport routier'),
-- LPG vehicles (kgCO2e/L)
('00000000-0000-0000-0001-000000000002',
 'scope1_mobile', 'lpg_vehicle',
 'CO2e', 1.6920, 'kgCO2e/L', 'L', 1, NULL, NULL,
 'ADEME BC v22 — GPL transport routier'),
-- Kerosene / aviation (kgCO2e/L)
('00000000-0000-0000-0001-000000000002',
 'scope1_mobile', 'kerosene_aviation',
 'CO2e', 2.5440, 'kgCO2e/L', 'L', 1, NULL, NULL,
 'ADEME BC v22 — Kérosène aviation');

-- -- Scope 2 — Electricity, location-based --------------------

-- France grid (location-based, FY2024)
INSERT INTO emission_factors
    (factor_set_id, category, sub_category, gas, value, unit, activity_unit,
     scope, scope2_type, region, source)
VALUES
('00000000-0000-0000-0001-000000000002',
 'scope2_electricity', 'grid_location',
 'CO2e', 0.0462, 'kgCO2e/kWh', 'kWh', 2, 'location', 'FR',
 'ADEME BC v22 — Réseau électrique France 2024 (AIB)');

-- Morocco grid (location-based, FY2024) — ONEE factor
-- Source: ONEE Rapport RSE / IEA Morocco 2023
-- Indicative value: 0.679 kgCO2e/kWh (mix réseau national 2023)
INSERT INTO emission_factors
    (factor_set_id, category, sub_category, gas, value, unit, activity_unit,
     scope, scope2_type, region, source, notes)
VALUES
('00000000-0000-0000-0001-000000000003',
 'scope2_electricity', 'grid_location',
 'CO2e', 0.6790, 'kgCO2e/kWh', 'kWh', 2, 'location', 'MA',
 'ONEE — facteur d''émission réseau électrique Maroc 2023',
 'Valeur indicative issue du rapport ONEE RSE 2023. '
 'Mise à jour annuelle recommandée. Validation expert requise.');

-- Morocco grid market-based (absence of guarantees of origin → use location factor as proxy)
INSERT INTO emission_factors
    (factor_set_id, category, sub_category, gas, value, unit, activity_unit,
     scope, scope2_type, region, source, notes)
VALUES
('00000000-0000-0000-0001-000000000003',
 'scope2_electricity', 'grid_market',
 'CO2e', 0.6790, 'kgCO2e/kWh', 'kWh', 2, 'market', 'MA',
 'ONEE — facteur d''émission réseau électrique Maroc 2023 (proxy marché)',
 'En l''absence de garanties d''origine au Maroc, le facteur marché '
 'utilise le facteur réseau comme valeur par défaut. '
 'Réviser si le client dispose de GO.');

COMMIT;
