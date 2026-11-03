import json
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BASE = Path(__file__).parent
st.set_page_config(page_title="AQIMERYL | Environmental Intelligence", page_icon="🌿", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
.block-container {padding-top:1.5rem;max-width:1350px}
.hero {padding:24px 27px;border-radius:18px;background:linear-gradient(110deg,#222044,#491f63 60%,#522e64);border:1px solid #8054a1;margin-bottom:14px}
.eyebrow {font-size:.78rem;letter-spacing:2px;color:#d9bdf2;font-weight:700}
.hero h1 {font-size:2.05rem;margin:8px 0 8px;color:white}
.hero p {max-width:780px;color:#e1d9e9;margin:0;font-size:1rem}
.smallnote {color:#b9b9d4;font-size:.85rem}
[data-testid="stMetric"]{background:#1a2136;padding:12px;border-radius:12px;border:1px solid #343c58}
</style>""", unsafe_allow_html=True)
st.markdown('<div class="hero"><div class="eyebrow">AQIMERYL · INTELLIGENCE LAB · BUILD 1.0.1 · ENVIRONMENTAL APP</div><h1>Environmental Intelligence Explorer</h1><p>Explore Toronto neighbourhood demographics and geography. Add attributed environmental measurements to investigate heat and tree-canopy patterns—without confusing exploratory associations with health outcomes.</p></div>',unsafe_allow_html=True)

@st.cache_data
def load():
    n=pd.read_csv(BASE/'data/neighbourhoods.csv')
    n['neighbourhood_id']=n['neighbourhood_id'].astype(int)
    with open(BASE/'data/boundaries.geojson',encoding='utf-8') as f: geo=json.load(f)
    for feat in geo['features']:
        feat['id']=int(feat['properties']['AREA_SHORT_CODE'])
    return n,geo

n, geo=load()
FIELDS={'Tree canopy (%)':'tree_canopy_pct','Surface temperature (°C)':'surface_temperature_c'}

@st.cache_data(show_spinner=False)
def parse_upload(content):
    from io import BytesIO
    return pd.read_csv(BytesIO(content))

def validate_env(source):
    required={'neighbourhood_id','tree_canopy_pct','surface_temperature_c','observation_year','source_url'}
    missing=required-set(source.columns)
    if missing: return None, f"Missing columns: {', '.join(sorted(missing))}"
    e=source[list(required)].copy()
    e['neighbourhood_id']=pd.to_numeric(e['neighbourhood_id'],errors='coerce')
    if e['neighbourhood_id'].isna().any() or not (e['neighbourhood_id']%1==0).all():return None,'Neighbourhood IDs must be whole numbers.'
    e['neighbourhood_id']=e['neighbourhood_id'].astype(int)
    if e['neighbourhood_id'].duplicated().any():return None,'One row per neighbourhood is required; duplicate IDs detected.'
    if not set(e.neighbourhood_id).issubset(set(n.neighbourhood_id)):return None,'Unknown neighbourhood ID found.'
    for key in FIELDS.values():
        raw=e[key].astype('string').str.strip().replace('',pd.NA)
        cleaned=pd.to_numeric(raw,errors='coerce')
        if (raw.notna() & cleaned.isna()).any():return None,f'{key} contains a nonnumeric measurement.'
        e[key]=cleaned
    if e['tree_canopy_pct'].dropna().lt(0).any() or e['tree_canopy_pct'].dropna().gt(100).any():return None,'Tree canopy percentage must be between 0 and 100.'
    e['observation_year']=e['observation_year'].astype('string').str.strip().replace('',pd.NA)
    e['source_url']=e['source_url'].astype('string').str.strip().replace('',pd.NA)
    measured=e[list(FIELDS.values())].notna().any(axis=1)
    if (measured & (e.observation_year.isna() | e.source_url.isna())).any():return None,'Every row with a measurement must have observation_year and source_url.'
    years=pd.to_numeric(e.loc[measured,'observation_year'],errors='coerce')
    if years.isna().any() or not years.between(1900,2100).all() or not (years%1==0).all():return None,'Observation years for measured rows must be valid four-digit years.'
    if (measured & ~e.source_url.fillna('').str.startswith(('http://','https://'))).any():return None,'Source URLs for measured rows must start with https:// or http://.'
    return e,None

st.sidebar.success("🌿 Environmental Intelligence · Build 1.0.1")
st.sidebar.markdown('### Explore environmental indicators')
file=st.sidebar.file_uploader('Load verified environmental measurements (CSV)',type=['csv'],help='Use the included environmental_data_template.csv, with neighbourhood_id as the join key.')
validated=None
if file:
    try:
        raw=parse_upload(file.getvalue())
        validated,error=validate_env(raw)
        if error:st.sidebar.error(error)
        else:st.sidebar.success('Measurements validated and joined by neighbourhood ID.')
    except Exception as ex:st.sidebar.error(f'Could not read CSV: {ex}')

all_df=n.merge(validated,on='neighbourhood_id',how='left',validate='one_to_one') if validated is not None else n.copy()
for key in FIELDS.values():
    if key not in all_df:all_df[key]=float('nan')
layer=st.sidebar.selectbox('Map layer',['Residents aged 65+ (%)','Low-income prevalence (%)']+list(FIELDS))
filter_text=st.sidebar.text_input('Find a neighbourhood',placeholder='e.g. Woburn')
subset=all_df[all_df.neighbourhood_name.str.contains(filter_text,case=False,regex=False,na=False)] if filter_text else all_df
if subset.empty:st.warning('No neighbourhoods match this search.');st.stop()

c1,c2,c3,c4=st.columns(4)
c1.metric('Neighbourhoods',len(subset))
c2.metric('2021 census population',f"{int(subset.age_group_sample_population.sum()):,}")
c3.metric('Canopy observations',f"{subset.tree_canopy_pct.notna().sum()} / {len(subset)}")
c4.metric('Temperature observations',f"{subset.surface_temperature_c.notna().sum()} / {len(subset)}")
if validated is None:
    st.info('**Environmental measurements not yet loaded.** The built-in maps use verified 2021 census demographics only. Download the CSV template below and add sourced environmental observations to activate canopy and heat layers.')
else:
    st.caption('Environmental observation years and sources come from your uploaded file. They may differ from the 2021 census year.')

layer_map={'Residents aged 65+ (%)':'age_65_plus_pct','Low-income prevalence (%)':'lim_at_low_income_pct',**FIELDS}
key=layer_map[layer]
left,right=st.columns([1.8,1],gap='large')
with left:
    st.subheader('Toronto neighbourhood map')
    shown=subset.copy()
    if shown[key].notna().sum()==0:
        st.warning('No verified observations for this layer. Select a demographic layer or upload environmental data.')
    else:
        fig=px.choropleth_mapbox(shown,geojson=geo,locations='neighbourhood_id',featureidkey='id',color=key,
            hover_name='neighbourhood_name',hover_data={'neighbourhood_id':False,key:':.1f'},
            color_continuous_scale='Plasma' if key=='surface_temperature_c' else 'Viridis',
            mapbox_style='carto-darkmatter',center={'lat':43.74,'lon':-79.40},zoom=9.3,opacity=.70,height=530,
            labels={key:layer})
        fig.update_layout(margin={'r':0,'t':0,'l':0,'b':0},paper_bgcolor='#0c1020',font_color='#e9e5fa')
        st.plotly_chart(fig,use_container_width=True)
    st.caption('Neighbourhood-level shading does not show conditions at an individual address. Environmental values are unavailable until uploaded.')
with right:
    st.subheader('Explore the data')
    st.caption('Search and filter the census profile; inspect optional environmental coverage.')
    opts=sorted(subset.neighbourhood_name.tolist())
    selected=st.selectbox('Neighbourhood',opts)
    row=subset.loc[subset.neighbourhood_name==selected].iloc[0]
    st.metric('Age 65+ population share',f"{row.age_65_plus_pct:.1f}%")
    st.metric('Low-income prevalence',f"{row.lim_at_low_income_pct:.1f}%" if pd.notna(row.lim_at_low_income_pct) else 'Not available')
    st.metric('Tree canopy',f"{row.tree_canopy_pct:.1f}%" if pd.notna(row.tree_canopy_pct) else 'Not loaded')
    st.metric('Surface temperature',f"{row.surface_temperature_c:.1f} °C" if pd.notna(row.surface_temperature_c) else 'Not loaded')
    if validated is not None and pd.notna(row.get('source_url')):st.caption(f"Observation: {row.get('observation_year')} · Source: {row.get('source_url')}")

st.divider()
t1,t2,t3=st.tabs(['Compare neighbourhoods','Patterns & coverage','Data & methodology'])
with t1:
    a,b=st.columns(2)
    names=sorted(all_df.neighbourhood_name.tolist())
    aa=a.selectbox('Neighbourhood A',names,index=0)
    bb=b.selectbox('Neighbourhood B',names,index=min(1,len(names)-1))
    comparison=all_df.set_index('neighbourhood_name').loc[[aa,bb],["age_65_plus_pct","lim_at_low_income_pct","tree_canopy_pct","surface_temperature_c"]].T
    comparison.index=['Residents 65+ (%)','Low-income prevalence (%)','Tree canopy (%)','Surface temperature (°C)']
    st.dataframe(comparison,use_container_width=True)
    st.caption('A missing value means no validated observation was provided; it does not mean zero.')
with t2:
    st.subheader('Explore relationships — not causal effects')
    metric=st.selectbox('Y-axis measure',['Low-income prevalence (%)','Tree canopy (%)','Surface temperature (°C)'])
    y={'Low-income prevalence (%)':'lim_at_low_income_pct','Tree canopy (%)':'tree_canopy_pct','Surface temperature (°C)':'surface_temperature_c'}[metric]
    clean=all_df.dropna(subset=['age_65_plus_pct',y])
    if len(clean)<3:st.warning('At least three observed neighbourhoods are needed for this chart. No synthetic environmental measurements are used.')
    else:
        f=px.scatter(clean,x='age_65_plus_pct',y=y,hover_name='neighbourhood_name',color='lim_at_low_income_pct' if y!='lim_at_low_income_pct' else None,
            labels={'age_65_plus_pct':'Residents aged 65+ (%)',y:metric},height=410)
        f.update_layout(paper_bgcolor='#0c1020',plot_bgcolor='#171c32',font_color='#edeaf6')
        st.plotly_chart(f,use_container_width=True)
    st.caption(f'Observed neighbourhoods in selected comparison: {len(clean)} / {len(all_df)}')
with t3:
    st.markdown('**Built-in source:** City of Toronto Neighbourhood Profiles (2021 census), combined with 158-neighbourhood boundaries (2022).')
    st.markdown('**Environmental indicators:** Optional user-provided observations only; not bundled in Build 1.0. Provide their source URL and observation year. Tree canopy must be percentage of area, and surface temperature must be degrees Celsius. Do not mix air temperature with land-surface temperature in one column.')
    st.markdown('**Geographic join:** City neighbourhood short code, not row order or neighbourhood name. No interpolation or modelled filling of gaps.')
    st.markdown('**Important limits:** Surface temperature depends on satellite acquisition conditions and time; canopy measurement methods and years can differ. These ecological indicators do not measure individual exposure, disease, patient risk, or environmental causation. Census percentages refer to 2021.')
    st.markdown('**Sources and reference resources:** [City of Toronto Neighbourhood Profiles](https://open.toronto.ca/dataset/neighbourhood-profiles/) · [Toronto Tree Equity](https://www.toronto.ca/services-payments/water-environment/trees/tree-equity/) · [Toronto neighbourhood geographic data](https://open.toronto.ca/dataset/neighbourhoods/)')
    if validated is not None:
        st.markdown('**Uploaded source inventory:**')
        provenance=all_df.loc[all_df[list(FIELDS.values())].notna().any(axis=1),['observation_year','source_url']].drop_duplicates()
        st.dataframe(provenance,use_container_width=True,hide_index=True)

st.divider()
d1,d2=st.columns(2)
with d1:
    st.download_button('⬇ Download current neighbourhood data',subset.to_csv(index=False).encode('utf-8'),file_name='aqimeryl_environmental_neighbourhoods.csv',mime='text/csv',use_container_width=True)
with d2:
    st.download_button('⬇ Download environmental CSV template',(BASE/'data'/'environmental_data_template.csv').read_bytes(),file_name='environmental_data_template.csv',mime='text/csv',use_container_width=True)
st.caption('AQIMERYL · A research prototype under Nuvanitic · Build 1.0.1 · Exploratory use only · No individual health risk assessment')
