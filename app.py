# app.py
# Bet365 Scorers (Rugby Tryscorers + AFL Goalscorers)
# Output columns: SelectionName | SelectionOdds | FirstOdds | LastOdds | AnyOdds
# Logic mirrors your Colab version.

import re
import io
import pandas as pd
import streamlit as st

st.set_page_config(page_title="🏉Rugby & AFL Scorers Extractor", layout="wide")

# ---------- Parser helpers (unchanged logic) ----------
_SCORER_HEADERS = ["Tryscorers", "Goalscorers", "Goal Scorers"]  # permissive
_NAME_ALLOW = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ'’.\- ]{2,}$")

def _norm(text: str) -> list[str]:
    t = re.sub(r"\r\n?", "\n", text)
    t = re.sub(r"\n{2,}", "\n", t)
    return [ln.strip() for ln in t.split("\n") if ln.strip()]

def _idx(lines, token):
    token = token.strip().lower()
    for i, ln in enumerate(lines):
        if ln.strip().lower() == token:
            return i
    return -1

def _find_any_index(lines, tokens):
    for tok in tokens:
        i = _idx(lines, tok)
        if i != -1:
            return i, tok
    return -1, ""

def _collect_names(lines, start, end):
    skip_exact = {
        "BB", "ET Extra Chance", "Show less", "View by", "Market", "Player",
        "New", "Bet", "Builder"
    }
    keep = []
    for ln in lines[start+1:end]:
        if ln in skip_exact:
            continue
        # skip pure numbers (jerseys/counts)
        if re.fullmatch(r"\d+(\.\d+)?", ln):
            continue
        if ln in {"No Tryscorer", "No Goalscorer"}:
            keep.append(ln); continue
        if _NAME_ALLOW.match(ln):
            keep.append(ln)
    return keep

def _collect_odds(lines, start, end):
    out = []
    for ln in lines[start+1:end]:
        if re.match(r"^\d+(\.\d+)?$", ln):
            out.append(float(ln))
    return out

def parse_bet365_scorers(raw: str) -> pd.DataFrame:
    """
    Works for Rugby 'Tryscorers' and AFL 'Goalscorers'.
    Expects headers: <Tryscorers|Goalscorers> + First + Last + Anytime
    """
    lines = _norm(raw)

    scorers_i, _ = _find_any_index(lines, _SCORER_HEADERS)
    first_i = _idx(lines, "First")
    last_i  = _idx(lines, "Last")
    any_i   = _idx(lines, "Anytime")

    if min(scorers_i, first_i, last_i, any_i) == -1:
        raise ValueError(
            "Could not find required headers: (Tryscorers|Goalscorers) / First / Last / Anytime"
        )

    names = _collect_names(lines, scorers_i, first_i)
    first = _collect_odds(lines, first_i, last_i)
    _last = _collect_odds(lines, last_i, any_i)   # alignment check; not displayed
    anyt  = _collect_odds(lines, any_i, len(lines))

    m = min(len(names), len(first), len(_last), len(anyt))
    if m == 0:
        raise ValueError(
            "No rows parsed. Make sure you copied the whole market incl. First/Last/Anytime."
        )

    df = pd.DataFrame({
        "SelectionName": names[:m],
        "FirstOdds": first[:m],
        "AnyOdds":   anyt[:m],
    })
    return df

# ---------- UI ----------
st.title("🏉🏟️ Bet365 Scorers (Rugby & AFL)")
st.caption("Go to **Bet365 → match → Players/Scorers → Allow Copy** → copy everything → paste below → hit **Extract**.")
raw_text = st.text_area("Paste here 👇", value="", height=260,
                        placeholder="Paste the copied Tryscorers / Goalscorers page content…")
extract = st.button("🏈 Extract", type="primary")  # fun icon; logic unchanged

if extract:
    if not raw_text.strip():
        st.warning("Paste some Bet365 text first.")
    else:
        try:
            df = parse_bet365_scorers(raw_text.strip())
        except Exception as e:
            st.error(f"Parse error: {e}")
            df = None

        if df is not None:
            # LastOdds mirrors FirstOdds; add blank SelectionOdds; reorder
            df["LastOdds"] = df["FirstOdds"]
            df.insert(1, "SelectionOdds", "")
            df = df[["SelectionName", "SelectionOdds", "FirstOdds", "LastOdds", "AnyOdds"]]

            st.success(f"Parsed {len(df)} rows.")
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Copy boxes (same as your Colab UX)
            st.subheader("Quick copy boxes")
            def fmt(x):
                s = str(x)
                if isinstance(x, float) or re.match(r"^\d+\.\d+$", s):
                    s = s.rstrip("0").rstrip(".")
                return s

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.text_area("SelectionName", "\n".join(df["SelectionName"].astype(str)), height=260)
            c2.text_area("SelectionOdds", "\n".join(df["SelectionOdds"].astype(str)), height=260)
            c3.text_area("FirstOdds", "\n".join(df["FirstOdds"].map(fmt)), height=260)
            c4.text_area("LastOdds",  "\n".join(df["LastOdds"].map(fmt)),  height=260)
            c5.text_area("AnyOdds",   "\n".join(df["AnyOdds"].map(fmt)),   height=260)

            # Downloads
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            xlsx_buf = io.BytesIO()
            with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Scorers")
            xlsx_buf.seek(0)

            d1, d2 = st.columns(2)
            d1.download_button("Download CSV", data=csv_bytes,
                               file_name="bet365_scorers.csv", mime="text/csv")
            d2.download_button("Download XLSX", data=xlsx_buf,
                               file_name="bet365_scorers.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
