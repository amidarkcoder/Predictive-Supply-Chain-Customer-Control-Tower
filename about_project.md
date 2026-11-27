# Predictive Supply Chain & Customer Control Tower

### Overview

Predictive Supply Chain & Customer Control Tower is a full-stack data engineering and prescriptive analytics platform built on the Databricks Lakehouse using dbt, PySpark, Delta Lake, and Databricks AI/BI Dashboards. Designed to eliminate operational blind spots across procurement, warehousing, last-mile delivery, and customer retention, the platform unifies transactional data into a single source of truth that drives automated replenishment, vendor accountability, and targeted customer growth.

### Architecture & Data Engineering

• Medallion Lakehouse Pipeline: Structures raw operational feeds and seed dimensions into validated Silver tables and business-ready Gold fact and dimension marts inside Unity Catalog.
• Incremental Processing (dbt + Delta Lake): Implements merge-based incremental models (fct_sales, fct_inventory_snapshot) with rolling lookback windows to capture late-arriving inventory snapshots and real-time order delivery updates without full table rebuilds.
• Historical State Tracking (SCD Type 2): Uses dbt check-strategy snapshots (snap_supplier_price, snap_customer_level) to preserve historical vendor pricing changes and customer loyalty tier transitions for accurate point-in-time auditing.
• Automated Data Quality & Observability: Enforces referential integrity and uniqueness via automated dbt schema tests alongside a dedicated PySpark Data Quality audit tracking null rates, duplicate business keys, and orphan foreign keys.

### Core Analytics & Machine Learning Modules

• Inventory & Warehouse Optimization: Computes dynamic Safety Stock, Economic Order Quantity (EOQ), ABC-XYZ velocity/variability matrices, Inventory Turnover & DIO, and cash tied up in 90-day dead stock.
• Supplier & Logistics Intelligence: Ranks vendors using a weighted Composite Scorecard (QC rating, on-time rate, price, lead time), flags single-sourced SKU vulnerabilities, quantifies lost sales revenue from late POs, evaluates warehouse-to-location route efficiency, and tracks carrier SLA breach rates.
• Customer & Revenue Growth: Segments buyers via RFM analysis (Champions, At-Risk, Lost), calculates Historical & Predictive CLV, and uncovers cross-sell bundles through Market Basket Analysis (Support, Confidence, Lift).
• Predictive ML Models (PySpark ML): Trains a Random Forest Classifier to flag high-risk open orders before SLA breaches occur, and a Logistic Regression model using tenure (active_days) and inactivity (no_shopping) to score customer churn probability.

### Executive Decision Dashboards (Databricks AI/BI)

Delivers three role-specific interactive dashboards equipped with KPI counters, threshold annotations, and multi-dimensional drill-downs:
1. Inventory & Warehouse Health: Stockout trends, warehouse capacity utilization, ABC-XYZ heatmaps, and replenishment gap alerts.
2. Supplier & Delivery Logistics: Vendor scorecards, fulfillment bottleneck breakdowns (dispatch vs. transit), route cost-vs-speed scatter plots, and high-risk order alerts.
3. Customer & Revenue Growth: RFM revenue distribution, churn risk vs. inactivity profiles, CLV at risk, and product affinity recommendations.

### Tech Stack

• Platform & Storage: Databricks (Serverless Compute, Unity Catalog, Delta Lake, Databricks Connect)
• Transformation & Testing: dbt-databricks (Incremental Merge, SCD Type 2 Snapshots, Schema & Relationship Tests)
• Analytics & ML: PySpark SQL, PySpark MLlib (Random Forest, Logistic Regression)
• Visualization: Databricks AI/BI Dashboards
Would you like me to also generate:
• Resume bullet points highlighting the business impact and technical stack of this project
• A text-based architecture diagram (Mermaid/ASCII) to embed directly inside your README.md
• The consolidated SQL queries to power all widgets across your three Databricks Dashboards




