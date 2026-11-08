import streamlit as st
import pandas as pd
import altair as alt
import math
from pathlib import Path

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='GDP dashboard',
    page_icon=':earth_americas:',
)

# -----------------------------------------------------------------------------
# Declare some useful functions.

@st.cache_data
def get_gdp_data():
    """Grab GDP data from a CSV file."""
    DATA_FILENAME = Path(__file__).parent/'data/gdp_data.csv'
    raw_gdp_df = pd.read_csv(DATA_FILENAME)

    MIN_YEAR = 1960
    MAX_YEAR = 2022

    gdp_df = raw_gdp_df.melt(
        ['Country Code'],
        [str(x) for x in range(MIN_YEAR, MAX_YEAR + 1)],
        'Year',
        'GDP',
    )

    gdp_df['Year'] = pd.to_numeric(gdp_df['Year'])
    return gdp_df

gdp_df = get_gdp_data()

# -----------------------------------------------------------------------------
# Draw the actual page

'''
# :earth_americas: GDP dashboard

Browse GDP data from the [World Bank Open Data](https://data.worldbank.org/) website. As you'll
notice, the data only goes to 2022 right now, and datapoints for certain years are often missing.
But it's otherwise a great (and did I mention _free_?) source of data.
'''

''
''

min_value = gdp_df['Year'].min()
max_value = gdp_df['Year'].max()

from_year, to_year = st.slider(
    'Which years are you interested in?',
    min_value=min_value,
    max_value=max_value,
    value=[min_value, max_value])

countries = gdp_df['Country Code'].unique()

selected_countries = st.multiselect(
    'Which countries would you like to view?',
    countries,
    ['DEU', 'FRA', 'GBR', 'BRA', 'MEX', 'JPN'])

if not selected_countries:
    st.warning("Select at least one country")
    st.stop()

''
''
''

# Filter the data
filtered_gdp_df = gdp_df[
    (gdp_df['Country Code'].isin(selected_countries))
    & (gdp_df['Year'] <= to_year)
    & (from_year <= gdp_df['Year'])
]

# -----------------------------------------------------------------------------
# NEW: KPI scorecard

# GDP values (non-missing) for the start and end year of the selected range
start_df = gdp_df[
    (gdp_df['Year'] == from_year)
    & (gdp_df['Country Code'].isin(selected_countries))
].dropna(subset=['GDP'])[['Country Code', 'GDP']]

end_df = gdp_df[
    (gdp_df['Year'] == to_year)
    & (gdp_df['Country Code'].isin(selected_countries))
].dropna(subset=['GDP'])[['Country Code', 'GDP']]

st.header(f'Key numbers ({from_year} to {to_year})', divider='gray')

''

if end_df.empty:
    st.info(f'No GDP data available for the selected countries in {to_year}.')
else:
    total_gdp = end_df['GDP'].sum()
    avg_gdp = end_df['GDP'].mean()

    top_row = end_df.loc[end_df['GDP'].idxmax()]
    top_share = top_row['GDP'] / total_gdp * 100

    # Growth is only calculated for countries that have data in BOTH years
    both = start_df.merge(end_df, on='Country Code', suffixes=('_start', '_end'))

    if both.empty:
        total_delta = None
        fastest_name, fastest_growth = 'n/a', None
    else:
        total_delta = (both['GDP_end'].sum() / both['GDP_start'].sum() - 1) * 100
        both['growth'] = both['GDP_end'] / both['GDP_start']
        fastest = both.loc[both['growth'].idxmax()]
        fastest_name, fastest_growth = fastest['Country Code'], fastest['growth']

    k1, k2, k3, k4 = st.columns(4)

    k1.metric(
        label=f'Total GDP ({to_year})',
        value=f'${total_gdp / 1e12:,.2f}T',
        delta=f'{total_delta:+.1f}% vs {from_year}' if total_delta is not None else None,
    )
    k2.metric(
        label='Average GDP per country',
        value=f'${avg_gdp / 1e9:,.0f}B',
    )
    k3.metric(
        label='Largest economy',
        value=top_row['Country Code'],
        delta=f'{top_share:.1f}% of total',
        delta_color='off',
    )
    k4.metric(
        label='Fastest growing',
        value=fastest_name,
        delta=f'{fastest_growth:,.1f}x since {from_year}' if fastest_growth is not None else None,
    )

''
''

# -----------------------------------------------------------------------------
# Line chart (unchanged)

st.header('GDP over time', divider='gray')

''

st.line_chart(
    filtered_gdp_df,
    x='Year',
    y='GDP',
    color='Country Code',
)

''
''

# -----------------------------------------------------------------------------
# NEW: Circular (donut) chart - share of total GDP in the end year

st.header(f'Share of total GDP in {to_year}', divider='gray')

''

if end_df.empty:
    st.info(f'No GDP data available for the selected countries in {to_year}.')
else:
    pie_df = end_df.copy()
    pie_df['Share %'] = pie_df['GDP'] / pie_df['GDP'].sum() * 100
    pie_df['GDP (B)'] = pie_df['GDP'] / 1e9

    donut = (
        alt.Chart(pie_df)
        .mark_arc(innerRadius=70)  # innerRadius makes it a donut; remove for a full pie
        .encode(
            theta=alt.Theta('GDP:Q', stack=True),
            color=alt.Color('Country Code:N', title='Country'),
            tooltip=[
                alt.Tooltip('Country Code:N', title='Country'),
                alt.Tooltip('GDP (B):Q', title='GDP (billions)', format=',.0f'),
                alt.Tooltip('Share %:Q', title='Share', format='.1f'),
            ],
        )
        .properties(height=400)
    )

    st.altair_chart(donut, use_container_width=True)

''
''

# -----------------------------------------------------------------------------
# Per-country GDP cards (unchanged, but made safe for missing data)

first_year = gdp_df[gdp_df['Year'] == from_year]
last_year = gdp_df[gdp_df['Year'] == to_year]

st.header(f'GDP in {to_year}', divider='gray')

''

cols = st.columns(4)

for i, country in enumerate(selected_countries):
    col = cols[i % len(cols)]

    with col:
        first_vals = first_year[first_year['Country Code'] == country]['GDP']
        last_vals = last_year[last_year['Country Code'] == country]['GDP']

        if last_vals.empty or math.isnan(last_vals.iat[0]):
            st.metric(label=f'{country} GDP', value='n/a')
            continue

        last_gdp = last_vals.iat[0] / 1e9
        first_gdp = first_vals.iat[0] / 1e9 if not first_vals.empty else float('nan')

        if math.isnan(first_gdp):
            growth = 'n/a'
            delta_color = 'off'
        else:
            growth = f'{last_gdp / first_gdp:,.2f}x'
            delta_color = 'normal'

        st.metric(
            label=f'{country} GDP',
            value=f'{last_gdp:,.0f}B',
            delta=growth,
            delta_color=delta_color,
        )
