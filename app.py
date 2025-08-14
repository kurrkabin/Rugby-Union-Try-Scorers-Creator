# app.py
# Bet365 Tryscorers -> 5 clean columns (SelectionName | SelectionOdds | FirstOdds | LastOdds | AnyOdds)
# Streamlit port of the original Colab/ipwidgets app (logic unchanged)

import re
import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="🏉 Rugby Union Tryscorers", layout="wide")

# ---------- Parser helpers (unchanged logic) ----------
def _norm(text: str) -> list[str]:
    t = re.sub(r'\r\n?', '\n', text)
    t = re.sub(r'\n{2,}', '\n', t)
    return [ln.strip() for ln in t.split('\n') if ln.strip()]

def _idx(lines, token):
    token = token.strip().lower()
    for i, ln in enumerate(lines):
        if ln.strip().lower() == token:
            return i
    return -1

def _collect_names(lines, start, end):
    keep = []
    for ln in lines[start+1:end]:
        if ln in {"BB", "ET Extra Chance"}:
            continue
        if ln == "No Tryscorer" or re.match(r"^[A-Za-zÀ-ÖØ-öø-ÿ'’.\- ]{2,}$", ln):
            keep.append(ln)
    return keep

def _collect_odds(lines, start, end):
    out = []
    for ln in lines[start+1:end]:
        if re.match(r"^\d+(\.\d+)?$", ln):
            out.append(float(ln))
    return out

def parse_bet365_tryscorers(raw: str) -> pd.DataFrame:
    lines = _norm(raw)
    try_i = _idx(lines, "Tryscorers")
    first_i = _idx(lines, "First")
    last_i  = _idx(lines, "Last")
    any_i   = _idx(lines, "Anytime")

    if min(try_i, first_i, last_i, any_i) == -1:
        raise ValueError("Could not find required headers: Tryscorers / First / Last / Anytime")

    names = _collect_names(lines, try_i, first_i)
    first = _collect_odds(lines, first_i, last_i)
    _last = _collect_odds(lines, last_i, any_i)   # align only (not used)
    anyt  = _collect_odds(lines, any_i, len(lines))

    m = min(len(names), len(first), len(_last), len(anyt))
    df = pd.DataFrame({
        "SelectionName": names[:m],
        "FirstOdds": first[:m],
        "AnyOdds":   anyt[:m],
    })

    # Add LastOdds = FirstOdds and blank SelectionOdds; reorder columns (same as original)
    df["LastOdds"] = df["FirstOdds"]
    df.insert(1, "SelectionOdds", "")
    df = df[["SelectionName", "SelectionOdds", "FirstOdds", "LastOdds", "AnyOdds"]]
    return df

# ---------- UI ----------
st.title("🏉 Rugby Union Tryscorers")
st.caption("Go to **Bet365 → Rugby match → Players → Allow Copy** → copy everything → paste it here. Then hit **Extract** to get the 5 columns and download CSV/XLSX.")

raw_text = st.text_area(
    "Paste here 👇",
    value="",
    height=260,
    placeholder="Paste the copied Players page content…",
)
extract = st.button("🏉 Extract", type="primary")


if extract:
    if not raw_text.strip():
        st.warning("Paste some Bet365 text first.")
    else:
        try:
            df = parse_bet365_tryscorers(raw_text.strip())
        except Exception as e:
            st.error(f"Parse error: {e}")
            df = None

        if df is not None and not df.empty:
            st.success(f"Parsed {len(df)} rows.")
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Copy boxes (5 columns) — mirrors the original UI intention
            st.subheader("Quick copy boxes")
            def fmt(x):
                s = str(x)
                if isinstance(x, float) or re.match(r"^\d+\.\d+$", s):
                    s = s.rstrip('0').rstrip('.')
                return s

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.text_area("SelectionName", "\n".join(df["SelectionName"].astype(str)), height=260)
            c2.text_area("SelectionOdds", "\n".join(df["SelectionOdds"].astype(str)), height=260)
            c3.text_area("FirstOdds", "\n".join(df["FirstOdds"].map(fmt)), height=260)
            c4.text_area("LastOdds",  "\n".join(df["LastOdds"].map(fmt)),  height=260)
            c5.text_area("AnyOdds",   "\n".join(df["AnyOdds"].map(fmt)),   height=260)

            # Downloads (same filenames as Colab result)
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            xlsx_buf = io.BytesIO()
            with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Tryscorers")
            xlsx_buf.seek(0)

            d1, d2 = st.columns(2)
            d1.download_button("Download CSV", data=csv_bytes, file_name="bet365_tryscorers.csv", mime="text/csv")
            d2.download_button("Download XLSX", data=xlsx_buf,
                               file_name="bet365_tryscorers.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
