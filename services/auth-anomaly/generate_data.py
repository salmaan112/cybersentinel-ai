"""
Generates synthetic login event logs for training the auth-anomaly detector.
No real credentials or breached data are used anywhere — every user, IP, and
timestamp here is fabricated by Faker plus explicit rule-based attack injection.

Attack patterns injected (labeled so we can train + evaluate against them):
  - credential_stuffing: one IP hitting many distinct usernames rapidly
  - brute_force: one IP hitting one username with many rapid failures
  - impossible_travel: same user, two logins from far-apart geos, too fast
"""
import random
import json
from datetime import datetime, timedelta
from faker import Faker
import pandas as pd

fake = Faker()
random.seed(42)
Faker.seed(42)

N_USERS = 300
NORMAL_LOGINS_PER_USER = 15
GEOS = [
    ("Bangalore", 12.9716, 77.5946), ("Mumbai", 19.0760, 72.8777),
    ("Delhi", 28.7041, 77.1025), ("London", 51.5074, -0.1278),
    ("New York", 40.7128, -74.0060), ("Singapore", 1.3521, 103.8198),
    ("Tokyo", 35.6762, 139.6503), ("Sydney", -33.8688, 151.2093),
]


def haversine_km(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, sqrt, atan2
    R = 6371
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lat1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def gen_normal_logs(users):
    rows = []
    for user_id in users:
        home_geo = random.choice(GEOS)
        home_ip = fake.ipv4_public()
        start = datetime(2026, 1, 1) + timedelta(days=random.randint(0, 200))
        for _ in range(NORMAL_LOGINS_PER_USER):
            start += timedelta(hours=random.randint(6, 72))  # spaced out, human-like
            rows.append({
                "user_id": user_id, "timestamp": start, "ip": home_ip,
                "city": home_geo[0], "lat": home_geo[1], "lon": home_geo[2],
                "success": 1, "label": "normal",
            })
    return rows


def gen_credential_stuffing(users):
    """One attacker IP rapidly tries many different usernames."""
    rows = []
    attacker_ip = fake.ipv4_public()
    geo = random.choice(GEOS)
    start = datetime(2026, 6, 1, 3, 0, 0)
    targets = random.sample(users, min(40, len(users)))
    for user_id in targets:
        start += timedelta(seconds=random.randint(1, 4))  # inhumanly fast
        rows.append({
            "user_id": user_id, "timestamp": start, "ip": attacker_ip,
            "city": geo[0], "lat": geo[1], "lon": geo[2],
            "success": random.choice([0, 0, 0, 1]),  # mostly fails, occasional hit
            "label": "credential_stuffing",
        })
    return rows


def gen_brute_force(users):
    """One attacker IP hammers a single username with many failed attempts."""
    rows = []
    attacker_ip = fake.ipv4_public()
    geo = random.choice(GEOS)
    target_user = random.choice(users)
    start = datetime(2026, 6, 5, 2, 0, 0)
    for _ in range(50):
        start += timedelta(seconds=random.randint(1, 3))
        rows.append({
            "user_id": target_user, "timestamp": start, "ip": attacker_ip,
            "city": geo[0], "lat": geo[1], "lon": geo[2],
            "success": 0, "label": "brute_force",
        })
    return rows


def gen_impossible_travel(users):
    """Same legit user, two logins from geographically distant cities too
    close together in time to be physically possible."""
    rows = []
    targets = random.sample(users, min(20, len(users)))
    for user_id in targets:
        geo_a, geo_b = random.sample(GEOS, 2)
        t1 = datetime(2026, 7, 1) + timedelta(days=random.randint(0, 60))
        t2 = t1 + timedelta(minutes=random.randint(5, 45))  # too fast for real travel
        rows.append({"user_id": user_id, "timestamp": t1, "ip": fake.ipv4_public(),
                      "city": geo_a[0], "lat": geo_a[1], "lon": geo_a[2],
                      "success": 1, "label": "normal"})
        rows.append({"user_id": user_id, "timestamp": t2, "ip": fake.ipv4_public(),
                      "city": geo_b[0], "lat": geo_b[1], "lon": geo_b[2],
                      "success": 1, "label": "impossible_travel"})
    return rows


def gen_noisy_normal_edge_cases(users):
    """Realistic-but-benign patterns that LOOK a bit suspicious, so the model
    has to learn more than a single hard threshold. Without these, attacks
    are trivially separable and the model learns nothing meaningful."""
    rows = []

    # Case 1: user mistypes password, retries within seconds (fast but benign)
    typo_users = random.sample(users, min(30, len(users)))
    for user_id in typo_users:
        geo = random.choice(GEOS)
        ip = fake.ipv4_public()
        start = datetime(2026, 4, 1) + timedelta(days=random.randint(0, 100))
        for attempt in range(random.randint(2, 4)):
            start += timedelta(seconds=random.randint(3, 15))
            rows.append({
                "user_id": user_id, "timestamp": start, "ip": ip,
                "city": geo[0], "lat": geo[1], "lon": geo[2],
                "success": 1 if attempt == 2 else 0,  # fails then succeeds
                "label": "normal",
            })

    # Case 2: shared office/campus IP — several distinct legit users, same IP,
    # loosely clustered in time (looks a bit like credential stuffing but isn't)
    office_ip = fake.ipv4_public()
    geo = random.choice(GEOS)
    office_users = random.sample(users, min(15, len(users)))
    start = datetime(2026, 5, 1, 9, 0, 0)
    for user_id in office_users:
        start += timedelta(minutes=random.randint(2, 8))  # normal office arrival spread
        rows.append({
            "user_id": user_id, "timestamp": start, "ip": office_ip,
            "city": geo[0], "lat": geo[1], "lon": geo[2],
            "success": 1, "label": "normal",
        })

    # Case 3: legit user travels for work, logs in from a new city days later
    # (large distance, but plausible elapsed time — should NOT trigger impossible travel)
    travel_users = random.sample(users, min(15, len(users)))
    for user_id in travel_users:
        geo_a, geo_b = random.sample(GEOS, 2)
        t1 = datetime(2026, 8, 1) + timedelta(days=random.randint(0, 30))
        t2 = t1 + timedelta(hours=random.randint(20, 48))  # plausible flight + settle time
        rows.append({"user_id": user_id, "timestamp": t1, "ip": fake.ipv4_public(),
                      "city": geo_a[0], "lat": geo_a[1], "lon": geo_a[2],
                      "success": 1, "label": "normal"})
        rows.append({"user_id": user_id, "timestamp": t2, "ip": fake.ipv4_public(),
                      "city": geo_b[0], "lat": geo_b[1], "lon": geo_b[2],
                      "success": 1, "label": "normal"})

    return rows


def main():
    users = [f"user_{i:04d}" for i in range(N_USERS)]

    rows = []
    rows += gen_normal_logs(users)
    rows += gen_credential_stuffing(users)
    rows += gen_brute_force(users)
    rows += gen_impossible_travel(users)
    rows += gen_noisy_normal_edge_cases(users)

    df = pd.DataFrame(rows).sort_values(["user_id", "timestamp"]).reset_index(drop=True)
    df.to_csv("data/login_logs.csv", index=False)

    print(f"Total rows: {len(df)}")
    print(df["label"].value_counts())


if __name__ == "__main__":
    main()
