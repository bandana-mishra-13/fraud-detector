from datetime import timedelta
import pandas as pd
from ..models.schemas import QueryFilters


def resolve_customer_accounts(customer: str, accounts: pd.DataFrame) -> list[str]:
    """Map a customer reference to account numbers."""
    ref = customer.strip()
    number = ref.lstrip("#")
    
    # Use case-insensitive matching for robustness
    by_id = accounts[accounts["entity_id"].astype(str).str.fullmatch(ref, case=False, na=False)]
    if not by_id.empty:
        return by_id["account"].tolist()
        
    by_name = accounts[
        accounts["entity_name"].astype(str).str.lower().str.endswith(f"#{number}".lower(), na=False)
    ]
    return by_name["account"].tolist()


def apply_filters(
    df: pd.DataFrame,
    f: QueryFilters,
    accounts: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Return (filtered_frame, summary-of-what-was-applied)."""
    applied: dict = {"rows_before": int(len(df))}
    out = df

    # 1. DATE FILTERS (Safe timestamp handling)
    if f.last_n_days is not None and not out.empty:
        anchor = out["timestamp"].max()
        cutoff = anchor - timedelta(days=f.last_n_days)
        out = out[out["timestamp"] >= cutoff]
        applied["last_n_days"] = {"days": f.last_n_days, "cutoff": str(cutoff)}
        
    if f.date_from is not None:
        safe_from = pd.to_datetime(f.date_from)
        out = out[out["timestamp"] >= safe_from]
        applied["date_from"] = str(f.date_from)
        
    if f.date_to is not None:
        safe_to = pd.to_datetime(f.date_to)
        out = out[out["timestamp"] <= safe_to]
        applied["date_to"] = str(f.date_to)

    # 2. AMOUNT FILTERS (Checks both sent and received amounts)
    if f.min_amount is not None:
        out = out[(out["amount_paid"] >= f.min_amount) | (out["amount_received"] >= f.min_amount)]
        applied["min_amount"] = f.min_amount
        
    if f.max_amount is not None:
        out = out[(out["amount_paid"] <= f.max_amount) | (out["amount_received"] <= f.max_amount)]
        applied["max_amount"] = f.max_amount

    # 3. CATEGORICAL FILTERS (Case-insensitive matching to prevent LLM typos)
    if f.currency:
        clean_curr = str(f.currency).strip().upper()
        out = out[out["payment_currency"].astype(str).str.upper() == clean_curr]
        applied["currency"] = f.currency
        
    if f.payment_format:
        clean_fmt = str(f.payment_format).strip().lower()
        out = out[out["payment_format"].astype(str).str.lower() == clean_fmt]
        applied["payment_format"] = f.payment_format
        
    if f.bank:
        clean_bank = str(f.bank).strip().lower()
        out = out[
            (out["from_bank"].astype(str).str.lower() == clean_bank) | 
            (out["to_bank"].astype(str).str.lower() == clean_bank)
        ]
        applied["bank"] = f.bank

    # 4. ACCOUNT & CUSTOMER FILTERS (FIXED FATAL SILENT LEAK BUG)
    filter_requested = False
    target_accounts: list[str] = []

    if f.account:
        filter_requested = True
        target_accounts = [f.account]
        applied["account"] = f.account
    elif f.customer:
        filter_requested = True
        if accounts is not None:
            target_accounts = resolve_customer_accounts(f.customer, accounts)
        applied["customer"] = {"ref": f.customer, "accounts": target_accounts}

    # Only filter if the user explicitly asked for an account/customer
    if filter_requested:
        if not target_accounts:
            # If they asked for a customer/account and we found nothing, return 0 rows!
            out = out.iloc[0:0]
        else:
            out = out[
                out["from_account"].isin(target_accounts)
                | out["to_account"].isin(target_accounts)
            ]

    applied["rows_after"] = int(len(out))
    return out, applied
