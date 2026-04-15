# Imports I used, went with streamlit because the Jupyter Widgets weren't robust enough for this
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
matplotlib.use('Agg')

st.set_page_config(page_title="NFL Data Explorer", layout="wide")

# Load the data and clean up the column names so they are easier to work with
@st.cache_data
def load_data():
    # 2023 NFL Dataset I found for free ProFootballFocus
    # This dataset be used for free for academic and non-commercial purposes like this
    df = pd.read_csv("NFL_Data.csv")

    # Rename the columns to something more readable
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

# This dictionary maps words the user might type to the actual column name in the dataframe
# My version of using an LLM. just preprogramming certain words and phrases
# I tried implementing API calls to different models but couldn't find any that were free,
# so this is a good second

# Longer phrases are checked first so something like "points allowed" doesnt
# accidentally match just "points," I figured this out after getting wrong results early on
KEYWORD_MAP = {
    "points allowed":     "points_allowed",
    "points against":     "points_allowed",
    "gave up":            "points_allowed",
    "pass yards allowed": "pass_yards_allowed",
    "passing defense":    "pass_yards_allowed",
    "rush yards allowed": "rush_yards_allowed",
    "rushing defense":    "rush_yards_allowed",
    "yards allowed":      "total_yards_allowed",
    "total defense":      "total_yards_allowed",
    "passing yards":      "pass_yards_off",
    "pass yards":         "pass_yards_off",
    "passing offense":    "pass_yards_off",
    "rushing yards":      "rush_yards_off",
    "rush yards":         "rush_yards_off",
    "rushing offense":    "rush_yards_off",
    "total yards":        "total_yards_off",
    "total offense":      "total_yards_off",
    "pass tds":           "pass_tds",
    "passing touchdowns": "pass_tds",
    "rush tds":           "rush_tds",
    "rushing touchdowns": "rush_tds",
    "interceptions thrown": "interceptions_thrown",
    "interceptions":      "interceptions_thrown",
    "turnovers":          "turnovers_off",
    "takeaways":          "takeaways",
    "turnovers forced":   "takeaways",
    "scoring percentage": "score_pct_off",
    "expected points":    "exp_pts_off",
    "points scored":      "points_for",
    "points for":         "points_for",
    "scored":             "points_for",
    "scoring":            "points_for",
    "defense":            "total_yards_allowed",
    "offense":            "total_yards_off",
    "yards":              "total_yards_off",
    "points":             "points_for",
}

# Stats where a lower number is better
LOWER_IS_BETTER = {
    "points_allowed",
    "pass_yards_allowed",
    "rush_yards_allowed",
    "total_yards_allowed",
    "interceptions_thrown",
    "turnovers_off",
    "score_pct_def",
    "exp_pts_def"
}

def find_column(text):
    # Loop through the keyword map and return the first column that matches
    for keyword in sorted(KEYWORD_MAP.keys(), key=len, reverse=True):
        if keyword in text:
            return KEYWORD_MAP[keyword]
    return None

def is_scatter_query(query):
    # Check if the user is asking to compare two things, make s a scatter instead
    scatter_words = ["vs", "versus", "compare", "scatter", "correlation", "relationship"]
    return any(word in query for word in scatter_words)


    # Try to find two columns to put on the x and y axes
def parse_scatter_query(query):

    split_words = ["vs", "versus", "compare", "and"]
    parts = [query]
    for word in split_words:
        if word in query:
            parts = query.split(word, 1)
            break

    col_x = find_column(parts[0])
    col_y = find_column(parts[1]) if len(parts) > 1 else None

    # Fall back to default columns on failure
    if col_x is None:
        col_x = "points_for"
    if col_y is None:
        col_y = "total_yards_off"

    return {"chart_type": "scatter", "col_x": col_x, "col_y": col_y}



# Methods for parcing the input query, direct way of using natural language instead of an LLM API
def parse_bar_query(query):
    col = find_column(query)
    if col is None:
        col = "points_for"

    # Figure out how many teams to show, default is 5
    n = 5
    for phrase, num in [("top 10", 10), ("10 teams", 10), ("ten", 10),
                        ("top 5", 5),  ("5 teams", 5),  ("five", 5),
                        ("top 3", 3),  ("3 teams", 3),  ("three", 3),
                        ("all 32", 32), ("all teams", 32), ("every", 32)]:
        if phrase in query:
            n = num
            break

    # Check if user wants the worst teams or the best
    wants_worst = any(w in query for w in ["worst", "bottom", "least", "fewest", "lowest", "bad", "weak"])
    wants_best  = any(w in query for w in ["best", "top", "most", "highest", "lead", "good", "strong"])

    # Sort direction depends on both the stat type and what the user typed
    if col in LOWER_IS_BETTER:
        ascending = True
        if wants_worst:
            ascending = False
    else:
        ascending = False
        if wants_worst and not wants_best:
            ascending = True

    return {"chart_type": "bar", "col": col, "n": n, "ascending": ascending}

# The feedback I got on my first build guide said to compare two outputs side by side
# This is a simple way of implementing this kind of comparison
def make_bar_variation(parsed):
    n2 = 10 if parsed["n"] <= 5 else 5
    return {
        "chart_type": "bar",
        "col": parsed["col"],
        "n": n2,
        "ascending": parsed["ascending"]
    }



    # Run the actual sort and filter on the dataframe to get the results
def get_bar_data(parsed):

    col = parsed["col"]
    n = parsed["n"]
    asc = parsed["ascending"]

    result = df[["team", col]].sort_values(col, ascending=asc).head(n).reset_index(drop=True)
    return result

# Build the SQL string for what pandas is doing
def get_sql(parsed):

    if parsed["chart_type"] == "scatter":
        col_x = parsed["col_x"]
        col_y = parsed["col_y"]
        return (
            f"SELECT team, {col_x}, {col_y}\n"
            f"FROM nfl_2023;"
        )

    col = parsed["col"]
    n = parsed["n"]
    direction = "ASC" if parsed["ascending"] else "DESC"
    return (
        f"SELECT team, {col}\n"
        f"FROM nfl_2023\n"
        f"ORDER BY {col} {direction}\n"
        f"LIMIT {n};"
    )


def make_bar_chart(data, title, excluded_teams):
    # Filter out any teams the user removed using the multiselect
    plot_data = data[~data["team"].isin(excluded_teams)]

    val_col = plot_data.columns[1]

    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(plot_data["team"], plot_data[val_col], color="#4472C4")

    ax.set_xticklabels(plot_data["team"], rotation=40, ha="right", fontsize=8)
    ax.set_ylabel(val_col)
    ax.set_title(title)

    # Show the value
    ax.bar_label(bars, fmt="%.0f", fontsize=7, padding=2)

    plt.tight_layout()
    return fig

# code to make the scatter plot
def make_scatter_chart(data, col_x, col_y):
    fig, ax = plt.subplots(figsize=(9, 5))

    ax.scatter(data[col_x], data[col_y], color="#4472C4", s=60, zorder=3)

    # Label every dot with the team name
    for _, row in data.iterrows():
        ax.annotate(
            row["team"],
            (row[col_x], row[col_y]),
            fontsize=6.5,
            xytext=(4, 4),
            textcoords="offset points"
        )

    # Add a trend line using numpy polyfit, learned this in a python class
    m, b    = np.polyfit(data[col_x], data[col_y], 1)
    x_range = np.linspace(data[col_x].min(), data[col_x].max(), 100)
    ax.plot(x_range, m * x_range + b, color="red", linestyle="--", linewidth=1, label="trend line")

    ax.set_xlabel(col_x)
    ax.set_ylabel(col_y)
    ax.set_title(f"{col_x} vs {col_y}")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.3)

    plt.tight_layout()
    return fig


# Streamlit page creation

st.title("NFL Data Explorer")
st.write("Type a question about NFL teams and get an answer. Uses natural language instead of SQL.")
st.write("---")

query   = st.text_input("Type a question:", placeholder="e.g. which teams scored the most points?")
run_btn = st.button("Run")

st.write("---")

# Maintain the session state between clicking or doing things on the page
for key, default in [
    ("last_query", ""),
    ("excluded_a", []),
    ("excluded_b", []),
    ("feedback",   None),
    ("parsed_a",   None),
    ("parsed_b",   None),
]:
    if key not in st.session_state:
        st.session_state[key] = default


if run_btn and query.strip():

    # Reset the excluded teams and feedback whenever a new question is asked
    if st.session_state.last_query != query:
        st.session_state.excluded_a = []
        st.session_state.excluded_b = []
        st.session_state.feedback = None
        st.session_state.last_query = query

    q = query.lower()

    if is_scatter_query(q):
        st.session_state.parsed_a = parse_scatter_query(q)
        st.session_state.parsed_b = None
    else:
        st.session_state.parsed_a = parse_bar_query(q)
        st.session_state.parsed_b = make_bar_variation(st.session_state.parsed_a)

elif run_btn and not query.strip():
    st.warning("Please type a question first.")


# Only show results if we have a parsed query and the query matches what is in the input box
if st.session_state.parsed_a is not None and st.session_state.last_query == query and query.strip():

    parsed_a = st.session_state.parsed_a
    parsed_b = st.session_state.parsed_b

    # Scatter plot with SQl below
    if parsed_a["chart_type"] == "scatter":
        col_x = parsed_a["col_x"]
        col_y = parsed_a["col_y"]

        scatter_data = df[["team", col_x, col_y]]

        st.subheader(f"{col_x} vs {col_y}")
        fig = make_scatter_chart(scatter_data, col_x, col_y)
        st.pyplot(fig)
        plt.close()

        # Show the correlation
        corr = scatter_data[col_x].corr(scatter_data[col_y])
        direction = "positive" if corr > 0 else "negative"
        strength = "strong" if abs(corr) > 0.6 else ("moderate" if abs(corr) > 0.3 else "weak")
        st.write(f"Correlation: **{corr:.2f}** — {strength} {direction} relationship")

        # display SQl
        st.write("Equivalent SQL query:")
        st.code(get_sql(parsed_a), language="sql")

    # Display bar chart with two interpretations side by side
    else:
        st.subheader("Two interpretations of your question")
        st.write("Both charts answer the same question but show a different number of teams. Pick which one you found more useful.")

        col_a, col_b = st.columns(2)

        with col_a:
            st.write(f"**Interpretation A — top {parsed_a['n']} teams**")

            data_a = get_bar_data(parsed_a)

            # Multiselect lets the user remove teams from the chart directly, interactive feature
            excluded_a = st.multiselect(
                "Remove teams:",
                options=data_a["team"].tolist(),
                default=st.session_state.excluded_a,
                key="excl_a"
            )
            st.session_state.excluded_a = excluded_a
            fig_a = make_bar_chart(data_a, title=f"Top {parsed_a['n']} by {parsed_a['col']}", excluded_teams=excluded_a)
            st.pyplot(fig_a)
            plt.close()

            # Show the SQL
            st.write("Equivalent SQL:")
            st.code(get_sql(parsed_a), language="sql")

            if st.button("This one is better", key="vote_a"):
                st.session_state.feedback = "A"

        with col_b:
            st.write(f"**Interpretation B — top {parsed_b['n']} teams**")

            data_b = get_bar_data(parsed_b)

            excluded_b = st.multiselect(
                "Remove teams:",
                options=data_b["team"].tolist(),
                default=st.session_state.excluded_b,
                key="excl_b"
            )
            st.session_state.excluded_b = excluded_b

            fig_b = make_bar_chart(data_b, title=f"Top {parsed_b['n']} by {parsed_b['col']}", excluded_teams=excluded_b)
            st.pyplot(fig_b)
            plt.close()

            # Show the SQL
            st.write("Equivalent SQL:")
            st.code(get_sql(parsed_b), language="sql")

            if st.button("This one is better", key="vote_b"):
                st.session_state.feedback = "B"

        # Show a confirmation when the user picks one
        if st.session_state.feedback:
            st.write(f"You preferred interpretation {st.session_state.feedback}.")


# Streamlit Sidebar
with st.sidebar:
    st.write("**Example questions to try:**")
    st.write("""
Bar charts:
- Which teams scored the most points?
- Top 10 rushing offenses
- Worst passing defense
- Most interceptions thrown
- Bottom 5 teams by points scored
- Most takeaways

Scatter plots:
- points vs yards
- passing yards vs points scored
- rushing yards vs points allowed
- turnovers vs points for
""")

    st.write("---")
    st.write("**Data preview:**")
    st.dataframe(
        df[["team", "points_for", "points_allowed", "total_yards_off"]].head(8),
        use_container_width=True
    )

st.write("---")
st.write("CS 3960 Final Project | David Perry | University of Utah")
