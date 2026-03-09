from __future__ import annotations

"""
Seed the Supabase tables with 1000+ realistic insurance records.

Usage:
    python -m database.seed
"""

import random
from datetime import date, timedelta
from faker import Faker
from database.connection import get_client

fake = Faker()
Faker.seed(42)
random.seed(42)

US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Illinois", "Indiana",
    "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland",
    "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri",
    "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey",
    "New Mexico", "New York", "North Carolina", "Ohio", "Oklahoma",
    "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "Tennessee",
    "Texas", "Utah", "Vermont", "Virginia", "Washington", "Wisconsin",
]

POLICY_TYPES = ["health", "auto", "life", "property", "travel"]

PROVIDERS = [
    "SafeGuard Insurance Co.", "National Shield Corp.", "TrustLife Assurance",
    "PrimeCover Group", "AllState Mutual", "Pinnacle Insurance Ltd.",
    "Horizon Underwriters", "Liberty Mutual Partners", "BlueCross Shield",
    "Evergreen Risk Corp.", "Patriot Insurance Inc.", "Summit Coverage LLC",
]

CLAIM_TYPES = ["medical", "collision", "theft", "property_damage", "death_benefit", "natural_disaster"]
CLAIM_STATUSES = ["filed", "under_review", "approved", "denied", "settled", "fraud_flagged"]
PAYMENT_METHODS_NOT_USED = []  # kept for compat

ADJUSTER_NAMES = [fake.name() for _ in range(25)]

DENIAL_REASONS = [
    "Pre-existing condition not covered",
    "Claim filed after coverage expiration",
    "Insufficient documentation provided",
    "Policy exclusion applies",
    "Duplicate claim submission",
    "Exceeds coverage limit",
    "Deductible not met",
    "Non-covered incident type",
    "Policyholder lapsed on premium payments",
    "Investigation found inconsistencies",
]


def seed_policyholders(count: int = 400):
    print(f"Seeding {count} policyholders...")
    client = get_client()
    batch = []
    emails_seen = set()

    for _ in range(count):
        first = fake.first_name()
        last = fake.last_name()
        email = f"{first.lower()}.{last.lower()}{random.randint(1, 999)}@{'gmail.com' if random.random() > 0.3 else 'yahoo.com'}"
        while email in emails_seen:
            email = f"{first.lower()}.{last.lower()}{random.randint(1, 9999)}@gmail.com"
        emails_seen.add(email)

        dob = fake.date_of_birth(minimum_age=21, maximum_age=75)
        start = fake.date_between(start_date=date(2020, 1, 1), end_date=date(2025, 6, 30))
        end = start + timedelta(days=random.choice([365, 730, 1095]))
        is_active = end >= date.today()

        batch.append({
            "first_name": first,
            "last_name": last,
            "email": email,
            "phone": fake.phone_number()[:15],
            "date_of_birth": dob.isoformat(),
            "gender": random.choice(["Male", "Female", "Other"]),
            "address": fake.street_address(),
            "city": fake.city(),
            "state": random.choice(US_STATES),
            "zip_code": fake.zipcode(),
            "policy_start_date": start.isoformat(),
            "policy_end_date": end.isoformat(),
            "premium_amount": round(random.uniform(50, 800), 2),
            "risk_score": random.randint(10, 95),
            "is_active": is_active,
        })

    for i in range(0, len(batch), 50):
        chunk = batch[i: i + 50]
        client.table("policyholders").insert(chunk).execute()

    print(f"  Inserted {count} policyholders.")
    return count


def seed_policies(count: int = 100):
    print(f"Seeding {count} policies...")
    client = get_client()
    batch = []
    numbers_seen = set()

    for i in range(count):
        ptype = random.choice(POLICY_TYPES)
        prefix = {"health": "HLT", "auto": "AUT", "life": "LIF", "property": "PRP", "travel": "TRV"}[ptype]
        num = f"{prefix}-{random.randint(100000, 999999)}"
        while num in numbers_seen:
            num = f"{prefix}-{random.randint(100000, 999999)}"
        numbers_seen.add(num)

        coverage = round(random.uniform(10000, 500000), 2)
        deductible = round(coverage * random.uniform(0.01, 0.1), 2)
        monthly = round(coverage * random.uniform(0.002, 0.015), 2)

        batch.append({
            "policy_number": num,
            "policy_type": ptype,
            "provider_name": random.choice(PROVIDERS),
            "coverage_amount": coverage,
            "deductible": deductible,
            "premium_monthly": monthly,
            "tenure_months": random.choice([6, 12, 24, 36, 60]),
            "terms_summary": f"Standard {ptype} coverage with {prefix} tier benefits.",
            "is_active": random.random() > 0.08,
        })

    for i in range(0, len(batch), 50):
        chunk = batch[i: i + 50]
        client.table("policies").insert(chunk).execute()

    print(f"  Inserted {count} policies.")
    return count


def seed_claims(count: int = 600):
    print(f"Seeding {count} claims...")
    client = get_client()

    ph_resp = client.table("policyholders").select("id").execute()
    pol_resp = client.table("policies").select("id, coverage_amount").execute()

    ph_ids = [p["id"] for p in ph_resp.data]
    pol_data = {p["id"]: float(p["coverage_amount"]) for p in pol_resp.data}
    pol_ids = list(pol_data.keys())

    if not ph_ids or not pol_ids:
        print("  ERROR: Seed policyholders and policies first.")
        return 0

    batch = []
    claim_nums_seen = set()

    for _ in range(count):
        pid = random.choice(ph_ids)
        polid = random.choice(pol_ids)
        ctype = random.choice(CLAIM_TYPES)
        coverage = pol_data[polid]

        claim_amt = round(random.uniform(500, min(coverage, 200000)), 2)

        status = random.choices(
            CLAIM_STATUSES,
            weights=[10, 15, 35, 15, 20, 5],
        )[0]

        approved_amt = None
        denial_reason = None
        fraud_flag = False
        resolved_date = None

        if status == "approved":
            approved_amt = round(claim_amt * random.uniform(0.6, 1.0), 2)
        elif status == "settled":
            approved_amt = round(claim_amt * random.uniform(0.4, 0.95), 2)
            resolved_date = fake.date_time_between(start_date="-6m", end_date="now").isoformat()
        elif status == "denied":
            denial_reason = random.choice(DENIAL_REASONS)
            resolved_date = fake.date_time_between(start_date="-6m", end_date="now").isoformat()
        elif status == "fraud_flagged":
            fraud_flag = True
            denial_reason = "Suspected fraudulent claim — under investigation"

        filed = fake.date_time_between(start_date="-2y", end_date="now")

        cnum = f"CLM-{random.randint(100000, 999999)}"
        while cnum in claim_nums_seen:
            cnum = f"CLM-{random.randint(100000, 999999)}"
        claim_nums_seen.add(cnum)

        batch.append({
            "policyholder_id": pid,
            "policy_id": polid,
            "claim_number": cnum,
            "claim_type": ctype,
            "claim_amount": claim_amt,
            "approved_amount": approved_amt,
            "status": status,
            "filed_date": filed.isoformat(),
            "resolved_date": resolved_date,
            "adjuster_name": random.choice(ADJUSTER_NAMES),
            "fraud_flag": fraud_flag,
            "denial_reason": denial_reason,
            "notes": fake.sentence() if random.random() > 0.5 else None,
        })

    for i in range(0, len(batch), 50):
        chunk = batch[i: i + 50]
        client.table("claims").insert(chunk).execute()

    print(f"  Inserted {count} claims.")
    return count


def seed_all():
    p = seed_policyholders(400)
    pol = seed_policies(100)
    c = seed_claims(600)
    total = p + pol + c
    print(f"\nTotal records seeded: {total}")
    return total


if __name__ == "__main__":
    seed_all()
