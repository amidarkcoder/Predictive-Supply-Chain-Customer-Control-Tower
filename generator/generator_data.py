from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------------
# 0. FIXED CALENDAR
# ----------------------------------------------------------------------------------
START_DATE = date(2025, 1, 1)
END_DATE = date(2025, 6, 30)
N_DAYS = (END_DATE - START_DATE).days + 1
DATES = [START_DATE + timedelta(days=i) for i in range(N_DAYS)]
DATES_OBJ = np.array(DATES + [None], dtype=object)       # index -1 -> None
CHANGE_DATE = date(2025, 4, 1)                           # SCD2 effective date
CHANGE_IDX = (CHANGE_DATE - START_DATE).days
DEAD_FROM = date(2025, 3, 10)                            # dead SKUs stop selling
DEAD_IDX = (DEAD_FROM - START_DATE).days
FESTIVE_IDX = (date(2025, 3, 14) - START_DATE).days      # festive demand peak

# ----------------------------------------------------------------------------------
# 1. STATIC MASTER DEFINITIONS
# ----------------------------------------------------------------------------------
CITIES = {  # lat, lon
    "Mumbai": (19.07, 72.88), "Delhi": (28.61, 77.21), "Bengaluru": (12.97, 77.59),
    "Chennai": (13.08, 80.27), "Kolkata": (22.57, 88.36), "Pune": (18.52, 73.86),
    "Hyderabad": (17.38, 78.48), "Ahmedabad": (23.02, 72.57), "Jaipur": (26.91, 75.79),
    "Lucknow": (26.85, 80.95), "Surat": (21.17, 72.83), "Nagpur": (21.15, 79.09),
}
CITY_NAMES = list(CITIES)
CITY_P = np.array([.16, .16, .14, .09, .08, .09, .08, .05, .05, .04, .03, .03])
CITY_P = CITY_P / CITY_P.sum()


def road_km(a, b):
    if a == b:
        return 10.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dphi, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * 6371 * math.asin(math.sqrt(h)) * 1.25, 0)


DIST = np.array([[road_km(CITIES[a], CITIES[b]) for b in CITY_NAMES] for a in CITY_NAMES])

WAREHOUSES = [  # id, name, city, manager (None = vacant -> natural NULL)
    ("WH01", "Mumbai Central DC", "Mumbai", "Rohan Mehta"),
    ("WH02", "Delhi North DC", "Delhi", "Anita Sharma"),
    ("WH03", "Bengaluru South DC", "Bengaluru", "Karthik Rao"),
    ("WH04", "Chennai Coastal DC", "Chennai", "Meena Iyer"),
    ("WH05", "Kolkata East DC", "Kolkata", None),
]
WH_IDS = [w[0] for w in WAREHOUSES]
WH_CITY_IDX = [CITY_NAMES.index(w[2]) for w in WAREHOUSES]
# for each customer city -> 3 nearest warehouses (home first, then fallbacks)
PREF_WH = [list(map(int, np.argsort(DIST[c, WH_CITY_IDX])[:3])) for c in range(len(CITY_NAMES))]

PARTNERS = [  # id, name, hub city, km/day, delay prob, base cost, cost per km
    ("DP01", "SwiftExpress", "Mumbai", 700, .07, 60, .090),
    ("DP02", "BlueLine Logistics", "Delhi", 550, .12, 45, .070),
    ("DP03", "SouthRoute", "Bengaluru", 500, .14, 40, .060),
    ("DP04", "CoastCargo", "Chennai", 450, .18, 35, .050),
    ("DP05", "EastCourier", "Kolkata", 400, .25, 30, .045),   # worst SLA
    ("DP06", "PanIndia Freight", "Nagpur", 380, .20, 28, .040),  # cheapest, slow
]

SUPPLIERS = [  # id, name, city, quoted base lead, on-time prob, QC, price factor
    ("SUP01", "Apex Foods", "Mumbai", 4, .95, 4.6, 1.05),
    ("SUP02", "Green Valley Agro", "Delhi", 5, .90, 4.3, 1.00),
    ("SUP03", "Southern Staples", "Chennai", 5, .88, 4.1, .98),
    ("SUP04", "Eastern Beverages", "Kolkata", 6, .80, 3.9, .97),
    ("SUP05", "Metro Dairy Co", "Pune", 3, .93, 4.5, 1.02),
    ("SUP06", "QuickMove FMCG", "Ahmedabad", 4, .72, 3.4, .93),   # cheap, unreliable
    ("SUP07", "BudgetBulk Traders", "Surat", 7, .62, 3.0, .90),    # worst supplier
    ("SUP08", "CleanHome Industries", "Hyderabad", 6, .85, 4.0, 1.00),
    ("SUP09", "Care & Glow Labs", "Bengaluru", 5, .91, 4.4, 1.03),
    ("SUP10", "Festive Hub", "Jaipur", 8, .78, 3.7, .96),
]
SUP_IDX = {s[0]: k for k, s in enumerate(SUPPLIERS)}
SUP_CITY_IDX = [CITY_NAMES.index(s[2]) for s in SUPPLIERS]
CATEGORY_POOL = {
    "Staples": ["SUP01", "SUP02", "SUP03", "SUP06", "SUP07"],
    "Beverages": ["SUP04", "SUP03", "SUP06", "SUP01"],
    "Dairy": ["SUP05", "SUP02", "SUP01"],
    "Bakery": ["SUP05", "SUP06"],
    "Snacks": ["SUP06", "SUP07", "SUP04", "SUP01"],
    "Frozen": ["SUP05", "SUP04"],
    "Personal Care": ["SUP09", "SUP08", "SUP01"],
    "Household": ["SUP08", "SUP07", "SUP09"],
    "Festive": ["SUP10", "SUP02"],
    "Home": ["SUP08", "SUP07", "SUP10"],
    "Electronics": ["SUP07", "SUP08"],
}
SINGLE_SOURCE = {"Bread Loaf", "Ice Cream Tub", "Sunscreen Lotion", "Hot Chocolate Mix",
                 "Dry Fruits Gift Box", "Sweets Box", "Holi Colour Pack", "Instant Coffee 100g",
                 "Pasta Sauce", "Cheese Slices 200g", "USB Charging Cable", "Scented Candles"}
FORCED = {"Sugar 1kg": ["SUP06"],      # fast SKU on ONE unreliable supplier -> stockouts
          "Bread Loaf": ["SUP05"]}

# name, category, cost, tier(A fast/B/C slow), season, weekend-heavy, xyz variability
CATALOG = [
    ("Basmati Rice 5kg", "Staples", 420, "A", None, False, "X"),
    ("Whole Wheat Flour 5kg", "Staples", 210, "A", None, False, "X"),
    ("Sunflower Oil 1L", "Staples", 140, "A", None, False, "X"),
    ("Sugar 1kg", "Staples", 42, "A", None, False, "X"),
    ("Toor Dal 1kg", "Staples", 120, "B", None, False, "X"),
    ("Tea Powder 500g", "Beverages", 180, "B", None, False, "X"),
    ("Instant Coffee 100g", "Beverages", 220, "B", None, False, "Y"),
    ("Full Cream Milk 1L", "Dairy", 56, "A", None, False, "X"),
    ("Butter 500g", "Dairy", 260, "B", None, False, "Y"),
    ("Cheese Slices 200g", "Dairy", 120, "B", None, False, "Y"),
    ("Bread Loaf", "Bakery", 35, "A", None, True, "X"),
    ("Eggs Tray 30", "Dairy", 170, "A", None, False, "X"),
    ("Potato Chips", "Snacks", 18, "A", None, True, "Y"),
    ("Chocolate Bar", "Snacks", 45, "B", None, True, "Y"),
    ("Biscuits Pack", "Snacks", 25, "A", None, False, "X"),
    ("Instant Noodles", "Snacks", 14, "A", None, False, "Y"),
    ("Pasta 500g", "Staples", 95, "B", None, False, "Y"),
    ("Pasta Sauce", "Staples", 110, "C", None, False, "Z"),
    ("Cola 2L", "Beverages", 85, "B", "summer", True, "Y"),
    ("Mango Juice 1L", "Beverages", 90, "B", "summer", False, "Y"),
    ("Ice Cream Tub", "Frozen", 160, "B", "summer", True, "Y"),
    ("Mineral Water 12pk", "Beverages", 150, "B", "summer", False, "Y"),
    ("Sunscreen Lotion", "Personal Care", 280, "C", "summer", False, "Z"),
    ("Hot Chocolate Mix", "Beverages", 240, "C", "winter", False, "Z"),
    ("Winter Body Cream", "Personal Care", 190, "C", "winter", False, "Z"),
    ("Honey 500g", "Staples", 230, "C", "winter", False, "Y"),
    ("Shampoo 340ml", "Personal Care", 190, "B", None, False, "Y"),
    ("Soap 4pk", "Personal Care", 110, "B", None, False, "X"),
    ("Toothpaste", "Personal Care", 85, "A", None, False, "X"),
    ("Toothbrush", "Personal Care", 40, "B", None, False, "Y"),
    ("Detergent Powder 2kg", "Household", 220, "B", None, False, "X"),
    ("Dishwash Liquid", "Household", 120, "B", None, False, "Y"),
    ("Floor Cleaner", "Household", 130, "C", None, False, "Z"),
    ("Toilet Paper 6pk", "Household", 180, "B", None, False, "X"),
    ("Air Freshener", "Household", 150, "C", None, False, "Z"),        # DEAD
    ("Holi Colour Pack", "Festive", 60, "C", "festive", False, "Z"),
    ("Dry Fruits Gift Box", "Festive", 650, "C", "festive", False, "Z"),
    ("Sweets Box", "Festive", 320, "C", "festive", False, "Z"),
    ("Scented Candles", "Home", 150, "C", None, False, "Z"),           # DEAD
    ("USB Charging Cable", "Electronics", 120, "C", None, False, "Z"),  # DEAD
]
DEAD = {"Air Freshener", "Scented Candles", "USB Charging Cable"}
PERISHABLE = {"Full Cream Milk 1L", "Bread Loaf", "Eggs Tray 30", "Ice Cream Tub"}
TIER_POP = {"A": 10.0, "B": 4.0, "C": 1.2}
TIER_QTY_LAM = {"A": 1.2, "B": 0.6, "C": 0.2}
PACK = {"A": 48, "B": 24, "C": 12}
XYZ_SIGMA = {"X": .12, "Y": .40, "Z": .90}
AFFINITY = [
    ("Bread Loaf", "Butter 500g"), ("Bread Loaf", "Eggs Tray 30"), ("Bread Loaf", "Cheese Slices 200g"),
    ("Pasta 500g", "Pasta Sauce"), ("Toothpaste", "Toothbrush"), ("Tea Powder 500g", "Sugar 1kg"),
    ("Potato Chips", "Cola 2L"), ("Instant Noodles", "Eggs Tray 30"),
    ("Basmati Rice 5kg", "Toor Dal 1kg"), ("Whole Wheat Flour 5kg", "Sunflower Oil 1L"),
    ("Shampoo 340ml", "Soap 4pk"), ("Detergent Powder 2kg", "Dishwash Liquid"),
    ("Ice Cream Tub", "Chocolate Bar"), ("Holi Colour Pack", "Sweets Box"),
    ("Sweets Box", "Dry Fruits Gift Box"), ("Sunscreen Lotion", "Mineral Water 12pk"),
    ("Hot Chocolate Mix", "Full Cream Milk 1L"),
]

SEGMENTS = ["champion", "regular", "occasional", "new", "at_risk", "lost"]
SEG_P = [.12, .33, .22, .12, .11, .10]
LEVELS = ["BASIC", "PLUS", "PREMIUM"]
LEVEL_P = {"champion": [.1, .4, .5], "regular": [.5, .35, .15], "occasional": [.85, .13, .02],
           "new": [.9, .1, 0.0], "at_risk": [.4, .4, .2], "lost": [.6, .3, .1]}
LEVEL_DISC = np.array([0.0, 0.02, 0.05])
FIRST = ["Aarav", "Vivaan", "Aditya", "Arjun", "Ishaan", "Rohan", "Kabir", "Neha", "Priya", "Ananya",
         "Diya", "Kavya", "Sneha", "Pooja", "Riya", "Sana", "Imran", "Farah", "Rahul", "Amit",
         "Suresh", "Lakshmi", "Deepa", "Manoj", "Vikram", "Nisha", "Tarun", "Meera", "Sanjay", "Isha"]
LAST = ["Sharma", "Verma", "Patel", "Reddy", "Nair", "Iyer", "Khan", "Singh", "Gupta", "Mehta",
        "Das", "Banerjee", "Joshi", "Kulkarni", "Rao", "Chopra", "Malhotra", "Bose", "Menon", "Shah"]

DQ = {  # controlled dirty-data rates (fractions of rows)
    "orders_null_item_name": .010, "orders_null_customer_id": .003, "orders_null_warehouse_id": .002,
    "orders_null_partner": .005, "orders_orphan_customer": .002, "orders_delivered_before_dispatch": .001,
    "orders_dirty_status": .005, "orders_duplicates": .003,
    "inv_negative_on_hand": .0005, "inv_null_safety": .01, "inv_null_lead": .01,
    "inv_null_holding": .005, "inv_duplicates": .001,
    "po_null_expected": .005, "po_null_price": .003, "po_received_null_but_status_received": .003,
    "po_orphan_supplier": .002,
    "cust_null_location": .02, "cust_null_name": .005, "cust_null_active_days": .03,
    "cust_duplicates": .003, "sup_null_qc": .03,
}


# ----------------------------------------------------------------------------------
# 2. MASTER BUILDERS
# ----------------------------------------------------------------------------------
def build_skus(rng):
    skus = []
    for i, (name, cat, cost, tier, season, wkend, xyz) in enumerate(CATALOG):
        skus.append(dict(
            idx=i, sku_id=f"SKU{i + 1:03d}", item_name=name, category=cat, cost=float(cost), tier=tier,
            season=season, weekend=wkend, xyz=xyz, dead=name in DEAD, perishable=name in PERISHABLE,
            pop=TIER_POP[tier] * float(rng.lognormal(0, .25)), pack=PACK[tier],
            cover=10 if name in PERISHABLE else 30,
            sell_price=round(cost * float(rng.uniform(1.25, 1.55)), 2),
            holding_cost=round(cost * 0.22, 2)))            # per unit per YEAR
    return skus


def build_suppliers(rng, skus):
    rows, updates, sku_sups, base_price, new_price, disc = [], [], {}, {}, {}, {}
    for s in skus:
        if s["item_name"] in FORCED:
            ids = FORCED[s["item_name"]]
        else:
            pool = CATEGORY_POOL[s["category"]]
            if s["item_name"] in SINGLE_SOURCE:
                ids = [str(rng.choice(pool))]
            else:
                k = min(len(pool), int(rng.integers(2, 4)))
                ids = [str(x) for x in rng.choice(pool, size=k, replace=False)]
        sku_sups[s["idx"]] = ids
        for sid in ids:
            _, name, city, _, ontime, qc, pf = SUPPLIERS[SUP_IDX[sid]]
            price = round(s["cost"] * pf * float(rng.uniform(.97, 1.03)), 2)
            d = float(rng.choice([np.nan, .02, .03, .05, .08], p=[.3, .2, .2, .2, .1]))
            row = dict(supplier_id=sid, sku_id=s["sku_id"], unit_price=price, location=city,
                       qc_rating=round(float(np.clip(qc + rng.normal(0, .2), 1, 5)), 1),
                       supply_rating=round(float(np.clip(ontime * 5 + rng.normal(0, .3), 1, 5)), 1),
                       discount=d, supplier_name=name, updated_at=START_DATE)
            rows.append(row)
            key = (sid, s["sku_id"])
            base_price[key], disc[key] = price, d
            if rng.random() < .30:  # price change on CHANGE_DATE (75% increases)
                f = rng.uniform(1.04, 1.15) if rng.random() < .75 else rng.uniform(.92, .98)
                new_price[key] = round(price * float(f), 2)
                u = dict(row)
                u["unit_price"], u["updated_at"] = new_price[key], CHANGE_DATE
                updates.append(u)
    return pd.DataFrame(rows), pd.DataFrame(updates), sku_sups, base_price, new_price, disc


def build_customers(rng, n):
    seg = rng.choice(SEGMENTS, size=n, p=SEG_P)
    city = rng.choice(len(CITY_NAMES), size=n, p=CITY_P)
    start, end, w = np.zeros(n, int), np.full(n, N_DAYS - 1), np.zeros(n)
    for i, s in enumerate(seg):
        if s == "champion": w[i] = 5
        elif s == "regular": w[i] = 1.8
        elif s == "occasional": w[i] = .5
        elif s == "new": w[i] = 2; start[i] = rng.integers(90, 166)
        elif s == "at_risk": w[i] = 2; end[i] = rng.integers(95, 131)    # quiet for 50-85 days
        else: w[i] = 2; end[i] = rng.integers(15, 76)                    # lost: quiet 100+ days
    lvl0 = np.array([rng.choice(3, p=LEVEL_P[s]) for s in seg])
    lvl1 = lvl0.copy()
    for i, s in enumerate(seg):
        if rng.random() < .18:
            if s in ("champion", "regular", "new"): lvl1[i] = min(2, lvl0[i] + 1)
            elif s in ("at_risk", "lost"): lvl1[i] = max(0, lvl0[i] - 1)
    signup = [START_DATE + timedelta(days=int(start[i])) if seg[i] == "new"
              else START_DATE - timedelta(days=int(rng.integers(30, 900))) for i in range(n)]
    names = [f"{rng.choice(FIRST)} {rng.choice(LAST)}" for _ in range(n)]
    return dict(n=n, ids=[f"C{i + 1:05d}" for i in range(n)], names=names, seg=seg, city=city,
                start=start, end=end, w=w, lvl0=lvl0, lvl1=lvl1, signup=signup)


# ----------------------------------------------------------------------------------
# 3. PASS 1 - DEMAND (orders / baskets), independent of stock
# ----------------------------------------------------------------------------------
def generate_demand(rng, skus, cust, rate):
    nsku, ncust = len(skus), cust["n"]
    days = np.arange(N_DAYS)
    prog = days / (N_DAYS - 1)
    weekend = np.array([d.weekday() >= 5 for d in DATES])
    W = np.zeros((N_DAYS, nsku))
    for j, s in enumerate(skus):
        m = np.ones(N_DAYS)
        if s["season"] == "summer": m = .55 + 1.6 * prog ** 1.3
        elif s["season"] == "winter": m = 1.9 - 1.5 * prog
        elif s["season"] == "festive": m = .4 + 4.0 * np.exp(-.5 * ((days - FESTIVE_IDX) / 6.0) ** 2)
        if s["weekend"]: m = m * np.where(weekend, 1.4, .9)
        sg = XYZ_SIGMA[s["xyz"]]
        w = s["pop"] * m * rng.lognormal(-sg ** 2 / 2, sg, N_DAYS)
        if s["dead"]: w = np.where(days > DEAD_IDX, 0.0, w)
        W[:, j] = w
    name_idx = {s["item_name"]: s["idx"] for s in skus}
    partners = defaultdict(list)
    for a, b in AFFINITY:
        partners[name_idx[a]].append(name_idx[b]); partners[name_idx[b]].append(name_idx[a])
    promo_days = set(int(x) for x in rng.choice(np.arange(10, N_DAYS - 5), size=5, replace=False))
    cust_rate = cust["w"] * rate
    L = defaultdict(list)
    O_day, O_cust, day_start = [], [], []
    for d in range(N_DAYS):
        f = (1.2 if DATES[d].weekday() >= 5 else 1.0) * (1.8 if d in promo_days else 1.0)
        f *= 1 + .15 * d / (N_DAYS - 1)                                    # mild growth
        active = (cust["start"] <= d) & (cust["end"] >= d)
        p = np.minimum(cust_rate * f * active, .95)
        buyers = np.nonzero(rng.random(ncust) < p)[0]
        cdf = np.cumsum(W[d]); cdf = cdf / cdf[-1]
        lvl = cust["lvl1"] if d >= CHANGE_IDX else cust["lvl0"]
        day_start.append(len(L["sku"]))
        for c in buyers:
            n_lines = int(rng.choice([1, 2, 3, 4, 5], p=[.30, .30, .20, .12, .08]))
            first = min(int(np.searchsorted(cdf, rng.random())), nsku - 1)
            chosen = [first]
            if partners[first] and rng.random() < .5:                       # affinity pair
                pj = int(rng.choice(partners[first]))
                if W[d, pj] > 0: chosen.append(pj)
            tries = 0
            while len(chosen) < n_lines and tries < 20:
                k = min(int(np.searchsorted(cdf, rng.random())), nsku - 1); tries += 1
                if k not in chosen: chosen.append(k)
            disc = float(LEVEL_DISC[lvl[c]]) + (.10 if d in promo_days else 0) + (.05 if rng.random() < .05 else 0)
            disc = round(min(disc, .25), 2)
            oi = len(O_day); O_day.append(d); O_cust.append(int(c))
            for k in chosen:
                L["day"].append(d); L["order"].append(oi); L["cust"].append(int(c)); L["sku"].append(k)
                L["qty"].append(1 + int(rng.poisson(TIER_QTY_LAM[skus[k]["tier"]])))
                L["disc"].append(disc)
    day_start.append(len(L["sku"]))
    out = {k: np.array(v) for k, v in L.items()}
    out["home"] = np.array([PREF_WH[cust["city"][c]][0] for c in out["cust"]])
    out["O_day"], out["O_cust"], out["day_start"] = np.array(O_day), np.array(O_cust), day_start
    out["promo_days"] = promo_days
    D = np.zeros((N_DAYS, len(WAREHOUSES), nsku))
    np.add.at(D, (out["day"], out["home"], out["sku"]), out["qty"])
    out["D"] = D
    return out


# ----------------------------------------------------------------------------------
# 4. PASS 2 - INVENTORY / PO SIMULATION
# ----------------------------------------------------------------------------------
def quoted_lead(sid, w):
    s = SUPPLIERS[SUP_IDX[sid]]
    return max(2, s[3] + int(DIST[SUP_CITY_IDX[SUP_IDX[sid]], WH_CITY_IDX[w]] / 700))


def simulate(rng, skus, cust, dem, sku_sups, base_price, new_price, disc):
    nwh, nsku = len(WAREHOUSES), len(skus)
    D = dem["D"]
    lead = np.array([[max(2, int(round(np.mean([quoted_lead(sid, w) for sid in sku_sups[s]]))))
                      for s in range(nsku)] for w in range(nwh)])
    planner_days = rng.choice([2, 3, 3, 4, 5], size=(nwh, nsku))
    dead_idx = np.array([s["idx"] for s in skus if s["dead"]])
    is_c = np.array([s["tier"] == "C" for s in skus])
    on_hand = np.zeros((nwh, nsku), dtype=np.int64)
    on_order = np.zeros((nwh, nsku), dtype=np.int64)
    last_supply = np.full((nwh, nsku), -1)
    S_oh = np.zeros((N_DAYS, nwh, nsku), dtype=np.int64)
    S_rop, S_ss = np.zeros_like(S_oh), np.zeros_like(S_oh)
    S_last = np.zeros_like(S_oh)
    arrivals, pos = defaultdict(list), []
    L_wh = np.full(len(dem["sku"]), -1)
    ds = dem["day_start"]
    po_n = 0
    rop = ss = avg = None
    for d in range(N_DAYS):
        if d == 0 or DATES[d].day == 1:                      # monthly planner revision
            lo, hi = max(0, d - 30), (d if d > 0 else 30)
            avg = np.maximum(D[lo:hi].mean(axis=0), .05)
            if d > DEAD_IDX: avg[:, dead_idx] = 0.0
            ss = np.ceil(avg * planner_days).astype(np.int64)
            rop = np.ceil(avg * lead + ss).astype(np.int64)
            if d == 0:
                cover = rng.uniform(np.where(is_c, 15, 6), np.where(is_c, 45, 22), size=(nwh, nsku))
                on_hand = np.ceil(rop + avg * cover).astype(np.int64)
        for w, s, q in arrivals.pop(d, []):                  # 1. receive POs
            on_hand[w, s] += q; on_order[w, s] -= q; last_supply[w, s] = d
        idxs = np.arange(ds[d], ds[d + 1]); rng.shuffle(idxs)
        for i in idxs:                                       # 2. fulfil lines
            s, q = dem["sku"][i], dem["qty"][i]
            for w in PREF_WH[cust["city"][dem["cust"][i]]]:
                if on_hand[w, s] >= q:
                    on_hand[w, s] -= q; L_wh[i] = w; break
        S_oh[d], S_rop[d], S_ss[d], S_last[d] = on_hand, rop, ss, last_supply   # 3. snapshot
        trig = np.argwhere((on_hand + on_order <= rop) & (rop > 0))             # 4. reorder
        for w, s in trig:
            w, s = int(w), int(s)
            sk = skus[s]
            p_now = on_hand[w, s] + on_order[w, s]
            target = rop[w, s] + avg[w, s] * sk["cover"]                         # order-up-to
            qty = int(math.ceil(max(target - p_now, 1) / sk["pack"]) * sk["pack"])
            ids = sku_sups[s]
            pr = np.array([.6, .25, .15][:len(ids)]); pr = pr / pr.sum()
            sid = ids[int(rng.choice(len(ids), p=pr))]
            sup = SUPPLIERS[SUP_IDX[sid]]
            ql = quoted_lead(sid, w)
            actual = max(1, ql + int(rng.choice([-1, 0, 0, 0]))) if rng.random() < sup[4] \
                else ql + int(rng.integers(2, 9))
            key = (sid, sk["sku_id"])
            price = new_price[key] if (d >= CHANGE_IDX and key in new_price) else base_price[key]
            dsc = disc[key]
            unit = round(price * (1 - dsc), 2) if (qty * price >= 15000 and not np.isnan(dsc)) else price
            po_n += 1
            rec_idx = d + actual
            rec = dict(po_id=f"PO{po_n:06d}", supplier_id=sid, sku_id=sk["sku_id"], warehouse_id=WH_IDS[w],
                       order_qty=qty, unit_price=unit, order_date=DATES[d],
                       expected_date=START_DATE + timedelta(days=d + ql), received_date=None)
            if rng.random() < .02:
                rec["po_status"] = "CANCELLED"
            elif rec_idx <= N_DAYS - 1:
                rec["po_status"], rec["received_date"] = "RECEIVED", DATES[rec_idx]
                arrivals[rec_idx].append((w, s, qty)); on_order[w, s] += qty
            else:
                rec["po_status"] = "OPEN"; on_order[w, s] += qty
            pos.append(rec)
    return dict(L_wh=L_wh, S_oh=S_oh, S_rop=S_rop, S_ss=S_ss, S_last=S_last, lead=lead,
                po=pd.DataFrame(pos))


# ----------------------------------------------------------------------------------
# 5. SHIPMENTS + TABLE ASSEMBLY
# ----------------------------------------------------------------------------------
def make_shipment(rng, d, w, city_idx, promo):
    dist = float(DIST[WH_CITY_IDX[w], city_idx])
    sla = 3 if dist < 50 else 4 if dist <= 700 else 6 if dist <= 1500 else 8
    hub = [k for k, p in enumerate(PARTNERS) if p[2] == WAREHOUSES[w][2]]
    k = hub[0] if (hub and rng.random() < .55) else int(rng.integers(len(PARTNERS)))
    _, _, _, speed, dprob, base, perkm = PARTNERS[k]
    lag = int(rng.choice([0, 1, 2], p=[.4, .4, .2])) + (1 if promo else 0)
    if (START_DATE + timedelta(days=d + lag)).weekday() == 6: lag += 1     # no Sunday dispatch
    transit = max(1, math.ceil(dist / speed))
    if rng.random() < dprob: transit += int(rng.integers(1, 4))
    disp, deliv = d + lag, d + lag + transit
    cost = round(max(20.0, base + perkm * dist + float(rng.normal(0, 3))), 2)
    returned = deliv <= N_DAYS - 1 and rng.random() < .03
    return dict(partner=PARTNERS[k][0], promised=d + sla, dispatch=disp, deliver=deliv, cost=cost,
                returned=returned, n=0, dist=dist)


def assemble(rng, skus, cust, dem, sim, sup_df, args):
    nsku = len(skus)
    sku_qc = {s["idx"]: float(sup_df[sup_df.sku_id == s["sku_id"]].qc_rating.mean()) for s in skus}
    # ---- shipments
    ships = {}
    for i in range(len(dem["sku"])):
        w = int(sim["L_wh"][i])
        if w < 0: continue
        key = (int(dem["order"][i]), w)
        if key not in ships:
            ships[key] = make_shipment(rng, int(dem["day"][i]), w, int(cust["city"][dem["cust"][i]]),
                                       int(dem["day"][i]) in dem["promo_days"])
        ships[key]["n"] += 1
    # ---- order lines
    rows = []
    for i in range(len(dem["sku"])):
        s = skus[int(dem["sku"][i])]
        d, q, c = int(dem["day"][i]), int(dem["qty"][i]), int(dem["cust"][i])
        w = int(sim["L_wh"][i])
        row = dict(order_id=f"ORD{int(dem['order'][i]) + 1:07d}", sku_id=s["sku_id"], item_name=s["item_name"],
                   order_date=DATES[d], quantity=q, unit_price=s["sell_price"], discount_pct=float(dem["disc"][i]),
                   amount=round(q * s["sell_price"] * (1 - float(dem["disc"][i])), 2),
                   warehouse_id=WH_IDS[int(dem["home"][i])] if w < 0 else WH_IDS[w],
                   customer_id=cust["ids"][c], delivery_partner_id=None, order_status="CANCELLED",
                   dispatch_date=None, delivered_date=None, promised_date=None, shipping_cost=None,
                   sku_rating=None)
        if w >= 0:
            sh = ships[(int(dem["order"][i]), w)]
            row.update(delivery_partner_id=sh["partner"], promised_date=DATES[sh["promised"]] if sh["promised"] < N_DAYS else None,
                       shipping_cost=round(sh["cost"] / sh["n"], 2))
            if sh["deliver"] <= N_DAYS - 1:
                row.update(order_status="RETURNED" if sh["returned"] else "DELIVERED",
                           dispatch_date=DATES[sh["dispatch"]], delivered_date=DATES[sh["deliver"]])
                if rng.random() < .35:                       # only some customers rate
                    late = sh["deliver"] > sh["promised"]
                    mu = 3.0 + .35 * sku_qc[s["idx"]] - (1.0 if late else 0) - (1.5 if sh["returned"] else 0)
                    row["sku_rating"] = int(np.clip(round(rng.normal(mu, .8)), 1, 5))
            elif sh["dispatch"] <= N_DAYS - 1:
                row.update(order_status="IN_TRANSIT", dispatch_date=DATES[sh["dispatch"]])
            else:
                row.update(order_status="PLACED")
        rows.append(row)
    orders = pd.DataFrame(rows)
    # ---- inventory snapshots (daily x warehouse x sku)
    nwh = len(WAREHOUSES)
    dd, ww, ss_ = np.meshgrid(np.arange(N_DAYS), np.arange(nwh), np.arange(nsku), indexing="ij")
    shape = (N_DAYS, nwh, nsku)
    hold = np.array([s["holding_cost"] for s in skus])
    inv = pd.DataFrame({
        "snapshot_date": DATES_OBJ[dd.ravel()],
        "warehouse_id": np.array(WH_IDS, dtype=object)[ww.ravel()],
        "sku_id": np.array([s["sku_id"] for s in skus], dtype=object)[ss_.ravel()],
        "on_hand_qty": sim["S_oh"].ravel(), "safety_stock": sim["S_ss"].ravel(),
        "lead_time": np.broadcast_to(sim["lead"], shape).ravel(), "rop": sim["S_rop"].ravel(),
        "last_supply_date": DATES_OBJ[sim["S_last"].ravel()],
        "holding_cost": np.broadcast_to(hold, shape).ravel()})
    # ---- warehouse (capacity derived from simulated peak stock)
    peak = sim["S_oh"].sum(axis=2).max(axis=0)
    wh = pd.DataFrame([dict(warehouse_id=w[0], warehouse_name=w[1], location=w[2],
                            capacity=int(math.ceil(peak[k] * float(rng.uniform(1.4, 1.9)) / 100) * 100),
                            manager_name=w[3]) for k, w in enumerate(WAREHOUSES)])
    # ---- customer
    od = pd.DataFrame({"c": dem["O_cust"], "d": dem["O_day"]}).drop_duplicates().groupby("c").size()
    order_days = np.array([int(od.get(i, 0)) for i in range(cust["n"])])
    window = cust["end"] - cust["start"] + 1
    active = np.minimum(order_days + rng.poisson(order_days * 1.2 + 3), window)
    customer = pd.DataFrame(dict(customer_id=cust["ids"], name=cust["names"],
                                 location=[CITY_NAMES[i] for i in cust["city"]], active_days=active,
                                 signup_date=cust["signup"], customer_level=[LEVELS[i] for i in cust["lvl0"]],
                                 updated_at=START_DATE))
    ch = np.nonzero(cust["lvl1"] != cust["lvl0"])[0]
    cust_upd = customer.iloc[ch].copy()
    cust_upd["customer_level"] = [LEVELS[cust["lvl1"][i]] for i in ch]
    cust_upd["updated_at"] = CHANGE_DATE
    dp = pd.DataFrame([dict(delivery_partner_id=p[0], location=p[2], partner_name=p[1]) for p in PARTNERS])
    return orders, inv, wh, customer, cust_upd, dp, ships


# ----------------------------------------------------------------------------------
# 6. DIRTY DATA INJECTION
# ----------------------------------------------------------------------------------
def _na(df, col):
    return np.nan if pd.api.types.is_float_dtype(df[col]) else pd.NA


def inject_dq(rng, T, log):
    def pick(df, frac):
        k = int(len(df) * frac)
        return rng.choice(df.index.values, size=k, replace=False) if k else np.array([], dtype=int)

    def nulls(tbl, col, key, mask=None):
        df = T[tbl]; base = df if mask is None else df[mask(df)]
        idx = pick(base, DQ[key]); df.loc[idx, col] = _na(df, col); log[f"{tbl}.{col} -> NULL"] = int(len(idx))

    o, i_, p, c = T["orders"], T["inventory"], T["purchase_orders"], T["customer"]
    nulls("orders", "item_name", "orders_null_item_name")
    nulls("orders", "customer_id", "orders_null_customer_id")
    nulls("orders", "warehouse_id", "orders_null_warehouse_id")
    nulls("orders", "delivery_partner_id", "orders_null_partner", lambda d: d.delivery_partner_id.notna())
    idx = pick(o, DQ["orders_orphan_customer"]); o.loc[idx, "customer_id"] = "C99999"
    log["orders.customer_id orphan (C99999)"] = int(len(idx))
    both = o[o.dispatch_date.notna() & o.delivered_date.notna()]
    idx = pick(both, DQ["orders_delivered_before_dispatch"])
    a, b = o.loc[idx, "dispatch_date"].values.copy(), o.loc[idx, "delivered_date"].values.copy()
    o.loc[idx, "dispatch_date"], o.loc[idx, "delivered_date"] = b, a
    log["orders delivered_date < dispatch_date"] = int(len(idx))
    idx = pick(o, DQ["orders_dirty_status"])
    o.loc[idx, "order_status"] = [str(x).lower() + " " for x in o.loc[idx, "order_status"]]
    log["orders.order_status dirty casing/space"] = int(len(idx))

    idx = pick(i_, DQ["inv_negative_on_hand"])
    i_.loc[idx, "on_hand_qty"] = -rng.integers(1, 6, size=len(idx)); log["inventory.on_hand_qty negative"] = int(len(idx))
    nulls("inventory", "safety_stock", "inv_null_safety")
    nulls("inventory", "lead_time", "inv_null_lead")
    nulls("inventory", "holding_cost", "inv_null_holding")

    nulls("purchase_orders", "expected_date", "po_null_expected")
    nulls("purchase_orders", "unit_price", "po_null_price")
    nulls("purchase_orders", "received_date", "po_received_null_but_status_received",
          lambda d: d.po_status == "RECEIVED")
    idx = pick(p, DQ["po_orphan_supplier"]); p.loc[idx, "supplier_id"] = "SUP99"
    log["purchase_orders.supplier_id orphan (SUP99)"] = int(len(idx))

    nulls("customer", "location", "cust_null_location")
    nulls("customer", "name", "cust_null_name")
    nulls("customer", "active_days", "cust_null_active_days")
    nulls("supplier", "qc_rating", "sup_null_qc")

    for tbl, key in (("orders", "orders_duplicates"), ("inventory", "inv_duplicates"), ("customer", "cust_duplicates")):
        df = T[tbl]; dup = df.loc[pick(df, DQ[key])]
        T[tbl] = pd.concat([df, dup], ignore_index=True); log[f"{tbl} exact duplicate rows"] = int(len(dup))


# ----------------------------------------------------------------------------------
# 7. WRITERS
# ----------------------------------------------------------------------------------
def write_df(df, path: Path, fmt):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "parquet": df.to_parquet(path.with_suffix(".parquet"), index=False)
    else: df.to_csv(path.with_suffix(".csv"), index=False)


def write_monthly(df, date_col, folder: Path, prefix, fmt):
    month = pd.to_datetime(df[date_col]).dt.strftime("%Y-%m")
    for m, part in df.groupby(month):
        write_df(part, folder / f"{prefix}_{m}", fmt)


# ----------------------------------------------------------------------------------
# 8. MAIN
# ----------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data"); ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--customers", type=int, default=800)
    ap.add_argument("--rate", type=float, default=.075, help="orders/day per unit customer weight")
    ap.add_argument("--format", choices=["csv", "parquet"], default="csv")
    ap.add_argument("--no-dq", action="store_true", help="skip dirty-data injection")
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    out = Path(args.out); raw, key = out / "raw", out / "answer_key"

    skus = build_skus(rng)
    sup_df, sup_upd, sku_sups, base_price, new_price, disc = build_suppliers(rng, skus)
    cust = build_customers(rng, args.customers)
    dem = generate_demand(rng, skus, cust, args.rate)
    sim = simulate(rng, skus, cust, dem, sku_sups, base_price, new_price, disc)
    orders, inv, wh, customer, cust_upd, dp, ships = assemble(rng, skus, cust, dem, sim, sup_df, args)
    po = sim["po"]

    for df, cols in ((inv, ["on_hand_qty", "safety_stock", "lead_time", "rop"]), (po, ["order_qty"]),
                     (orders, ["quantity", "sku_rating"]), (customer, ["active_days"]),
                     (cust_upd, ["active_days"])):
        for col in cols: df[col] = df[col].astype("Int64")

    T = dict(orders=orders, inventory=inv, purchase_orders=po, customer=customer, supplier=sup_df)
    log = {}
    if not args.no_dq: inject_dq(rng, T, log)

    # ---- write RAW
    write_monthly(T["orders"], "order_date", raw / "orders", "orders", args.format)
    write_monthly(T["inventory"], "snapshot_date", raw / "inventory", "inventory", args.format)
    write_monthly(T["purchase_orders"], "order_date", raw / "purchase_orders", "purchase_orders", args.format)
    write_df(T["customer"], raw / "customer", args.format)
    write_df(cust_upd, raw / "customer_updates", args.format)
    write_df(T["supplier"], raw / "supplier", args.format)
    write_df(sup_upd, raw / "supplier_updates", args.format)
    write_df(wh, raw / "warehouse", args.format)
    write_df(dp, raw / "delivery_partner", args.format)

    # ---- write ANSWER KEY
    ak = pd.DataFrame([dict(sku_id=s["sku_id"], item_name=s["item_name"], speed_tier=s["tier"],
                            variability_xyz=s["xyz"], season=s["season"], weekend_heavy=s["weekend"],
                            is_dead_stock=s["dead"], perishable=s["perishable"],
                            n_suppliers=len(sku_sups[s["idx"]]), single_source=len(sku_sups[s["idx"]]) == 1)
                       for s in skus])
    write_df(ak, key / "sku_profile", "csv")
    write_df(pd.DataFrame(dict(customer_id=cust["ids"], true_segment=cust["seg"])), key / "customer_segments", "csv")
    write_df(pd.DataFrame(SUPPLIERS, columns=["supplier_id", "name", "city", "base_lead", "true_on_time_prob",
                                              "true_qc", "price_factor"]), key / "supplier_profile", "csv")
    write_df(pd.DataFrame(PARTNERS, columns=["partner_id", "name", "hub", "km_per_day", "delay_prob",
                                             "base_cost", "cost_per_km"]), key / "partner_profile", "csv")
    (key).mkdir(parents=True, exist_ok=True)
    (key / "dq_injection_log.json").write_text(json.dumps(log, indent=2))

    # ---- summary
    n_ship = len(ships)
    breach = np.mean([s["deliver"] > s["promised"] for s in ships.values() if s["deliver"] < N_DAYS])
    recv = po[po.po_status == "RECEIVED"]
    late_po = np.mean([(r.received_date > r.expected_date) for r in recv.itertuples() if r.received_date is not None])
    print(f"window            : {START_DATE} -> {END_DATE} ({N_DAYS} days)")
    print(f"orders / lines    : {orders.order_id.nunique():,} / {len(orders):,}  (cancelled lines "
          f"{(orders.order_status == 'CANCELLED').mean():.1%}  = stockout lost sales)")
    print(f"inventory rows    : {len(inv):,}   zero-stock snapshots: {(sim['S_oh'] == 0).mean():.1%}")
    print(f"purchase orders   : {len(po):,}   late-received share: {late_po:.1%}")
    print(f"shipments         : {n_ship:,}   SLA breach (delivered): {breach:.1%}")
    print(f"customers         : {cust['n']:,}   suppliers rows: {len(sup_df)}   warehouses: {len(wh)}")
    print(f"written to        : {raw.resolve()}  (+ answer_key/)")


if __name__ == "__main__":
    main()