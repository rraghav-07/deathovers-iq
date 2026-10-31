"""Launch with: python -m streamlit run app/streamlit_app.py"""
from contextlib import closing
import html, json, sqlite3, sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from model.matchup import MatchupModel, PHASES
st.set_page_config(page_title="DeathOvers IQ", page_icon="D", layout="wide")

st.markdown("""
<style>
:root{--paper:#f7f5ef;--panel:#fffdf8;--ink:#202722;--muted:#68756d;--rule:#d9ded5;--green:#123f32;--green2:#1f6b51;--orange:#c76a2b}
.stApp{background:var(--paper);color:var(--ink)}.block-container{max-width:1480px;padding:2rem 3rem 3rem}
[data-testid="stSidebar"]{background:#17372e;border-right:1px solid #2b5748}[data-testid="stSidebar"] *{color:#eff4ed}[data-testid="stSidebar"] hr{border-color:#416555}
[data-testid="stMetric"]{background:var(--panel);border:1px solid var(--rule);border-radius:3px;padding:14px 16px;box-shadow:none}[data-testid="stMetricLabel"]{color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:.1em}[data-testid="stMetricValue"]{color:var(--green);font-variant-numeric:tabular-nums}
[data-baseweb="select"]>div,[data-baseweb="input"]>div{border-radius:3px;border-color:#aeb9b0;background:var(--panel)}.stButton button,.stDownloadButton button{border-radius:3px;border:1px solid #8c9b90;color:var(--green);background:transparent;font-weight:650}
h1{color:var(--green);letter-spacing:-.035em;font-weight:750;font-size:2.65rem;margin-bottom:.25rem}h2,h3{color:var(--green);letter-spacing:-.02em}.eyebrow{color:var(--orange);font-size:.69rem;letter-spacing:.18em;font-weight:800;text-transform:uppercase}.kicker{color:var(--muted);font-size:.92rem;max-width:800px;line-height:1.55}.section-rule{height:1px;background:var(--rule);margin:1.4rem 0}.data-note{color:var(--muted);font-size:.78rem;line-height:1.5}.callout{border-left:4px solid var(--orange);background:#fbf0e8;padding:14px 16px;color:#4c382b}.callout strong{color:#7e3e17}
.pick{background:var(--green);color:#f4f5ec;border:1px solid #315f4d;border-top:4px solid var(--orange);border-radius:3px;padding:18px;min-height:196px}.pick.secondary{background:#edf1e9;color:var(--ink);border-top-color:#9aac84}.pick-rank{color:#efb486;font-size:.67rem;letter-spacing:.15em;font-weight:800}.pick.secondary .pick-rank{color:#6f8b65}.pick-name{font-size:1.4rem;font-weight:750;margin:10px 0 13px}.pick-stats{font-size:.92rem;line-height:1.75;font-variant-numeric:tabular-nums}.pick-note{font-size:.73rem;opacity:.75;line-height:1.4;margin-top:12px}
.pitch-wrap{min-height:340px;display:flex;align-items:center;justify-content:center;background:#edf0e9;border:1px solid var(--rule);border-radius:4px;overflow:hidden;position:relative}.pitch-scene{width:360px;height:275px;position:relative;perspective:850px}.pitch-3d{position:absolute;inset:16px 28px 24px;transform:rotateX(58deg) rotateZ(-28deg) skewX(-5deg);transform-style:preserve-3d;background:#2e6647;border:2px solid #1d4c37;box-shadow:14px 18px 0 #c8d3c2,21px 25px 0 rgba(33,58,45,.12)}.pitch-3d:before{content:"";position:absolute;inset:14% 18%;background:#c6a878;border:2px solid #9c7c4e}.pitch-3d:after{content:"";position:absolute;left:11%;right:11%;top:48%;height:4%;background:#f5e7c8;box-shadow:0 118px 0 #f5e7c8}.crease{position:absolute;left:18%;right:18%;top:16%;height:3%;border-top:3px solid #fff6dd;border-bottom:3px solid #fff6dd;box-shadow:0 170px 0 #fff6dd,0 177px 0 #fff6dd}.wicket{position:absolute;z-index:3;width:25px;height:28px;border-left:3px solid #f7edce;border-right:3px solid #f7edce;left:47%;top:9%;transform:rotateX(-58deg) rotateZ(28deg);box-shadow:8px 0 0 -1px #f7edce}.wicket.back{top:78%}.ball{position:absolute;z-index:4;width:21px;height:21px;border-radius:50%;background:#bf582f;border:2px solid #873a24;left:64%;top:53%;box-shadow:3px 4px 0 rgba(35,47,34,.2)}.stadium-light{position:absolute;width:88px;height:88px;border-radius:50%;background:rgba(255,248,208,.54);filter:blur(18px);top:18px;left:28px}.pitch-label{position:absolute;left:14px;bottom:10px;color:#64746a;font-size:.68rem;letter-spacing:.12em;text-transform:uppercase}.timeline{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:14px}.phase{border-top:3px solid #b7c4b8;padding:9px 8px 7px;color:#6b766f;font-size:.72rem}.phase.active{border-top-color:var(--orange);color:var(--green);background:#f4ebe4;font-weight:750}.phase small{display:block;font-size:.65rem;font-weight:400;margin-top:4px}@media(prefers-reduced-motion:reduce){.pitch-3d{transform:none}}@media(max-width:900px){.block-container{padding:1.2rem 1rem 2rem}h1{font-size:2.1rem}.pitch-scene{transform:scale(.86)}}
</style>""",unsafe_allow_html=True)
DB=ROOT/'data/deathovers.sqlite'; CONFIG=ROOT/'outputs/model_config.json'; RESULTS=ROOT/'outputs/backtest_results.json'
if not DB.exists() or not CONFIG.exists() or not RESULTS.exists(): st.error('Project data or backtest results are missing.'); st.stop()
@st.cache_resource
def load_model(db_stamp,config_text):
 c=json.loads(config_text); return MatchupModel(DB,c['through_season'],c['k_runs'],c['k_wickets'],c['profile_strength'])
config=json.loads(CONFIG.read_text()); report=json.loads(RESULTS.read_text()); model=load_model(DB.stat().st_mtime_ns,CONFIG.read_text())
@st.cache_data
def phase_profile(role,player_key,cutoff,db_stamp):
 if role not in ('batter','bowler'): raise ValueError('Unknown profile role.')
 field=role+'_key'
 with closing(sqlite3.connect(DB.as_uri()+'?mode=ro',uri=True)) as con:
  return pd.read_sql_query(f'''SELECT p.name AS Phase,p.phase_key,SUM(f.legal_ball) AS Balls,SUM(f.batsman_runs) AS Bat_runs,SUM(f.bowler_runs) AS Conceded,SUM(f.bowler_wicket) AS Wickets,SUM(CASE WHEN f.legal_ball=1 THEN f.batsman_runs ELSE 0 END) AS Legal_runs,SUM(CASE WHEN f.legal_ball=1 THEN f.bowler_wicket ELSE 0 END) AS Legal_wickets FROM fact_deliveries f JOIN dim_match m USING(match_key) JOIN dim_phase p USING(phase_key) WHERE f.{field}=? AND m.season<=? AND f.is_super_over=0 GROUP BY p.phase_key ORDER BY p.phase_key''',con,params=(player_key,cutoff))
def chart(fig,caption,key,height=325):
 fig.update_layout(template='plotly_white',paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font=dict(family='Arial',color='#46554d',size=12),margin=dict(l=8,r=12,t=20,b=8),height=height,legend_title_text='',colorway=['#1f6b51','#c76a2b','#788f62','#9aa7a0'])
 fig.update_xaxes(showgrid=False,linecolor='#cbd3cc'); fig.update_yaxes(gridcolor='#e6e9e3',zeroline=False); st.plotly_chart(fig,width='stretch',key=key); st.caption(caption)
def csv_download(frame,name,key): st.download_button('Download table as CSV',frame.to_csv(index=False).encode('utf-8'),file_name=name,mime='text/csv',key=key)
def player_options(role):
 profiles=model.batters if role=='batter' else model.bowlers; return sorted({model.names_by_key[p] for (p,ph),v in profiles.items() if v.balls>0})
def pitch_component(active):
 items=[('Powerplay','01–06'),('Middle','07–15'),('Death','16–20')]; timeline=''.join(f'<div class="phase {"active" if n==active else ""}" aria-label="{n} phase {"selected" if n==active else "not selected"}">{n}<small>overs {o}</small></div>' for n,o in items)
 st.markdown(f'''<div class="pitch-wrap" role="img" aria-label="Stylised isometric cricket pitch. Visual phase marker only; not a trajectory or field-placement prediction."><div class="stadium-light"></div><div class="pitch-scene"><div class="pitch-3d"><div class="crease"></div><div class="wicket"></div><div class="wicket back"></div><div class="ball"></div></div></div><div class="pitch-label">Static pitch view · no trajectory inference</div></div><div class="timeline" aria-label="Over phase timeline">{timeline}</div>''',unsafe_allow_html=True)
with st.sidebar:
 st.markdown('## DEATHOVERS IQ'); st.caption('IPL matchup workstation'); page=st.radio('Navigate',["Captain’s Cheat Sheet",'Batter Profile','Bowler Profile','Model Validation'],key='page'); st.divider(); st.markdown('**Frozen data context**'); st.caption(f'Dataset: 2008–2024\n\nRecommendation history: through {model.through_season}\n\nFinal test: 2023–2024'); st.caption('Historical decision support only. No live feed, current-form adjustment, squad list or availability check.')
st.markdown('<div class="eyebrow">DEATHOVERS IQ / IPL MATCHUP LAB</div>',unsafe_allow_html=True)

if page=="Captain’s Cheat Sheet":
 st.title('Captain’s Cheat Sheet'); st.markdown('<p class="kicker">Compare selected bowlers against a batter using historical matchup data. Choose a phase and inspect predicted scoring rates, wicket probabilities and sample sizes.</p>',unsafe_allow_html=True); st.markdown('<div class="section-rule"></div>',unsafe_allow_html=True)
 control,pitch=st.columns([1.08,1],gap='large')
 with control:
  st.markdown('**Matchup controls**'); batters=player_options('batter'); batter=st.selectbox('Batter',batters,index=batters.index('V Kohli') if 'V Kohli' in batters else 0,key='captain_batter'); phase=st.selectbox('Match phase',list(PHASES),index=2,key='captain_phase'); options=[p for p in model.available_bowlers(phase) if p!=batter]; defaults=[p for p in ['JJ Bumrah','R Ashwin','RA Jadeja','SP Narine'] if p in options]
  if 'captain_bowlers' in st.session_state:
   previous=st.session_state['captain_bowlers']; filtered=[p for p in previous if p in options]
   if filtered!=previous: st.session_state['captain_bowlers']=filtered
   defaults=None
  bowlers=st.multiselect('Bowlers available to you',options,default=defaults,key='captain_bowlers',help='Choose eligible bowlers yourself. The app does not enforce teams or quotas.'); value=st.slider('Wicket value · assumed runs',0,40,20,1,key='wicket_value',help='Zero ranks by run suppression alone. This assumption is not learned from data.'); st.markdown('<div class="data-note">Score = bat runs per legal ball − assumed wicket value × wicket probability. It is not a match-win probability.</div>',unsafe_allow_html=True)
 with pitch: st.markdown('**Phase marker**'); pitch_component(phase)
 if not bowlers: st.info('Select at least one available bowler to compare estimates.')
 else:
  rows=model.recommend(batter,bowlers,phase,value); st.markdown('<div class="section-rule"></div>',unsafe_allow_html=True); st.subheader('Recommended order'); cols=st.columns(min(3,len(rows)))
  for i,r in enumerate(rows[:3]):
   with cols[i]:
    cls='pick' if i==0 else 'pick secondary'; rank='PRIMARY CALL' if i==0 else f'SECONDARY {i}'; st.markdown(f'''<div class="{cls}"><div class="pick-rank">{rank}</div><div class="pick-name">{html.escape(r['bowler'])}</div><div class="pick-stats"><b>{r['expected_runs_per_legal_ball']:.2f}</b> bat runs / legal ball<br><b>{100*r['wicket_probability_per_legal_ball']:.2f}%</b> wicket probability</div><div class="pick-note">{r['matchup_balls']} direct balls · {r['support']}<br>Direct run weight: {100*r['direct_weight_runs']:.1f}%</div></div>''',unsafe_allow_html=True)
  best=rows[0]; gap=best['fewer_bat_runs_per_six_vs_league']; direction='fewer' if gap>=0 else 'more'; st.info(f'Prefer {best["bowler"]} among your selections under this wicket-value setting. The estimate is {abs(gap):.2f} {direction} bat runs per six legal deliveries than the league phase average. This is a rate comparison, not a single-over forecast.')
  if any(r['profile_fallback'] for r in rows): st.warning('At least one selection lacks a training-phase player profile. Its estimate uses a league fallback.')
  if phase=='Death': st.warning('Death-phase validation is sparse: only 4 common-history groups qualified.')
  st.caption('Support labels describe sample counts; they are not calibrated confidence levels. Extras are not predicted.')
  frame=pd.DataFrame([{'Bowler':r['bowler'],'Bat runs / legal ball':r['expected_runs_per_legal_ball'],'Wicket probability (%)':100*r['wicket_probability_per_legal_ball'],'Score':r['score'],'Direct balls':r['matchup_balls'],'Direct run weight (%)':100*r['direct_weight_runs'],'Direct wicket weight (%)':100*r['direct_weight_wickets'],'Batter phase balls':r['batter_phase_balls'],'Bowler phase balls':r['bowler_phase_balls']} for r in rows])
  st.subheader('Runs versus wickets'); fig=px.scatter(frame,x='Bat runs / legal ball',y='Wicket probability (%)',text='Bowler',size='Bowler phase balls',size_max=34,color='Bowler'); fig.update_traces(textposition='top center',marker_line_width=1,marker_line_color='#fff'); chart(fig,'Left is lower predicted bat-run rate; higher is more wicket potential. Marker size shows bowler phase sample size.','tradeoff'); st.subheader('Comparison table'); st.dataframe(frame.round(3),hide_index=True,width='stretch'); csv_download(frame,'deathovers_shortlist.csv','shortlist_csv')
  with st.expander('Model notes'): st.write('Run and wicket matchup strengths: 60 and 240 prior legal deliveries; player profile strength: 120. Selected on 2022, before testing on 2023–2024.'); st.write('Predicted bat runs per legal delivery differ from official economy: extras and illegal-delivery outcomes are not predicted.'); st.write('A negative score is a ranking value, not negative predicted runs. Historical recommendations are not proven to improve match outcomes.')

elif page in ('Batter Profile','Bowler Profile'):
 role='batter' if page=='Batter Profile' else 'bowler'; st.title(f'{role.title()} Profile'); st.markdown(f'<p class="kicker">Phase scoring, wicket rates and direct matchup records for a historical {role} through {model.through_season}. Sample sizes stay visible beside every rate.</p>',unsafe_allow_html=True); options=player_options(role); default='V Kohli' if role=='batter' else 'JJ Bumrah'; player=st.selectbox(role.title(),options,index=options.index(default) if default in options else 0,key=role+'_profile'); key=model.player_key(player); frame=phase_profile(role,key,model.through_season,DB.stat().st_mtime_ns); frame=frame[frame['Balls']>0].copy()
 if frame.empty: st.info('No legal-delivery profile is available.'); st.stop()
 frame['Bat runs / 100 legal balls']=100*frame['Legal_runs']/frame['Balls']; frame['Bowler-wicket rate (%)']=100*frame['Legal_wickets']/frame['Balls']; frame['Economy']=6*frame['Conceded']/frame['Balls']; a,b,c=st.columns(3); a.metric('Legal deliveries',f'{int(frame.Balls.sum()):,}'); b.metric('Bat runs' if role=='batter' else 'Runs charged',f'{int(frame.Bat_runs.sum() if role=="batter" else frame.Conceded.sum()):,}'); c.metric('Bowler-credited wickets',f'{int(frame.Wickets.sum()):,}'); st.caption('Rates use legal deliveries. For a batter, wickets are opposing bowler-credited wickets; run-outs and retirements are excluded.')
 left,right=st.columns(2)
 with left:
  y='Bat runs / 100 legal balls' if role=='batter' else 'Economy'; chart(px.bar(frame,x='Phase',y=y,color='Phase',text_auto='.1f'),'Higher bars mean faster legal-ball scoring; this is not official strike rate.' if role=='batter' else 'Lower economy means fewer runs charged per six legal balls; unlike the prediction target, this includes wide/no-ball extras.','profile_rate')
 with right: chart(px.bar(frame,x='Phase',y='Bowler-wicket rate (%)',color='Phase',text_auto='.2f'),'Bowler-credited wickets per legal delivery. Excludes run-outs and events on illegal balls.','profile_wickets')
 columns=['Phase','Balls','Bat_runs','Wickets','Bat runs / 100 legal balls','Bowler-wicket rate (%)'];
 if role=='bowler': columns.insert(4,'Economy')
 st.dataframe(frame[columns].round(2),hide_index=True,width='stretch'); st.subheader('Direct matchup records'); phase=st.selectbox('Phase for direct history',list(PHASES),index=2,key='profile_phase'); minimum=st.slider('Minimum direct legal balls',1,60,12,key='profile_minimum'); direct=[]
 for (bat,bowl,ph),v in model.matchups.items():
  if ph!=PHASES[phase] or v.balls<minimum or (bat if role=='batter' else bowl)!=key: continue
  opponent=model.names_by_key[bowl if role=='batter' else bat]; direct.append({'Opponent':opponent,'Direct balls':v.balls,'Bat runs / legal ball':v.runs/v.balls,'Bowler-wicket rate (%)':100*v.wickets/v.balls})
 history=pd.DataFrame(direct)
 if history.empty: st.info('No direct matchups meet this phase and minimum-ball selection. Try a lower threshold or another phase.')
 else:
  history=history.sort_values(['Bat runs / legal ball','Opponent']); first,last=st.columns(2)
  with first: st.markdown('**Lowest historical scoring rates**'); st.dataframe(history.head(5).round(3),hide_index=True,width='stretch')
  with last: st.markdown('**Highest historical scoring rates**'); st.dataframe(history.sort_values('Bat runs / legal ball',ascending=False).head(5).round(3),hide_index=True,width='stretch')
  st.caption('Higher scoring rates favor the batter; lower rates favor the bowler. These are raw historical records, not shrinkage predictions.'); csv_download(history,f'{role}_direct_history.csv','profile_csv')

else:
 st.title('Model Validation'); st.markdown('<p class="kicker">A chronological holdout, shown plainly. Settings were selected on 2022; predictions for 2023–2024 use only history through 2022.</p>',unsafe_allow_html=True); common=report['common_history']; m=common['methods']; ib=100*(m['Bowler']['mae']-m['Shrinkage']['mae'])/m['Bowler']['mae']; ih=100*(m['Raw H2H']['mae']-m['Shrinkage']['mae'])/m['Raw H2H']['mae']; il=100*(m['League']['mae']-m['Shrinkage']['mae'])/m['League']['mae']; a,b,c,d=st.columns(4); a.metric('MAE reduction vs bowler',f'{ib:.2f}%'); b.metric('MAE reduction vs raw H2H',f'{ih:.2f}%'); c.metric('MAE reduction vs league',f'{il:.2f}%'); d.metric('Common-history groups',str(common['groups'])); st.caption('Lower MAE is better. These are error reductions, not percentage accuracy or expected reductions in runs conceded.'); st.markdown('<div class="callout"><strong>Read the boundary:</strong> only 4 death-phase groups qualify for the common-history comparison. That is too sparse for strong death-over-specific claims.</div>',unsafe_allow_html=True)
 mode=st.radio('Comparison population',['Same groups for all four methods','All eligible groups'],horizontal=True,key='validation_population'); selected=common if mode.startswith('Same') else report['all_eligible']; metrics_frame=pd.DataFrame([{'Method':method,'MAE':r['mae'],'Ball-weighted MAE':r['ball_weighted_mae'],'Wicket Brier':r['wicket_brier']} for method,r in selected['methods'].items() if r]); chart(px.bar(metrics_frame,x='Method',y='MAE',color='Method',text_auto='.4f'),f"Lower is better. Every bar uses the same {selected['groups']} test groups in this population.",'validation_mae'); st.dataframe(metrics_frame.round(5),hide_index=True,width='stretch'); st.caption('The bowler baseline predicts bat runs per legal ball, not official economy. Wicket Brier is a probability error score; lower is better, not proof of calibration.')
 if not mode.startswith('Same'): st.info('Raw H2H cannot predict unseen training matchups, so it is excluded from the all-eligible comparison.')
 phase_rows=[]
 for phase_name,result in report['by_phase'].items():
  for method,r in result['methods'].items():
   if r: phase_rows.append({'Phase':phase_name,'Method':method,'MAE':r['mae'],'Groups':result['groups']})
 st.subheader('Performance by phase'); chart(px.bar(pd.DataFrame(phase_rows),x='Phase',y='MAE',color='Method',barmode='group',hover_data=['Groups']),'Powerplay: 48 groups · Middle: 67 · Death: 4. Larger death bars are based on very few observations.','phase_mae'); st.subheader('Protocol and limitations'); st.write('2008–2021: initial training → 2022: validation → refit through 2022 → 2023–2024: final test. Each group is one batter–bowler–phase–season with at least 12 legal test deliveries. The primary comparison also requires at least one direct training ball.')
 with st.expander('Limitations and assumptions',expanded=True): st.markdown('''- One chronological holdout; no statistical significance or calibrated confidence claim.
- Sample-support labels are descriptive counts, not calibrated confidence.
- Extras, illegal-delivery outcomes, pitch, handedness, toss and current form are not modelled.
- Groups with fewer than 12 test balls are excluded; the death-phase subset is particularly small.
- The model beats the league phase baseline by only 0.87% on the common-history comparison.
- Wicket value 20 is an assumption; its ranking benefit and match-win impact are untested.
- Predicted bat runs per legal delivery differ from official economy.
- Profile and wicket strengths reached the predefined grid boundary; the test was not used to expand it.''')
 st.download_button('Download full backtest report',(ROOT/'outputs/BACKTEST_RESULTS.md').read_bytes(),file_name='DeathOvers_IQ_Backtest.md',mime='text/markdown'); st.download_button('Download holdout predictions',(ROOT/'outputs/test_predictions.csv').read_bytes(),file_name='test_predictions.csv',mime='text/csv')
st.markdown('<div class="section-rule"></div>',unsafe_allow_html=True); st.caption('DeathOvers IQ · historical IPL decision support · dataset through 2024 · recommendations use history through 2022 · no live match feed')
