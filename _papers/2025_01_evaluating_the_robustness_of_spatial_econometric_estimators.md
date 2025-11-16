---
name: Evaluating the Robustness of Spatial Econometric Estimators
category: Journal Article
year: 2025
date: 2025-01-01
authors: Vincenzo Nardelli, Niccolò Salvini
journal: NETWORKS AND SPATIAL ECONOMICS
link: "https://doi.org/10.1007/s11067-025-09716-9"
---

# Abstract
Statistical procedures can be significantly affected by outliers, and spatial econometric models are no exception. While Maximum Likelihood (ML) estimators are common, computationally efficient Generalized Method of Moments (GM) estimators–such as Spatial Two-Stage Least Squares (STSLS) for lag models, GMerrorsar for error models, and Generalized Spatial Two-Stage Least Squares (GSTSLS) for combined (SARAR) models–are increasingly preferred for large datasets. However, systematic evidence on the comparative robustness of these diverse estimation techniques (ML versus GM) to local outliers remains limited, particularly concerning their performance when models are correctly specified versus potentially misspecified. This paper aims to fill this gap by employing the Local Influence Function (LIF), an extension of the classical influence function to spatial datasets. First, we conduct Monte Carlo experiments to systematically evaluate the robustness of Maximum Likelihood (ML) versus Generalized Method of Moments (GM) estimators for Spatial Lag (SLM), Spatial Error (SEM), and Spatial Autoregressive with Autoregressive Disturbances (SARAR) models. For each model type, estimators are assessed using data generated from their respective true Data Generating Processes (DGPs) under local perturbations of the dependent variable. These simulations indicate that, under correct model specification, ML estimators generally demonstrate superior robustness for key parameters (
, 
, 
) compared to their GM counterparts. Second, we demonstrate the practical utility of the LIF methodology using a large-scale dataset of approximately 7,900 Italian municipalities to analyze the relationship between average equivalent income and unemployment rates. Our application reveals that key parameters of the GM estimator for the most comprehensive model (SARAR/SAC) can exhibit considerable local sensitivity to data perturbations, and the LIF effectively identifies specific municipalities exerting disproportionate influence, allowing for the mapping of these spatial patterns of sensitivity.
