-- Migration: Intensity metrics & RSE scoring for Morocco
-- Phase: Morocco Enhancement (post-Phase 7)
-- Adds: intensity_metrics table, rse_scores table, AMEE energy reporting fields

-- ── Intensity metrics reference data ─────────────────────────────────────────
-- Pre-defined intensity denominators for GRI 305-4 computation
-- Bureau/project can select the right denominator for their sector
CREATE TABLE IF NOT EXISTS intensity_denominators (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code        TEXT NOT NULL UNIQUE,  -- e.g. 'revenue_mad', 'm2_surface', 'tonne_produit'
    name        TEXT NOT NULL,
    unit        TEXT NOT NULL,
    description TEXT,
    sector_code TEXT  -- NULL = applicable to all sectors
);

INSERT INTO intensity_denominators (code, name, unit, description, sector_code) VALUES
    ('revenue_mad',       'Chiffre d''affaires (MAD)',       'MAD',           'Revenu total en Dirhams Marocains',                    NULL),
    ('revenue_mad_k',     'Chiffre d''affaires (kMAD)',      'kMAD',          'Revenu total en milliers de MAD',                      NULL),
    ('revenue_usd',       'Revenue (USD)',                    'USD',           'Total revenue in USD',                                 NULL),
    ('fte',               'Équivalents Temps Plein (ETP)',   'ETP',           'Nombre d''employés en ETP',                            NULL),
    ('m2_surface',        'Surface (m²)',                     'm²',            'Surface bâtie en m²',                                  'F41'),
    ('tonne_produit',     'Tonne de produit fini',           'tonne',         'Production totale en tonnes',                          NULL),
    ('tonne_ciment',      'Tonne de clinker/ciment',         'tonne_ciment',  'Production ciment — OCP, Holcim, Lafarge Maroc',       'C23'),
    ('tonne_phosphate',   'Tonne de phosphate brut',         'tonne_P2O5',    'Production phosphate OCP',                             'B08'),
    ('tonne_acier',       'Tonne d''acier brut',             'tonne_acier',   'Production acier — Sonasid',                           'C24'),
    ('passager_km',       'Passager-kilomètre',              'passager.km',   'Transport passagers — ONCF, CTM, RAM',                 'H49'),
    ('nuitee',            'Nuitée hôtelière',                'nuitée',        'Hôtellerie — nombre de nuitées',                       'I55'),
    ('kwh_produit',       'kWh d''énergie produite',         'kWh',           'Production d''électricité — ONEE, producteurs EnR',    'D35'),
    ('tep',               'Tonne Équivalent Pétrole (TEP)',  'TEP',           'Consommation énergétique en TEP — Bilan AMEE',         NULL)
ON CONFLICT (code) DO NOTHING;

-- ── Project intensity config ──────────────────────────────────────────────────
-- Stores the denominator + value chosen for GRI 305-4 intensity computation
CREATE TABLE IF NOT EXISTS project_intensity_config (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bureau_id            UUID NOT NULL REFERENCES bureaus(id) ON DELETE CASCADE,
    project_id           UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    denominator_type     TEXT NOT NULL REFERENCES intensity_denominators(code),
    denominator_value    NUMERIC(20,4) NOT NULL CHECK (denominator_value > 0),
    reporting_year       INTEGER NOT NULL,
    note                 TEXT,
    created_at           TIMESTAMPTZ DEFAULT now(),
    UNIQUE (project_id, denominator_type, reporting_year)
);

ALTER TABLE project_intensity_config ENABLE ROW LEVEL SECURITY;

CREATE POLICY "bureau_intensity_config" ON project_intensity_config
    USING (bureau_id = current_setting('app.bureau_id')::UUID);

-- ── RSE scores (Bourse de Casablanca — Rapport RSE) ─────────────────────────
-- Tracks RSE indicator scores per project/year for BVC-listed companies
-- Format follows the BVC RSE reporting template (2012+, updated 2019)
CREATE TABLE IF NOT EXISTS rse_scores (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bureau_id       UUID NOT NULL REFERENCES bureaus(id) ON DELETE CASCADE,
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    reporting_year  INTEGER NOT NULL,
    -- Pilier Environnemental (E)
    e_ghg_scope1    NUMERIC(12,4),  -- tCO2e Scope 1
    e_ghg_scope2    NUMERIC(12,4),  -- tCO2e Scope 2 (location-based)
    e_ghg_scope3    NUMERIC(12,4),  -- tCO2e Scope 3 (sélectif)
    e_energy_total  NUMERIC(12,4),  -- TEP énergie totale consommée
    e_energy_renew  NUMERIC(12,4),  -- TEP énergie renouvelable
    e_water_total   NUMERIC(12,4),  -- m³ eau consommée
    e_water_recycle NUMERIC(12,4),  -- m³ eau recyclée/réutilisée
    e_waste_total   NUMERIC(12,4),  -- tonnes déchets générés
    e_waste_recycle NUMERIC(12,4),  -- tonnes déchets valorisés
    -- Pilier Social (S)
    s_employees_total   INTEGER,    -- Effectif total ETP
    s_women_pct         NUMERIC(5,2), -- % femmes
    s_training_hours    NUMERIC(10,2), -- heures formation/ETP
    s_accidents_rate    NUMERIC(8,4),  -- taux de fréquence accidents
    -- Pilier Gouvernance (G)
    g_board_women_pct   NUMERIC(5,2),  -- % femmes au CA
    g_independent_pct   NUMERIC(5,2),  -- % administrateurs indépendants
    -- Meta
    methodology_ref TEXT DEFAULT 'BVC-RSE-2019',
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE (project_id, reporting_year)
);

ALTER TABLE rse_scores ENABLE ROW LEVEL SECURITY;

CREATE POLICY "bureau_rse_scores" ON rse_scores
    USING (bureau_id = current_setting('app.bureau_id')::UUID);

-- ── AMEE Bilan Énergétique fields ─────────────────────────────────────────────
-- For Loi 47-09 compliance: large consumers (> 500 TEP/an) must report to AMEE
ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS amee_reporting_required   BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS amee_entity_code          TEXT,   -- Code entité AMEE
    ADD COLUMN IF NOT EXISTS total_energy_tep          NUMERIC(12,4),  -- Consommation totale en TEP
    ADD COLUMN IF NOT EXISTS energy_intensity_tep_mad  NUMERIC(12,6);  -- TEP/MAD de CA

-- ── Additional Morocco emission factor categories (Loi 47-09 AMEE) ───────────
-- Add missing AMEE-specific energy categories to the Morocco factor set
-- These complement the Phase 5 migration data

-- Find the AMEE factor set ID dynamically
DO $$
DECLARE
    amee_set_id UUID;
    methodology_id_var UUID;
BEGIN
    SELECT id INTO methodology_id_var FROM methodologies WHERE code = 'AMEE' LIMIT 1;
    IF methodology_id_var IS NULL THEN RETURN; END IF;

    SELECT id INTO amee_set_id
    FROM factor_sets
    WHERE methodology_id = methodology_id_var
      AND name ILIKE '%AMEE%'
    LIMIT 1;
    IF amee_set_id IS NULL THEN RETURN; END IF;

    -- GPL (Gaz de Pétrole Liquéfié) — bouteille et vrac
    INSERT INTO emission_factors
        (factor_set_id, category, sub_category, gas, value, unit, activity_unit, scope, source, region)
    VALUES
        (amee_set_id, 'energie_gpl_vrac',    NULL, 'CO2e', 2.965, 'kgCO2e/kg',    'kg',     1, 'AMEE/ADEME Base Carbone v22', 'MA'),
        (amee_set_id, 'energie_charbon',      NULL, 'CO2e', 3.24,  'kgCO2e/kg',    'kg',     1, 'AMEE/ADEME Base Carbone v22', 'MA'),
        (amee_set_id, 'energie_coke_petrole', NULL, 'CO2e', 3.83,  'kgCO2e/kg',    'kg',     1, 'AMEE/ADEME Base Carbone v22', 'MA'),
        (amee_set_id, 'energie_bois_bûche',  NULL, 'CO2e', 0.028, 'kgCO2e/kg',    'kg',     1, 'AMEE/Base Carbone — biomasse', 'MA'),
        (amee_set_id, 'energie_gaz_naturel',  NULL, 'CO2e', 2.15,  'kgCO2e/kg',    'kg',     1, 'AMEE/ADEME Base Carbone v22', 'MA'),
        -- Energie thermique ONEE (vapeur, process)
        (amee_set_id, 'chaleur_onee',         NULL, 'CO2e', 0.85,  'kgCO2e/kWh_th','kWh_th', 1, 'AMEE Maroc estimation 2023', 'MA'),
        -- Transport interne site industriel
        (amee_set_id, 'transport_chariot_elev',NULL,'CO2e', 0.153, 'kgCO2e/km',    'km',     1, 'ADEME Base Carbone v22', 'MA'),
        (amee_set_id, 'transport_camion_12t', NULL, 'CO2e', 0.296, 'kgCO2e/km',    'km',     3, 'ADEME Base Carbone v22', 'MA'),
        (amee_set_id, 'transport_camion_26t', NULL, 'CO2e', 0.199, 'kgCO2e/km',    'km',     3, 'ADEME Base Carbone v22', 'MA'),
        -- Eau de process industriel
        (amee_set_id, 'eau_process_industriel',NULL,'CO2e', 0.198, 'kgCO2e/m3',    'm3',     3, 'AMEE Maroc estimation 2023', 'MA'),
        -- Production vapeur chaudière industrielle (fuel)
        (amee_set_id, 'vapeur_chaudiere_fuel',NULL, 'CO2e', 0.091, 'kgCO2e/kWh_th','kWh_th', 1, 'AMEE Maroc/ADEME', 'MA')
    ON CONFLICT DO NOTHING;

END $$;

-- ── Conversion factors for new units ─────────────────────────────────────────
-- conversion_type is one of ('NCV','density','oxidation','direct') per schema CHECK.
INSERT INTO conversion_factors
    (from_unit, to_unit, coefficient, conversion_type, source, effective_from)
VALUES
    -- GPL vrac: kg → MJ
    ('kg', 'MJ', 46.30,  'NCV',       'AMEE/CODIGAZ GPL vrac',     '2020-01-01'),
    -- Charbon: kg → TEP (energy content expressed as direct coefficient)
    ('tonne_charbon', 'TEP', 0.727, 'direct', 'AMEE Maroc/AIE 2023', '2020-01-01'),
    -- Gaz naturel: m3 → kg (densité standard 0°C 1atm)
    ('m3_gaz_naturel', 'kg', 0.717, 'density', 'CODIGAZ/GRTgaz', '2020-01-01'),
    -- kWh_th (thermique) → MJ
    ('kWh_th', 'MJ', 3.6, 'direct', 'SI', '2000-01-01'),
    -- tonne → kg
    ('tonne', 'kg', 1000.0, 'direct', 'SI', '2000-01-01'),
    -- Coke de pétrole: kg → MJ
    ('kg_coke_petrole', 'MJ', 32.48, 'NCV', 'ADEME Base Carbone v22', '2020-01-01')
ON CONFLICT DO NOTHING;

-- ── Indexes for performance ───────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_rse_scores_project ON rse_scores (project_id, reporting_year);
CREATE INDEX IF NOT EXISTS idx_intensity_config_project ON project_intensity_config (project_id);
