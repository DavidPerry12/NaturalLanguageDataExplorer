import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np

matplotlib.use('Agg')

st.set_page_config(page_title="NFL Data Explorer", page_icon="🏈", layout="wide")


# load the data and rename columns to something readable
@st.cache_data
def load_data():
    df = pd.read_csv("NFL_Combined_Data_2023.csv")
    df.columns = df.columns.str.replace('.', '_', regex=False)
    df = df.rename(columns={
        'Tm': 'team',
        'PF': 'points_for',
        'PA': 'points_allowed',
        'PassYds_offense': 'pass_yards_off',
        'RushYds_offense': 'rush_yards_off',
        'Yds_offense': 'total_yards_off',
        'TD_offense': 'pass_tds',
        'TD_1_offense': 'rush_tds',
        'Int_offense': 'interceptions_thrown',
        'TO_offense': 'turnovers_off',
        'PassYds_defense': 'pass_yards_allowed',
        'RushYds_defense': 'rush_yards_allowed',
        'Yds_defense': 'total_yards_allowed',
        'TO_defense': 'takeaways',
        'Int_defense': 'interceptions_def',
        'Sc%_offense': 'score_pct_off',
        'Sc%_defense': 'score_pct_def',
        'EXP_offense': 'exp_pts_off',
        'EXP_defense': 'exp_pts_def',
    })
    return df

df = load_data()


# dictionary that maps words a user might type to the actual column name
KEYWORD_MAP = {
    "points allowed": "points_allowed",
    "gave up": "points_allowed",
    "points against": "points_allowed",
    "pass yards allowed": "pass_yards_allowed",
    "passing defense": "pass_yards_allowed",
    "rush yards allowed": "rush_yards_allowed",
    "rushing defense": "rush_yards_allowed",
    "yards allowed": "total_yards_allowed",
    "total defense": "total_yards_allowed",
    "passing yards": "pass_yards_off",
    "pass yards": "pass_yards_off",
    "passing offense": "pass_yards_off",
    "rushing yards": "rush_yards_off",
    "rush yards": "rush_yards_off",
    "rushing offense": "rush_yards_off",
    "total yards": "total_yards_off",
    "total offense": "total_yards_off",
    "pass tds": "pass_tds",
    "passing touchdowns": "pass_tds",
    "rush tds": "rush_tds",
    "rushing touchdowns": "rush_tds",
    "interceptions thrown": "interceptions_thrown",
    "interceptions": "interceptions_thrown",
    "turnovers": "turnovers_off",
    "takeaways": "takeaways",
    "turnovers forced": "takeaways",
    "scoring percentage": "score_pct_off",
    "expected points": "exp_pts_off",
    "points scored": "points_for",
    "points for": "points_for",
    "scored": "points_for",
    "scoring": "points_for",
    "defense": "total_yards_allowed",
    "offense": "total_yards_off",
    "yards": "total_yards_off",
    "points": "points_for",
}

# stats where lower is better (like points allowed or turnovers)
LOWER_IS_BETTER = {
    "points_allowed", "pass_yards_allowed", "rush_yards_allowed",
    "total_yards_allowed", "interceptions_thrown", "turnovers_off",
    "score_pct_def", "exp_pts_def"
}


def find_column(text):
    # scan the text for keywords, check longer phrases first to avoid partial matches
    for keyword in sorted(KEYWORD_MAP.keys(), key=len, reverse=True):
        if keyword in text:
            return KEYWORD_MAP[keyword]
    return None


def is_scatter_query(query):
    # check if the user is asking for a comparison / scatter plot
    scatter_words = ["vs", "versus", "compare", "scatter", "correlation", "relationship"]
    return any(word in query for word in scatter_words)


def parse_scatter_query(query):
    # find two columns to put on the scatter plot axes
    # we split the query around the comparison word and look for a column in each half
    split_words = ["vs", "versus", "compare", "and"]
    parts = [query]
    for word in split_words:
        if word in query:
            parts = query.split(word, 1)
            break

    col_x = find_column(parts[0])
    col_y = find_column(parts[1]) if len(parts) > 1 else None

    # fall back to defaults if we couldn't find one
    if col_x is None:
        col_x = "points_for"
    if col_y is None:
        col_y = "total_yards_off"

    code = f"result = df[['team', '{col_x}', '{col_y}']]"
    return {"code": code, "chart_type": "scatter", "col_x": col_x, "col_y": col_y}


def parse_bar_query(query):
    # figure out which stat column they want
    col = find_column(query)
    if col is None:
        col = "points_for"

    # figure out how many teams to show
    n = 5
    for phrase, num in [("top 10", 10), ("10 teams", 10), ("ten", 10),
                         ("top 5", 5), ("5 teams", 5), ("five", 5),
                         ("top 3", 3), ("3 teams", 3), ("three", 3),
                         ("all 32", 32), ("all teams", 32), ("every", 32)]:
        if phrase in query:
            n = num
            break

    # figure out if they want best or worst
    wants_worst = any(w in query for w in ["worst", "bottom", "least", "fewest", "lowest", "bad", "weak"])
    wants_best  = any(w in query for w in ["best", "top", "most", "highest", "lead", "good", "strong"])

    if col in LOWER_IS_BETTER:
        # for defensive stats, best = lowest value so we sort ascending
        ascending = True
        if wants_worst:
            ascending = False
    else:
        ascending = False
        if wants_worst and not wants_best:
            ascending = True

    code = f"result = df[['team', '{col}']].sort_values('{col}', ascending={ascending}).head({n})"
    return {"code": code, "chart_type": "bar", "col": col, "n": n, "ascending": ascending}


def make_bar_variation(parsed):
    # second interpretation just shows a different number of teams
    col = parsed["col"]
    ascending = parsed["ascending"]
    n2 = 10 if parsed["n"] <= 5 else 5
    code = f"result = df[['team', '{col}']].sort_values('{col}', ascending={ascending}).head({n2})"
    return {"code": code, "chart_type": "bar", "col": col, "n": n2, "ascending": ascending}


def run_code(code_str):
    # run the generated pandas code and return the result
    local_vars = {"df": df.copy(), "pd": pd, "np": np}
    try:
        exec(code_str, {}, local_vars)
        return local_vars.get("result", None), None
    except Exception as e:
        return None, str(e)


def to_sql(parsed):
    # convert the parsed query into an equivalent SQL statement to show the user
    if parsed["chart_type"] == "scatter":
        col_x = parsed["col_x"]
        col_y = parsed["col_y"]
        return f"SELECT team, {col_x}, {col_y}\nFROM nfl_2023;"

    col = parsed["col"]
    n   = parsed["n"]
    asc = parsed["ascending"]
    direction = "ASC" if asc else "DESC"
    return f"SELECT team, {col}\nFROM nfl_2023\nORDER BY {col} {direction}\nLIMIT {n};"


def make_bar_chart(result_df, title="", excluded_teams=None):
    if excluded_teams is None:
        excluded_teams = []

    # filter out any teams the user removed
    plot_df  = result_df[~result_df[result_df.columns[0]].isin(excluded_teams)].copy()
    team_col = plot_df.columns[0]
    val_col  = plot_df.columns[1]

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(plot_df[team_col], plot_df[val_col], color="#1f77b4")
    ax.set_xticklabels(plot_df[team_col], rotation=40, ha="right", fontsize=8)
    ax.set_ylabel(val_col)
    ax.set_title(title)
    ax.bar_label(bars, fmt="%.0f", fontsize=7, padding=2)
    plt.tight_layout()
    return fig


def make_scatter_chart(result_df, col_x, col_y):
    fig, ax = plt.subplots(figsize=(9, 5))

    ax.scatter(result_df[col_x], result_df[col_y], color="#1f77b4", s=60, zorder=3)

    # label each dot with the team name
    for _, row in result_df.iterrows():
        ax.annotate(row["team"], (row[col_x], row[col_y]),
                    fontsize=6.5, xytext=(4, 4), textcoords="offset points")

    # add a trend line so you can see the correlation
    m, b = np.polyfit(result_df[col_x], result_df[col_y], 1)
    x_line = np.linspace(result_df[col_x].min(), result_df[col_x].max(), 100)
    ax.plot(x_line, m * x_line + b, color="red", linestyle="--", linewidth=1, label="trend")

    ax.set_xlabel(col_x)
    ax.set_ylabel(col_y)
    ax.set_title(f"{col_x} vs {col_y} — all 32 teams")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.3)
    plt.tight_layout()
    return fig


# ── UI ────────────────────────────────────────────────────────────────────────

st.title("🏈 NFL 2023 Data Explorer")
st.write("Ask a question about NFL teams in plain English and get instant answers from real 2023 stats.")
st.divider()

query   = st.text_input("Ask a question:", placeholder="e.g. which teams scored the most points?")
run_btn = st.button("Run", type="primary")
st.divider()

# keep track of things between reruns using session state
for key, default in [("feedback", None), ("excluded_a", []), ("excluded_b", []),
                      ("last_query", ""), ("result_a", None), ("result_b", None),
                      ("parsed_a", None), ("parsed_b", None)]:
    if key not in st.session_state:
        st.session_state[key] = default

if run_btn and query.strip():

    # reset state when user asks a new question
    if st.session_state.last_query != query:
        st.session_state.excluded_a = []
        st.session_state.excluded_b = []
        st.session_state.feedback   = None
        st.session_state.last_query = query

    q = query.lower()

    if is_scatter_query(q):
        # scatter plot query - just one interpretation since there's only one chart to show
        parsed_a = parse_scatter_query(q)
        parsed_b = None
    else:
        # bar chart query - make two interpretations with different n values
        parsed_a = parse_bar_query(q)
        parsed_b = make_bar_variation(parsed_a)

    result_a, err_a = run_code(parsed_a["code"])
    result_b = None
    err_b    = None
    if parsed_b:
        result_b, err_b = run_code(parsed_b["code"])

    st.session_state.result_a = result_a
    st.session_state.result_b = result_b
    st.session_state.parsed_a = parsed_a
    st.session_state.parsed_b = parsed_b
    st.session_state.err_a    = err_a
    st.session_state.err_b    = err_b

elif run_btn and not query.strip():
    st.warning("Please type a question first.")


# show the results
if st.session_state.result_a is not None and st.session_state.last_query == query and query.strip():

    result_a = st.session_state.result_a
    result_b = st.session_state.result_b
    parsed_a = st.session_state.parsed_a
    parsed_b = st.session_state.parsed_b

    # scatter plot - just show one full width chart
    if parsed_a["chart_type"] == "scatter":
        st.subheader(f"Scatter plot: {parsed_a['col_x']} vs {parsed_a['col_y']}")
        fig = make_scatter_chart(result_a, parsed_a["col_x"], parsed_a["col_y"])
        st.pyplot(fig)
        plt.close()

        # show correlation number
        corr = result_a[parsed_a["col_x"]].corr(result_a[parsed_a["col_y"]])
        direction = "positive" if corr > 0 else "negative"
        strength  = "strong" if abs(corr) > 0.6 else ("moderate" if abs(corr) > 0.3 else "weak")
        st.info(f"Correlation: **{corr:.2f}** — {strength} {direction} relationship")

        with st.expander("See the equivalent SQL"):
            st.code(to_sql(parsed_a), language="sql")

    # bar chart - show two interpretations side by side
    else:
        st.subheader("Two Interpretations — Which is more useful?")
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown(f"#### Interpretation A — Top {parsed_a['n']} teams")
            if isinstance(result_a, pd.DataFrame):
                team_col   = result_a.columns[0]
                excluded_a = st.multiselect(
                    "Remove teams from chart:",
                    options=result_a[team_col].tolist(),
                    default=st.session_state.excluded_a,
                    key="excl_a"
                )
                st.session_state.excluded_a = excluded_a
                fig = make_bar_chart(result_a, title=f"Top {parsed_a['n']} — {parsed_a['col']}", excluded_teams=excluded_a)
                st.pyplot(fig)
                plt.close()
            with st.expander("See the equivalent SQL"):
                st.code(to_sql(parsed_a), language="sql")
            if st.button("👍 This was more useful", key="vote_a"):
                st.session_state.feedback = "A"

        with col_b:
            st.markdown(f"#### Interpretation B — Top {parsed_b['n']} teams")
            if isinstance(result_b, pd.DataFrame):
                team_col   = result_b.columns[0]
                excluded_b = st.multiselect(
                    "Remove teams from chart:",
                    options=result_b[team_col].tolist(),
                    default=st.session_state.excluded_b,
                    key="excl_b"
                )
                st.session_state.excluded_b = excluded_b
                fig = make_bar_chart(result_b, title=f"Top {parsed_b['n']} — {parsed_b['col']}", excluded_teams=excluded_b)
                st.pyplot(fig)
                plt.close()
            with st.expander("See the equivalent SQL"):
                st.code(to_sql(parsed_b), language="sql")
            if st.button("👍 This was more useful", key="vote_b"):
                st.session_state.feedback = "B"

        if st.session_state.feedback:
            st.success(f"Got it! You preferred Interpretation {st.session_state.feedback}.")


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("💡 Try These")
    st.markdown("""
**Bar chart queries:**
- Which teams scored the most points?
- Show the top 5 rushing offenses
- Which defense allowed the fewest yards?
- Who threw the most interceptions?
- Worst rushing defense
- Bottom 5 teams by points scored

**Scatter plot queries:**
- points vs yards
- compare passing yards vs points scored
- rushing yards vs points allowed
- turnovers vs points for
""")
    st.divider()
    st.header("📋 Data Preview")
    st.dataframe(
        df[["team", "points_for", "points_allowed", "total_yards_off"]].head(8),
        use_container_width=True
    )

st.divider()
st.caption("CS 3960 Final Project · David Perry · NFL 2023 · University of Utah")
