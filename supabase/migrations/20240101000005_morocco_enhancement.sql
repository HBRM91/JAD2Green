-- ============================================================
-- Migration 005: Morocco Deep Enhancement
-- Adds Morocco-specific methodologies, emission factors, and
-- sector categories aligned with:
--   • Loi 99-12 (Charte Nationale Environnement)
--   • SNDD 2030 (Stratégie Nationale Développement Durable)
--   • NDC Maroc 2030 (Nationally Determined Contribution)
--   • ISO 14064-1:2018
--   • GRI 305 Emissions Standard
--   • GHG Protocol Corporate Standard
--   • AMEE (Agence Marocaine Efficacité Energétique)
--   • Rapport RSE (Bourse de Casablanca, obligatoire sociétés cotées)
-- ============================================================

BEGIN;

-- ============================================================
-- 1. ADDITIONAL METHODOLOGIES
-- ============================================================

-- ISO 14064-1:2018 — Organizational GHG Quantification
-- Widely referenced in Morocco for formal verification projects
INSERT INTO methodologies (id, name, version, region, description)
VALUES (
    '00000000-0000-0000-0000-000000000002',
    'ISO 14064-1',
    '2018',
    NULL,
    'Norme internationale ISO 14064-1:2018 — Quantification et déclaration des '
    'émissions et suppressions de GES au niveau organisationnel. '
    'Compatible avec le Protocole GES et utilisable au Maroc pour vérification tierce.'
);

-- GHG Protocol Corporate Standard
-- International standard aligned with Morocco''s NDC reporting framework
INSERT INTO methodologies (id, name, version, region, description)
VALUES (
    '00000000-0000-0000-0000-000000000003',
    'GHG Protocol Corporate Standard',
    '2015',
    NULL,
    'Protocole GES — Norme d''entreprise et de chaîne de valeur (World Resources Institute). '
    'Standard international utilisé pour le CDP, TCFD et alignement NDC Maroc.'
);

-- GRI 305 — Emissions (part of GRI Standards suite)
-- Mandatory for listed companies on Bourse de Casablanca (Rapport RSE since 2012)
INSERT INTO methodologies (id, name, version, region, description)
VALUES (
    '00000000-0000-0000-0000-000000000004',
    'GRI 305 Émissions',
    '2016',
    NULL,
    'Standard GRI 305:2016 Émissions. Obligatoire pour les sociétés cotées à la Bourse '
    'de Casablanca dans le cadre du Rapport RSE (depuis 2012). '
    'Couvre GES Scope 1, 2, 3, ozone, particules fines.'
);

-- AMEE Bilan Énergétique — Morocco specific
-- Mandatory energy audit for large consumers (>500 TEP/year) under Loi 47-09
INSERT INTO methodologies (id, name, version, region, description)
VALUES (
    '00000000-0000-0000-0000-000000000005',
    'AMEE Bilan Énergétique',
    '2.0',
    'MA',
    'Bilan énergétique selon le référentiel AMEE (Agence Marocaine pour l''Efficacité '
    'Energétique). Obligatoire pour les grands consommateurs (>500 TEP/an) en vertu '
    'de la Loi 47-09 relative à l''efficacité énergétique. '
    'Conversion automatique en émissions GES via le facteur ONEE.'
);

-- ============================================================
-- 2. MOROCCO FACTOR SETS FOR NEW METHODOLOGIES
-- ============================================================

-- ISO 14064-1 Morocco FY2024
INSERT INTO factor_sets (id, methodology_id, name, version, effective_from, effective_to,
                         gwp_basis, region, source_url)
VALUES (
    '00000000-0000-0000-0002-000000000001',
    '00000000-0000-0000-0000-000000000002',
    'ISO 14064-1 — Maroc FY2024',
    '1.0-MA-2024',
    '2024-01-01',
    NULL,
    'AR6',
    'MA',
    'https://www.iso.org/standard/66453.html'
);

-- GHG Protocol Morocco FY2024
INSERT INTO factor_sets (id, methodology_id, name, version, effective_from, effective_to,
                         gwp_basis, region, source_url)
VALUES (
    '00000000-0000-0000-0003-000000000001',
    '00000000-0000-0000-0000-000000000003',
    'GHG Protocol — Maroc FY2024',
    '1.0-MA-2024',
    '2024-01-01',
    NULL,
    'AR6',
    'MA',
    'https://ghgprotocol.org'
);

-- GRI 305 Morocco FY2024
INSERT INTO factor_sets (id, methodology_id, name, version, effective_from, effective_to,
                         gwp_basis, region, source_url)
VALUES (
    '00000000-0000-0000-0004-000000000001',
    '00000000-0000-0000-0000-000000000004',
    'GRI 305 — Maroc FY2024',
    '1.0-MA-2024',
    '2024-01-01',
    NULL,
    'AR6',
    'MA',
    'https://www.globalreporting.org/standards/media/1012/gri-305-emissions-2016.pdf'
);

-- AMEE Morocco FY2024
INSERT INTO factor_sets (id, methodology_id, name, version, effective_from, effective_to,
                         gwp_basis, region, source_url)
VALUES (
    '00000000-0000-0000-0005-000000000001',
    '00000000-0000-0000-0000-000000000005',
    'AMEE Bilan Énergétique — Maroc FY2024',
    '2.0-MA-2024',
    '2024-01-01',
    NULL,
    'AR5',
    'MA',
    'https://www.amee.ma'
);

-- ============================================================
-- 3. MOROCCO-SPECIFIC EMISSION FACTORS
-- ============================================================
-- All Morocco-specific factors go into the Bilan Carbone MA set
-- (id = 00000000-0000-0000-0001-000000000003) and the new MA sets.

-- ─────────────────────────────────────────────────────────────
-- 3A. MOROCCAN FUELS (not in ADEME standard Base Carbone)
-- ─────────────────────────────────────────────────────────────

-- Butane (bouteilles de gaz, usage très répandu au Maroc)
-- La bouteille de 12kg est le standard résidentiel/PME au Maroc
-- Source: IPCC 2006 + ADEME; facteur proche du GPL
INSERT INTO emission_factors
    (factor_set_id, category, sub_category, gas, value, unit, activity_unit,
     scope, scope2_type, region, source, notes)
VALUES
('00000000-0000-0000-0001-000000000003',
 'scope1_stationary', 'butane_boiler',
 'CO2e', 0.06321, 'kgCO2e/MJ', 'MJ', 1, NULL, 'MA',
 'ADEME BC v22 / IPCC 2006 — Butane combustion stationnaire',
 'Butane (C4H10) facteur similaire au GPL. '
 'Très utilisé au Maroc résidentiel et PME (bouteilles 12kg, 3kg).'),
-- Butane direct en kg (sans conversion énergétique)
('00000000-0000-0000-0001-000000000003',
 'scope1_stationary', 'butane_boiler_kg',
 'CO2e', 2.9820, 'kgCO2e/kg', 'kg', 1, NULL, 'MA',
 'IPCC 2006 Vol.2 Table 1.4 — Butane combustion',
 'Facteur direct kg butane → kgCO2e. NCV butane = 45.74 MJ/kg.'),
-- Gasoil professionnel (subventionné, secteur industriel/BTP Maroc)
('00000000-0000-0000-0001-000000000003',
 'scope1_mobile', 'gasoil_professionnel',
 'CO2e', 2.5760, 'kgCO2e/L', 'L', 1, NULL, 'MA',
 'ADEME BC v22 — Gazole (gasoil professionnel, teneur soufre 50ppm Maroc)',
 'Gasoil professionnel Maroc (ex-S50). Facteur identique au diesel standard.'),
-- Fuel domestique (fioul domestique, utilisé en industrie et collectivités MA)
('00000000-0000-0000-0001-000000000003',
 'scope1_stationary', 'fuel_domestique',
 'CO2e', 0.07453, 'kgCO2e/MJ', 'MJ', 1, NULL, 'MA',
 'ADEME BC v22 — Fioul domestique',
 'Fuel domestique utilisé dans les chaudières des établissements collectifs au Maroc.');

-- ─────────────────────────────────────────────────────────────
-- 3B. TRANSPORT MOROCCO
-- ─────────────────────────────────────────────────────────────

INSERT INTO emission_factors
    (factor_set_id, category, sub_category, gas, value, unit, activity_unit,
     scope, scope2_type, region, source, notes)
VALUES
-- ONCF Train Maroc (passager, kgCO2e/passager.km)
-- Source: ONCF Rapport RSE 2023 + calcul basé mix électrique ONEE
('00000000-0000-0000-0001-000000000003',
 'scope3_transport', 'oncf_train_passager',
 'CO2e', 0.0082, 'kgCO2e/passager.km', 'passager.km', 3, NULL, 'MA',
 'ONCF Rapport RSE 2023 — facteur électricité train Maroc',
 'Train électrique ONCF: facteur ONEE 0.679 kgCO2e/kWh × ~12 Wh/passager.km. '
 'Inclus Tanger-Casablanca, BHNS. Mettre à jour annuellement.'),
-- ONCF Fret (kgCO2e/tonne.km)
('00000000-0000-0000-0001-000000000003',
 'scope3_transport', 'oncf_train_fret',
 'CO2e', 0.0280, 'kgCO2e/tonne.km', 'tonne.km', 3, NULL, 'MA',
 'ONCF / ADEME Fret ferroviaire Maroc',
 'Fret ferroviaire ONCF. Valeur approchée; mise à jour recommandée.'),
-- Grand taxi Maroc (kgCO2e/passager.km)
('00000000-0000-0000-0001-000000000003',
 'scope3_transport', 'grand_taxi_passager',
 'CO2e', 0.0840, 'kgCO2e/passager.km', 'passager.km', 3, NULL, 'MA',
 'Calcul ADEME BC v22 adapté Maroc — Grand taxi',
 'Grand taxi (Mercedes 190D, Peugeot 504) — taux occupation moyen 5 passagers. '
 'Consommation ≈ 8L/100km diesel → 206 gCO2/km ÷ 5 passagers.'),
-- Petit taxi Maroc (kgCO2e/passager.km)
('00000000-0000-0000-0001-000000000003',
 'scope3_transport', 'petit_taxi_passager',
 'CO2e', 0.1210, 'kgCO2e/passager.km', 'passager.km', 3, NULL, 'MA',
 'Calcul ADEME BC v22 adapté Maroc — Petit taxi',
 'Petit taxi urbain (Dacia Logan, Fiat Siena) — taux occupation moyen 2 passagers. '
 'Consommation ≈ 7L/100km essence → 160 gCO2/km ÷ 1.5 passagers.'),
-- CTM/Supratours bus longue distance
('00000000-0000-0000-0001-000000000003',
 'scope3_transport', 'bus_longue_distance',
 'CO2e', 0.0320, 'kgCO2e/passager.km', 'passager.km', 3, NULL, 'MA',
 'ADEME BC v22 adapté — Autocar longue distance Maroc',
 'Autocar classe III (CTM, Supratours). Consommation ≈ 25L/100km diesel '
 'pour 50 passagers → 64 gCO2/passager.km.'),
-- Transport urbain BHNS (Bus à Haut Niveau de Service)
('00000000-0000-0000-0001-000000000003',
 'scope3_transport', 'bhns_urbain',
 'CO2e', 0.0680, 'kgCO2e/passager.km', 'passager.km', 3, NULL, 'MA',
 'Calcul local Maroc — BHNS (M''Dina Bus, Alsa)',
 'Bus diesel urbain (Casablanca, Rabat, Marrakech). Taux remplissage moyen 35%.'),
-- Royal Air Maroc (vols domestiques, kgCO2e/passager.km)
('00000000-0000-0000-0001-000000000003',
 'scope3_transport', 'vol_domestique_maroc',
 'CO2e', 0.2550, 'kgCO2e/passager.km', 'passager.km', 3, NULL, 'MA',
 'ADEME BC v22 — Court courrier (< 1000 km) court-courrier',
 'Vols intérieurs Royal Air Maroc. Inclus radiative forcing (×2). '
 'Casablanca-Marrakech, Casa-Agadir, etc.'),
-- Vol international depuis/vers Maroc (moyen courrier)
('00000000-0000-0000-0001-000000000003',
 'scope3_transport', 'vol_international_moyen_courrier',
 'CO2e', 0.1860, 'kgCO2e/passager.km', 'passager.km', 3, NULL, 'MA',
 'ADEME BC v22 — Moyen courrier (1000-3500 km) économique',
 'Vols internationaux Maroc-Europe. Ex: Casablanca-Paris (2100 km).'),
-- Transport maritime (import/export portuaire)
('00000000-0000-0000-0001-000000000003',
 'scope3_transport', 'transport_maritime_conteneur',
 'CO2e', 0.0110, 'kgCO2e/tonne.km', 'tonne.km', 3, NULL, 'MA',
 'ADEME BC v22 — Transport maritime conteneurisé',
 'Porte-conteneurs. Très pertinent Maroc (port Tanger Med, Casablanca). '
 'Ex: import depuis Chine → 1 tonne × 10,000 km = 110 kgCO2e.');

-- ─────────────────────────────────────────────────────────────
-- 3C. DÉCHETS (Waste) — Très pertinent au Maroc
-- ─────────────────────────────────────────────────────────────
-- Le Maroc génère ~8 millions tonnes/an de déchets solides
-- Traitement: ~60% décharges contrôlées, 25% décharges sauvages

INSERT INTO emission_factors
    (factor_set_id, category, sub_category, gas, value, unit, activity_unit,
     scope, scope2_type, region, source, notes)
VALUES
-- Décharge contrôlée avec récupération biogaz (STEP biogaz)
('00000000-0000-0000-0001-000000000003',
 'scope3_dechets', 'decharge_controlee_biogaz',
 'CO2e', 0.4700, 'kgCO2e/kg', 'kg', 3, NULL, 'MA',
 'ADEME IPCC 2006 — Décharge contrôlée avec torchère biogaz',
 'Décharge de classe II (Médiouna Casablanca, Oum Azza Rabat). '
 'Avec récupération/torchère biogaz. Valeur ADEME Base Carbone.'),
-- Décharge sans récupération (situation la plus courante au Maroc)
('00000000-0000-0000-0001-000000000003',
 'scope3_dechets', 'decharge_sans_biogaz',
 'CO2e', 0.9200, 'kgCO2e/kg', 'kg', 3, NULL, 'MA',
 'IPCC 2006 Vol.5 Ch.3 — Décharge sans récupération biogaz',
 'Décharge de classe II sans récupération biogaz. '
 'Situation fréquente hors grandes villes au Maroc.'),
-- Décharge sauvage (décharge non contrôlée — dchour, périphéries urbaines)
('00000000-0000-0000-0001-000000000003',
 'scope3_dechets', 'decharge_sauvage',
 'CO2e', 1.1500, 'kgCO2e/kg', 'kg', 3, NULL, 'MA',
 'IPCC 2006 — Décharge ouverte / décharge sauvage',
 'Décharge illicite / dépôt sauvage. Facteur plus élevé: combustion '
 'à ciel ouvert partielle + décomposition non contrôlée. '
 'Contexte marocain: zones périurbaines et rurales.'),
-- Traitement eaux usées industrielles (STEP)
('00000000-0000-0000-0001-000000000003',
 'scope3_dechets', 'step_eaux_usees_industrielles',
 'CO2e', 0.7100, 'kgCO2e/kg_DCO', 'kg_DCO', 3, NULL, 'MA',
 'IPCC 2006 Vol.5 Ch.6 / ADEME — Traitement eaux usées industrielles',
 'Station d''épuration industrielle (STEP). Exprimé en kg DCO traité. '
 'Applicable aux industries agroalimentaires, textile, tanneries (Fès, Marrakech).'),
-- Valorisation énergétique déchets (incinération)
('00000000-0000-0000-0001-000000000003',
 'scope3_dechets', 'incineration_valorisation',
 'CO2e', 0.5400, 'kgCO2e/kg', 'kg', 3, NULL, 'MA',
 'ADEME BC v22 — Incinération avec valorisation énergétique',
 'Incinération avec production d''énergie. Rare au Maroc actuellement '
 'mais en développement (projets déchets-énergie ONEE).'),
-- Compostage déchets verts / boues STEP
('00000000-0000-0000-0001-000000000003',
 'scope3_dechets', 'compostage',
 'CO2e', 0.0610, 'kgCO2e/kg', 'kg', 3, NULL, 'MA',
 'ADEME BC v22 — Compostage déchets organiques',
 'Compostage déchets verts et organiques. Valorisation préférée. '
 'En croissance au Maroc (projets ONEE/communes).'),
-- Collecte et transport des déchets (camion-benne)
('00000000-0000-0000-0001-000000000003',
 'scope3_dechets', 'collecte_transport_dechets',
 'CO2e', 0.0320, 'kgCO2e/kg', 'kg', 3, NULL, 'MA',
 'ADEME BC v22 — Collecte/transport déchets ménagers',
 'Collecte par camion-benne diesel. Inclus transport vers la décharge. '
 'Valeur moyenne par kg de déchet collecté.');

-- ─────────────────────────────────────────────────────────────
-- 3D. EAU (Water) — Spécificité marocaine
-- ─────────────────────────────────────────────────────────────
-- L''eau est un enjeu stratégique au Maroc (stress hydrique)
-- ONEE produit et distribue eau potable + assainissement

INSERT INTO emission_factors
    (factor_set_id, category, sub_category, gas, value, unit, activity_unit,
     scope, scope2_type, region, source, notes)
VALUES
-- Eau potable ONEE (production + distribution)
-- Consommation électrique moyenne pompage + traitement ≈ 0.45 kWh/m3
-- × facteur ONEE 0.679 kgCO2e/kWh = 0.305 kgCO2e/m3
('00000000-0000-0000-0001-000000000003',
 'scope3_eau', 'eau_potable_onee',
 'CO2e', 0.3050, 'kgCO2e/m3', 'm3', 3, NULL, 'MA',
 'ONEE + calcul Adrar AI (consommation électrique pompage × facteur ONEE)',
 'Eau potable réseau ONEE: facteur émission calculé sur base '
 'consommation électrique moyenne pompage/traitement (0.45 kWh/m3) '
 'multiplié par facteur réseau ONEE (0.679 kgCO2e/kWh). '
 'Mise à jour annuelle recommandée avec rapport ONEE.'),
-- Eau d''irrigation (pompage agricole)
('00000000-0000-0000-0001-000000000003',
 'scope3_eau', 'eau_irrigation_pompage',
 'CO2e', 0.2030, 'kgCO2e/m3', 'm3', 3, NULL, 'MA',
 'ONEE / ORMVA — Pompage irrigation',
 'Eau d''irrigation pompée. Consommation ≈ 0.3 kWh/m3 × facteur ONEE. '
 'Applicable aux ORMVAs (périmètres irrigués). '
 'Très pertinent: 80% eau consommée Maroc = agriculture.'),
-- Traitement eaux usées (assainissement ONEE)
('00000000-0000-0000-0001-000000000003',
 'scope3_eau', 'assainissement_onee',
 'CO2e', 0.7440, 'kgCO2e/m3', 'm3', 3, NULL, 'MA',
 'ONEE Rapport RSE + IPCC 2006 — Assainissement + émissions biogéniques',
 'Traitement eaux usées urbaines: énergie STEP + émissions CH4/N2O '
 'des procédés biologiques. Inclus boues STEP.');

-- ─────────────────────────────────────────────────────────────
-- 3E. INDUSTRIES CLÉS MAROC
-- ─────────────────────────────────────────────────────────────

INSERT INTO emission_factors
    (factor_set_id, category, sub_category, gas, value, unit, activity_unit,
     scope, scope2_type, region, source, notes)
VALUES
-- INDUSTRIE CIMENTIÈRE (top 3 monde: LafargeHolcim MA, Ciments du Maroc, Asment)
-- Clinker (émissions procédé: décarbonatation calcaire)
('00000000-0000-0000-0001-000000000003',
 'scope1_process', 'clinker_calcination',
 'CO2e', 0.5200, 'kgCO2e/kg_clinker', 'kg_clinker', 1, NULL, 'MA',
 'IPCC 2006 Vol.3 Ch.2 / ADEME — Calcination calcaire (décarbonatation)',
 'Émissions procédé cimenterie: décarbonatation CaCO3 → CaO + CO2. '
 'Hors combustion. Standard industrie cimentière mondiale. '
 'Pertinent: Maroc 4ème producteur ciment en Afrique (Ciments du Maroc, LafargeHolcim).'),
-- Ciment broyage (consommation électrique)
('00000000-0000-0000-0001-000000000003',
 'scope2_electricity', 'ciment_broyage_elec',
 'CO2e', 0.6790, 'kgCO2e/kWh', 'kWh', 2, 'location', 'MA',
 'ONEE 2023 — Facteur réseau électrique Maroc',
 'Consommation électrique broyage ciment (~110 kWh/tonne ciment). '
 'Utiliser facteur ONEE local.'),
-- INDUSTRIE PHOSPHATIÈRE (OCP — 70% réserves mondiales)
-- Calcination phosphate (fours rotatifs)
('00000000-0000-0000-0001-000000000003',
 'scope1_process', 'phosphate_calcination',
 'CO2e', 0.0340, 'kgCO2e/kg_phosphate', 'kg_phosphate', 1, NULL, 'MA',
 'OCP SA Rapport Développement Durable 2023 / IPCC 2006 Vol.3',
 'Calcination/séchage minerai phosphaté. Facteur spécifique OCP. '
 'Hors combustion combustibles. Mise à jour avec rapport OCP annuel.'),
-- Production acide phosphorique (procédé voie humide)
('00000000-0000-0000-0001-000000000003',
 'scope1_process', 'acide_phosphorique_production',
 'CO2e', 0.0080, 'kgCO2e/kg_h3po4', 'kg_H3PO4', 1, NULL, 'MA',
 'IPCC 2006 / OCP — Production acide phosphorique voie humide',
 'Émissions procédé production H3PO4. OCP est le premier producteur mondial.'),
-- INDUSTRIE SIDÉRURGIQUE (Sonasid, Izar Steel)
('00000000-0000-0000-0001-000000000003',
 'scope1_process', 'acier_four_electrique',
 'CO2e', 0.3950, 'kgCO2e/kg_acier', 'kg_acier', 1, NULL, 'MA',
 'ADEME BC v22 / World Steel Association — Acier four électrique à arc',
 'Four électrique à arc (EAF) — technologie Sonasid. '
 'Hors électricité (Scope 2). Émissions procédé + électrodes.'),
-- TEXTILE (Tanger, Fès, Casablanca — 2ème exportateur UE)
('00000000-0000-0000-0001-000000000003',
 'scope3_achats', 'coton_teinture_traitement',
 'CO2e', 8.5000, 'kgCO2e/kg_coton_teint', 'kg_coton_teint', 3, NULL, 'MA',
 'Higg FEM / ADEME — Teinture et finissage textile',
 'Procédés de teinture et finissage textile. Très énergivore. '
 'Applicable aux confectionneurs et teinturiers de Fès, Tanger, Casablanca.'),
-- AGROALIMENTAIRE (Cosumar, Centrale Danone, Bimo...)
-- Froid industriel (réfrigérants fugitifs)
('00000000-0000-0000-0001-000000000003',
 'scope1_fugitive', 'refrigerant_r410a_fugitif',
 'CO2e', 2088.0, 'kgCO2e/kg', 'kg', 1, NULL, 'MA',
 'IPCC AR6 / ADEME BC v22 — HFC-32/125 (R-410A) fuites fugitives',
 'Pertes de réfrigérant R-410A. GWP100 (AR6) = 2088. '
 'R-410A très utilisé climatisation Maroc (hôtels, grandes surfaces, industrie). '
 'Taux de fuite recommandé audit: 5-20%/an selon équipement.'),
('00000000-0000-0000-0001-000000000003',
 'scope1_fugitive', 'refrigerant_r22_fugitif',
 'CO2e', 1760.0, 'kgCO2e/kg', 'kg', 1, NULL, 'MA',
 'IPCC AR5 / ADEME BC v22 — HCFC-22 (R-22) fuites fugitives',
 'Pertes de réfrigérant R-22 (HCFC-22). GWP100 (AR5) = 1760. '
 'Encore très présent au Maroc malgré le Protocole de Montréal. '
 'Phase-out prévu 2040 pour pays Article 5.'),
('00000000-0000-0000-0001-000000000003',
 'scope1_fugitive', 'refrigerant_r134a_fugitif',
 'CO2e', 1526.0, 'kgCO2e/kg', 'kg', 1, NULL, 'MA',
 'IPCC AR6 / ADEME BC v22 — HFC-134a fuites fugitives',
 'Pertes de réfrigérant R-134a. GWP100 (AR6) = 1526. '
 'Utilisé climatisation voitures et froid commercial.'),
-- AGRICULTURE (dominant GDP sector in Morocco — 15% PIB)
-- Bovins (élevage bovin lait + viande — Maroc Élevage)
('00000000-0000-0000-0001-000000000003',
 'scope1_agriculture', 'bovins_fermentation_enterique',
 'CO2e', 1.5700, 'kgCO2e/animal.jour', 'animal.jour', 1, NULL, 'MA',
 'IPCC 2006 Vol.4 Ch.10 / MAPMDREF Maroc — Bovins lait',
 'Fermentation entérique bovins lait Maroc. Facteur régionalisé Afrique du Nord. '
 '≈ 573 kgCO2e/animal/an. Méthodologie Tier 1 IPCC.'),
('00000000-0000-0000-0001-000000000003',
 'scope1_agriculture', 'ovins_fermentation_enterique',
 'CO2e', 0.1589, 'kgCO2e/animal.jour', 'animal.jour', 1, NULL, 'MA',
 'IPCC 2006 Vol.4 Ch.10 — Ovins (petits ruminants)',
 'Fermentation entérique ovins. ≈ 58 kgCO2e/animal/an. '
 'Très pertinent Maroc: 20 millions ovins. Tier 1 IPCC.'),
-- Engrais azotés (émissions N2O)
('00000000-0000-0000-0001-000000000003',
 'scope1_agriculture', 'engrais_azotes_n2o',
 'CO2e', 4.4170, 'kgCO2e/kg_N', 'kg_N', 1, NULL, 'MA',
 'IPCC 2006 Vol.4 Ch.11 / ADEME — Émissions N2O engrais azotés',
 'Émissions N2O directes et indirectes application engrais azotés. '
 'Facteur: 1% azote épandu converti en N2O × GWP265 (AR5). '
 'OCP fournisseur d''engrais → très pertinent pour traçabilité aval.');

-- ─────────────────────────────────────────────────────────────
-- 3F. ÉLECTRICITÉ MAROC — MISE À JOUR + SCÉNARIOS FUTURS
-- ─────────────────────────────────────────────────────────────
-- NDC Maroc 2030: 52% EnR dans le mix électrique
-- Noor (solaire concentré), Tarfaya (éolien), Jorf (gaz)

INSERT INTO emission_factors
    (factor_set_id, category, sub_category, gas, value, unit, activity_unit,
     scope, scope2_type, region, source, notes)
VALUES
-- Facteur ONEE 2023 (valeur actualisée du rapport ONEE RSE 2023)
('00000000-0000-0000-0001-000000000003',
 'scope2_electricity', 'onee_grid_2023_location',
 'CO2e', 0.6790, 'kgCO2e/kWh', 'kWh', 2, 'location', 'MA',
 'ONEE Rapport Annuel RSE 2023 — Facteur émission réseau national Maroc',
 'Facteur officiel réseau électrique national marocain 2023. '
 'Mix: ~40% charbon (Jorf Lasfar), ~20% gaz, ~20% éolien+solaire, ~20% hydraulique. '
 'Mise à jour requise chaque année avec publication ONEE.'),
-- Facteur ONEE 2024 projection (objectif NDC)
('00000000-0000-0000-0001-000000000003',
 'scope2_electricity', 'onee_grid_2024_projection',
 'CO2e', 0.6200, 'kgCO2e/kWh', 'kWh', 2, 'location', 'MA',
 'Adrar AI — Projection ONEE 2024 sur base plan NDC',
 'Valeur projetée 2024 intégrant la montée en puissance des parcs EnR '
 '(Noor III solaire, Tarfaya éolien extension, Taza éolien). '
 'À confirmer avec publication officielle ONEE.'),
-- Autoconsommation solaire PV (émissions grises panneau)
('00000000-0000-0000-0001-000000000003',
 'scope2_electricity', 'solaire_pv_autoconsommation',
 'CO2e', 0.0480, 'kgCO2e/kWh', 'kWh', 2, 'market', 'MA',
 'ADEME BC v22 — Énergie solaire photovoltaïque (ACV)',
 'Facteur ACV (analyse cycle de vie) panneaux PV installés au Maroc. '
 'Production locale (marché M) utilisable comme facteur marché '
 'pour les sites avec panneaux propres certifiés.'),
-- EnR achetée avec GO (Garantie d''Origine — peu disponible au Maroc)
('00000000-0000-0000-0001-000000000003',
 'scope2_electricity', 'enr_avec_go_marche',
 'CO2e', 0.0000, 'kgCO2e/kWh', 'kWh', 2, 'market', 'MA',
 'GHG Protocol Scope 2 Guidance — EnR avec GO',
 'Électricité renouvelable avec Garantie d''Origine (GO) valide. '
 'Scope 2 marché = 0 si GO couvre 100% consommation. '
 'Peu disponible au Maroc actuellement; en cours de développement (AMEE).');

-- ─────────────────────────────────────────────────────────────
-- 3G. CONSTRUCTION / BTP (Secteur #1 du PIB hors agriculture MA)
-- ─────────────────────────────────────────────────────────────

INSERT INTO emission_factors
    (factor_set_id, category, sub_category, gas, value, unit, activity_unit,
     scope, scope2_type, region, source, notes)
VALUES
-- Béton (production clinker incluse, impact global)
('00000000-0000-0000-0001-000000000003',
 'scope3_achats', 'beton_btp',
 'CO2e', 0.1420, 'kgCO2e/kg', 'kg', 3, NULL, 'MA',
 'ADEME BC v22 / CSTB — Béton B25 (25 MPa)',
 'Béton courant B25. Inclus clinker + granulats + transport. '
 'Chantiers BTP Maroc (lots courants). '
 'Pour haute résistance (B40, B50): multiplier ×1.3.'),
-- Acier de construction (produit par Sonasid Maroc)
('00000000-0000-0000-0001-000000000003',
 'scope3_achats', 'acier_construction_maroc',
 'CO2e', 1.1800, 'kgCO2e/kg', 'kg', 3, NULL, 'MA',
 'World Steel Association 2023 / Sonasid — Acier long (rond à béton)',
 'Rond à béton (fer à béton) produit par Sonasid Jorf Lasfar. '
 'Base four électrique à arc (scrap). Valeur ACV cradle-to-gate. '
 'Utilisé dans la construction résidentielle et infrastructures.'),
-- Brique de terre cuite (matériau très utilisé Maroc)
('00000000-0000-0000-0001-000000000003',
 'scope3_achats', 'brique_terre_cuite',
 'CO2e', 0.2350, 'kgCO2e/kg', 'kg', 3, NULL, 'MA',
 'ADEME INIES / Briqueteries du Maroc — Brique creuse 8 trous',
 'Brique creuse (brique de terre cuite marocaine). '
 'Production locale (Briqueteries Ain Johra, Settat, Meknès). '
 'Hors pose (enduit, mortier à quantifier séparément).'),
-- Verre plat (Saint-Gobain Maroc, Guardian)
('00000000-0000-0000-0001-000000000003',
 'scope3_achats', 'verre_plat',
 'CO2e', 0.8600, 'kgCO2e/kg', 'kg', 3, NULL, 'MA',
 'ADEME BC v22 / Saint-Gobain — Verre float plat',
 'Verre plat (float). Production locale (AGC Bouskoura) et import. '
 'Forte empreinte procédé (four verrier à 1550°C).'),
-- PVC (tuyauteries, menuiseries — très utilisé BTP Maroc)
('00000000-0000-0000-0001-000000000003',
 'scope3_achats', 'pvc_construction',
 'CO2e', 2.4100, 'kgCO2e/kg', 'kg', 3, NULL, 'MA',
 'ADEME BC v22 / PlasticsEurope — PVC',
 'PVC (polychlorure de vinyle). Menuiseries, canalisations. '
 'Import majoritaire au Maroc depuis Europe + Asie.');

-- ─────────────────────────────────────────────────────────────
-- 3H. SCOPE 3 — ACHATS STRATÉGIQUES MAROC
-- ─────────────────────────────────────────────────────────────

INSERT INTO emission_factors
    (factor_set_id, category, sub_category, gas, value, unit, activity_unit,
     scope, scope2_type, region, source, notes)
VALUES
-- Papier (secteur tertiaire + administration — usage massif)
('00000000-0000-0000-0001-000000000003',
 'scope3_achats', 'papier_bureau',
 'CO2e', 0.9340, 'kgCO2e/kg', 'kg', 3, NULL, 'MA',
 'ADEME BC v22 — Papier de bureau (80 g/m²)',
 'Papier A4 80g/m² importé (quasi-totalité importée au Maroc). '
 'Administrations publiques, banques, assurances, grandes entreprises.'),
-- Informatique (ordinateurs portables)
('00000000-0000-0000-0001-000000000003',
 'scope3_achats', 'ordinateur_portable_achat',
 'CO2e', 316.0, 'kgCO2e/unité', 'unité', 3, NULL, 'MA',
 'ADEME BC v22 / Dell Sustain. Report — Ordinateur portable',
 'PC portable (production + transport). Amortissement sur 5 ans recommandé: '
 '~63 kgCO2e/an/ordinateur.'),
-- Fournitures de bureau (approvisionnement)
('00000000-0000-0000-0001-000000000003',
 'scope3_achats', 'fournitures_bureau',
 'CO2e', 2.1000, 'kgCO2e/kg', 'kg', 3, NULL, 'MA',
 'ADEME BC v22 — Fournitures de bureau (mix plastique/métal)',
 'Consommables bureau: stylos, classeurs, etc. Import quasi-total.'),
-- Repas (restauration collective)
('00000000-0000-0000-0001-000000000003',
 'scope3_achats', 'repas_cafeteria',
 'CO2e', 2.6000, 'kgCO2e/repas', 'repas', 3, NULL, 'MA',
 'ADEME BC v22 — Repas traditionnel (viande rouge + légumes)',
 'Repas type restauration collective Maroc (tagine viande + légumes). '
 'Inclus production alimentaire + transport. '
 'Repas végétarien: ~0.8 kgCO2e/repas.'),
-- Hébergement hôtelier (déplacements professionnels)
('00000000-0000-0000-0001-000000000003',
 'scope3_transport', 'nuit_hotel_maroc',
 'CO2e', 28.5000, 'kgCO2e/nuit', 'nuit', 3, NULL, 'MA',
 'ADEME BC v22 adapté Maroc — Hébergement hôtel 3 étoiles',
 'Nuitée hôtel 3* Maroc (Accor MA, Barceló, hôtels indépendants). '
 'Inclus énergie, eau, linge, restauration partielle. '
 'Hôtel 5*: multiplier ×2.5.');

-- ─────────────────────────────────────────────────────────────
-- 3I. ÉNERGIE RENOUVELABLE — Spécificité NDC Maroc
-- ─────────────────────────────────────────────────────────────

INSERT INTO emission_factors
    (factor_set_id, category, sub_category, gas, value, unit, activity_unit,
     scope, scope2_type, region, source, notes)
VALUES
-- Éolien (parcs Tarfaya, Taza, Jbel Khalladi, Midelt)
('00000000-0000-0000-0001-000000000003',
 'scope1_stationary', 'eolien_production',
 'CO2e', 0.0115, 'kgCO2e/kWh', 'kWh', 1, NULL, 'MA',
 'ADEME BC v22 — Éolien terrestre (ACV)',
 'Facteur ACV éolien terrestre (installation + exploitation + fin de vie). '
 'Applicable aux parcs éoliens marocains (Tarfaya, Midelt, Jbel Khalladi). '
 'Émissions très faibles vs réseau conventionnel (÷60).'),
-- Solaire PV utilité (Noor, Mohammed bin Rashid, centrales utility-scale)
('00000000-0000-0000-0001-000000000003',
 'scope1_stationary', 'solaire_pv_utility',
 'CO2e', 0.0480, 'kgCO2e/kWh', 'kWh', 1, NULL, 'MA',
 'ADEME BC v22 — Solaire PV utilité (ACV)',
 'Solaire photovoltaïque grande centrale (Noor PV Ouarzazate, Mohammed bin Rashid). '
 'ACV fabrication panneau + installation + maintenance.'),
-- CSP (Concentré Solaire Thermique — Noor I, II, III Ouarzazate)
('00000000-0000-0000-0001-000000000003',
 'scope1_stationary', 'csp_noor',
 'CO2e', 0.0200, 'kgCO2e/kWh', 'kWh', 1, NULL, 'MA',
 'ADEME BC v22 / IRENA — CSP parabolique avec stockage thermique',
 'Centrales solaires à concentration (CSP) Noor I/II/III Ouarzazate. '
 'Stockage thermique 3-8h permet production nocturne. '
 'L''une des plus basses empreintes par kWh produit.');

-- ============================================================
-- 4. MISE À JOUR CONVERSION FACTORS MAROC
-- Butane (non inclus dans ADEME global)
-- ============================================================

INSERT INTO conversion_factors
    (from_unit, to_unit, coefficient, conversion_type, fuel_type, source, effective_from)
VALUES
-- Butane kg → MJ (NCV = 45.74 MJ/kg)
('kg', 'MJ', 45.74, 'NCV', 'butane', 'IPCC 2006 / ADEME — Butane (C4H10)', '2024-01-01'),
-- Bouteille 12kg → kg (standard Maroc)
('bouteille_12kg', 'kg', 12.0, 'direct', 'butane', 'Standard bouteille gaz Maroc ONHYM', '2024-01-01'),
-- Bouteille 3kg → kg (petite bouteille ménagère)
('bouteille_3kg', 'kg', 3.0, 'direct', 'butane', 'Standard bouteille gaz Maroc ONHYM', '2024-01-01'),
-- TEP → MJ (Tonne Équivalent Pétrole — unité AMEE)
('TEP', 'MJ', 41868.0, 'direct', NULL, 'OCDE / AMEE Maroc — 1 TEP = 41 868 MJ', '2020-01-01'),
-- kTEP → TEP
('kTEP', 'TEP', 1000.0, 'direct', NULL, 'AMEE Maroc', '2020-01-01'),
-- passager.km (unité transport personnes)
('passager.km', 'passager.km', 1.0, 'direct', NULL, 'SI passager transport', '2020-01-01'),
-- tonne.km (unité transport fret)
('tonne.km', 'tonne.km', 1.0, 'direct', NULL, 'SI fret transport', '2020-01-01'),
-- animal.jour (unité élevage)
('animal.jour', 'animal.an', 365.0, 'direct', NULL, 'IPCC — élevage bovin', '2020-01-01'),
-- m3 eau
('m3', 'm3', 1.0, 'direct', 'eau', 'SI eau', '2020-01-01');

-- ============================================================
-- 5. SCHEMA ADDITIONS: NDC tracking + RSE metadata
-- ============================================================

-- Add NDC-tracking and reporting framework fields to projects
ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS reporting_frameworks TEXT[] DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS ndc_target_year INTEGER,
    ADD COLUMN IF NOT EXISTS ndc_baseline_year INTEGER,
    ADD COLUMN IF NOT EXISTS sector_code TEXT,
    ADD COLUMN IF NOT EXISTS language TEXT DEFAULT 'fr' CHECK (language IN ('fr','en','ar'));

-- Add client sector taxonomy (Morocco industry codes)
ALTER TABLE clients
    ADD COLUMN IF NOT EXISTS naics_code TEXT,
    ADD COLUMN IF NOT EXISTS secteur_maroc TEXT,
    ADD COLUMN IF NOT EXISTS is_listed_bvc BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS rse_reporting_required BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN clients.is_listed_bvc IS
    'Société cotée à la Bourse des Valeurs de Casablanca — Rapport RSE obligatoire';
COMMENT ON COLUMN clients.rse_reporting_required IS
    'Rapport RSE obligatoire (BVC coté ou engagement volontaire)';
COMMENT ON COLUMN projects.reporting_frameworks IS
    'Standards de reporting sélectionnés: bilan_carbone, iso_14064, ghg_protocol, gri_305, csrd, tcfd, cdp, amee';
COMMENT ON COLUMN projects.sector_code IS
    'Code secteur marocain: phosphate, ciment, textile, agroalimentaire, btp, tourisme, banque, etc.';

-- Extend report_snapshots with framework-specific outputs
ALTER TABLE report_snapshots
    ADD COLUMN IF NOT EXISTS gri_305_data JSONB,
    ADD COLUMN IF NOT EXISTS ndc_alignment JSONB,
    ADD COLUMN IF NOT EXISTS intensity_metrics JSONB;

COMMENT ON COLUMN report_snapshots.gri_305_data IS
    'Données GRI 305 calculées: 305-1 (Scope1), 305-2 (Scope2 loc+mkt), 305-3 (Scope3), '
    '305-4 (intensité GES), 305-5 (réduction), 305-6 (ODS), 305-7 (NOx, SOx, polluants)';
COMMENT ON COLUMN report_snapshots.ndc_alignment IS
    'Alignement NDC Maroc: émissions vs trajectoire -45.5% d''ici 2030, '
    'contribution sectorielle, % EnR atteint';
COMMENT ON COLUMN report_snapshots.intensity_metrics IS
    'Métriques d''intensité: kgCO2e/m2 (BTP), kgCO2e/tonne produit (industrie), '
    'kgCO2e/CA (tertiaire), kgCO2e/employé (services)';

COMMIT;
