from pathlib import Path
import numpy as np, pandas as pd, plotly.express as px, streamlit as st

st.set_page_config(page_title="Community Sports Facility Booking Optimizer", page_icon="🏟️", layout="wide")
BASE=Path(__file__).parent
DEFAULT=BASE/"data"/"sample_sports_facility_records.csv"
REQ=["facility_id","facility_name","zone","sport","capacity_slots","weekly_demand","waitlist_size","accessibility_score","avg_travel_min","maintenance_days_month","weather_risk_index","booking_cancel_rate_pct","facility_condition_score","booking_reliability_score","maintenance_days_ahead","peak_travel_min","facility_status","bookings_last_month","unique_users_last_month","youth_demand_index","senior_demand_index","adaptive_sport_demand_index","recent_maintenance_events"]

st.markdown("""<style>
.stApp{background:linear-gradient(180deg,#f7fbff,#f8fafc 55%,#f1f7ff);color:#172033}
.block-container{max-width:1500px;padding-top:1.1rem}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#fff,#eef7ff)}
.hero{padding:28px 30px;border:1px solid #d9e6f2;border-radius:24px;background:linear-gradient(135deg,#fff,#edf8ff 60%,#effcf5);box-shadow:0 12px 30px #1e40af10}
.hero h1{margin:8px 0;color:#122033;font-size:2.25rem}.hero p{color:#58697e;font-size:1rem;line-height:1.55}
.badge{display:inline-block;padding:6px 11px;margin-right:6px;border-radius:99px;background:#e9f7ff;color:#0969a6;font-size:.75rem;font-weight:700}
.kpi{background:#fff;border:1px solid #e4eaf1;border-radius:18px;padding:16px;min-height:108px;box-shadow:0 8px 24px #0f172a08}
.kpi b{font-size:1.8rem;color:#142033}.kpi span{display:block;color:#68778a;font-size:.8rem;margin-bottom:5px}
</style>""", unsafe_allow_html=True)

st.markdown("""<div class="hero"><span class="badge">LOCAL-FIRST</span><span class="badge">COMMUNITY SPORT</span><span class="badge">PLANNING SUPPORT</span>
<h1>🏟️ Community Sports Facility Booking Optimizer</h1>
<p>Match limited sports facilities with local demand, accessibility needs, maintenance schedules, weather context and travel burden using locally supplied CSV data. No external APIs are required.</p></div>""",unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Controls")
    up=st.file_uploader("Upload facility CSV",type="csv")
    raw=pd.read_csv(up) if up else pd.read_csv(DEFAULT)
    missing=[c for c in REQ if c not in raw.columns]
    if missing:
        st.error("CSV is missing required columns")
        st.code(", ".join(missing)); st.stop()
    zones=sorted(raw.zone.dropna().unique()); sports=sorted(raw.sport.dropna().unique())
    zs=st.multiselect("Zones",zones,zones); ss=st.multiselect("Sports",sports,sports)
    ceiling=st.slider("Maximum priority score",0,100,100)
    st.divider(); st.caption("All scoring, filtering and charts run locally.")

d=raw.copy()
for c in REQ:
    if c not in ["facility_id","facility_name","zone","sport","facility_status"]: d[c]=pd.to_numeric(d[c],errors="coerce")
d=d[d.zone.isin(zs)&d.sport.isin(ss)].copy()

def score(x):
    demand=np.clip(x.weekly_demand/x.capacity_slots.replace(0,np.nan)*55+x.waitlist_size*1.8,0,100)
    access=np.clip((1-x.accessibility_score)*100,0,100)
    travel=np.clip(x.avg_travel_min*2.2,0,100)
    maint=np.clip(x.maintenance_days_month*7+x.maintenance_days_ahead*1.2,0,100)
    weather=np.clip(x.weather_risk_index*4,0,100)
    condition=np.clip((1-x.facility_condition_score)*100,0,100)
    reliability=np.clip((1-x.booking_reliability_score)*100,0,100)
    cancel=np.clip(x.booking_cancel_rate_pct*2.5,0,100)
    p=demand*.27+access*.13+travel*.12+maint*.10+weather*.08+condition*.10+reliability*.08+cancel*.07+x.adaptive_sport_demand_index*.05
    r=np.clip(x.facility_condition_score*35+x.booking_reliability_score*25+x.accessibility_score*25+(1-x.maintenance_days_month/31).clip(0,1)*15,0,100)
    x["priority_score"]=np.round(np.clip(p,0,100),1); x["readiness_score"]=np.round(r,1)
    x["priority_class"]=pd.cut(x.priority_score,[-1,25,50,75,101],labels=["Low","Moderate","High","Critical"]).astype(str)
    x["capacity_pressure_pct"]=np.round(np.clip(x.weekly_demand/x.capacity_slots*100,0,300),1)
    x["review_flag"]=np.where((x.priority_score>=65)|(x.waitlist_size>=10)|(x.accessibility_score<.75),"Review","Monitor")
    return x

d=score(d); d=d[d.priority_score<=ceiling].copy()
if d.empty: st.warning("No records match the selected filters."); st.stop()

k=st.columns(5)
for col,label,val,note in zip(k,["Facilities","Avg priority","Avg readiness","High + Critical","Waitlist"],
    [len(d),f"{d.priority_score.mean():.1f}/100",f"{d.readiness_score.mean():.1f}/100",int((d.priority_score>=50).sum()),int(d.waitlist_size.sum())],
    ["records in view","booking pressure","operational readiness","additional review","reported demand"]):
    col.markdown(f'<div class="kpi"><span>{label}</span><b>{val}</b><small>{note}</small></div>',unsafe_allow_html=True)

st.subheader("📊 Command Center")
a,b=st.columns([1.35,1])
with a:
    q=d.sort_values("priority_score")
    fig=px.bar(q,x="priority_score",y="facility_name",color="priority_class",orientation="h",text="priority_score",title="Facility priority landscape")
    fig.update_layout(height=470,margin=dict(l=10,r=10,t=55,b=10)); st.plotly_chart(fig,use_container_width=True)
with b:
    cc=d.priority_class.value_counts().reindex(["Low","Moderate","High","Critical"]).fillna(0).reset_index()
    cc.columns=["class","count"]; fig=px.pie(cc,names="class",values="count",hole=.62,title="Priority mix")
    fig.update_layout(height=470,margin=dict(l=10,r=10,t=55,b=10)); st.plotly_chart(fig,use_container_width=True)

st.subheader("🗺️ Zone Intelligence")
z=d.groupby("zone",as_index=False).agg(facilities=("facility_id","count"),priority=("priority_score","mean"),readiness=("readiness_score","mean"),demand=("weekly_demand","sum"),waitlist=("waitlist_size","sum"),travel=("avg_travel_min","mean"))
c1,c2=st.columns(2)
with c1:
    fig=px.scatter(z,x="travel",y="priority",size="demand",color="priority",text="zone",title="Zone pressure vs travel burden",labels={"travel":"Average travel (min)","priority":"Average priority"})
    fig.update_traces(textposition="top center"); fig.update_layout(height=420); st.plotly_chart(fig,use_container_width=True)
with c2:
    fig=px.bar(z.sort_values("waitlist"),x="waitlist",y="zone",orientation="h",color="readiness",title="Zone waitlist concentration",labels={"waitlist":"Total waitlist","zone":""})
    fig.update_layout(height=420); st.plotly_chart(fig,use_container_width=True)

st.subheader("🎯 Demand, Access & Capacity")
c1,c2,c3=st.columns(3)
with c1:
    fig=px.scatter(d,x="capacity_slots",y="weekly_demand",size="waitlist_size",color="priority_score",hover_name="facility_name",title="Demand vs weekly capacity")
    fig.update_layout(height=360); st.plotly_chart(fig,use_container_width=True)
with c2:
    fig=px.bar(d.sort_values("accessibility_score"),x="accessibility_score",y="facility_name",orientation="h",color="accessibility_score",title="Accessibility readiness")
    fig.update_layout(height=360); st.plotly_chart(fig,use_container_width=True)
with c3:
    fig=px.scatter(d,x="avg_travel_min",y="waitlist_size",size="weekly_demand",color="sport",hover_name="facility_name",title="Travel burden vs waitlist")
    fig.update_layout(height=360); st.plotly_chart(fig,use_container_width=True)

st.subheader("🧩 Smart Booking Match")
o1,o2,o3=st.columns(3)
with o1: sport=st.selectbox("Sport",sorted(d.sport.unique()))
with o2: zone=st.selectbox("Target zone",sorted(d.zone.unique()))
with o3: amin=st.slider("Minimum accessibility",.50,1.00,.80,.01)
cand=d[(d.sport==sport)&(d.zone==zone)&(d.accessibility_score>=amin)].copy()
if cand.empty: st.info("No facility matches all selected criteria.")
else:
    cand["match_score"]=np.round(cand.capacity_slots.rank(pct=True)*25+(1-cand.avg_travel_min.rank(pct=True))*20+cand.accessibility_score*20+cand.booking_reliability_score*15+(1-cand.weather_risk_index/25)*10+(1-cand.priority_score/100)*10,1)
    st.dataframe(cand.sort_values("match_score",ascending=False)[["facility_name","zone","sport","capacity_slots","weekly_demand","waitlist_size","accessibility_score","avg_travel_min","priority_score","match_score"]],use_container_width=True,hide_index=True)

st.subheader("🔮 What-if Planning Lab")
s1,s2,s3,s4=st.columns(4)
with s1: cap=st.slider("Capacity boost %",0,50,10,5)
with s2: tr=st.slider("Travel reduction %",0,40,10,5)
with s3: ac=st.slider("Accessibility boost",0,25,5,5)
with s4: mr=st.slider("Maintenance reduction %",0,60,20,5)
sc=d.copy(); sc.capacity_slots*=1+cap/100; sc.avg_travel_min*=1-tr/100; sc.accessibility_score=np.clip(sc.accessibility_score+ac/100,0,1); sc.maintenance_days_month*=1-mr/100; sc=score(sc)
before=d.priority_score.mean(); after=sc.priority_score.mean()
m1,m2,m3=st.columns(3); m1.metric("Current avg priority",f"{before:.1f}"); m2.metric("Scenario avg priority",f"{after:.1f}",f"{after-before:+.1f}"); m3.metric("Priority improvement",f"{max(0,before-after):.1f} pts")
cmp=d[["facility_name","priority_score"]].copy(); cmp["scenario"]=sc.priority_score.values; cmp["change"]=np.round(cmp.scenario-cmp.priority_score,1)
fig=px.bar(cmp.sort_values("change"),x="change",y="facility_name",orientation="h",color="change",title="Before vs scenario priority change"); fig.add_vline(x=0,line_dash="dash"); fig.update_layout(height=420); st.plotly_chart(fig,use_container_width=True)

st.subheader("🚦 Rule-based Planning Alerts")
alerts=[]
for _,r in d.iterrows():
    if r.priority_score>=75: alerts.append(f"🔴 **Critical review:** {r.facility_name} — elevated modeled booking pressure.")
    elif r.priority_score>=50: alerts.append(f"🟠 **High review:** {r.facility_name} — multiple planning-pressure signals.")
    if r.waitlist_size>=10: alerts.append(f"🟡 **Waitlist:** {r.facility_name} — reported waitlist {int(r.waitlist_size)}.")
    if r.accessibility_score<.75: alerts.append(f"🔵 **Access:** {r.facility_name} — accessibility score below screening threshold.")
if alerts:
    for x in alerts[:12]: st.info(x)
else: st.success("No rule-based alerts under the current filters.")

st.subheader("📋 Priority Review Queue")
queue=d.sort_values(["priority_score","waitlist_size"],ascending=[False,False])
show=["facility_id","facility_name","zone","sport","priority_score","priority_class","readiness_score","weekly_demand","capacity_slots","waitlist_size","accessibility_score","avg_travel_min","weather_risk_index","facility_condition_score","booking_reliability_score","review_flag"]
st.dataframe(queue[show],use_container_width=True,hide_index=True)
st.download_button("⬇️ Export filtered priority queue CSV",queue[show].to_csv(index=False).encode(),file_name="sports_facility_priority_queue.csv",mime="text/csv")

with st.expander("🔎 Methodology & data quality"):
    st.write("Priority is an explainable screening score combining demand pressure, accessibility gap, travel burden, maintenance pressure, weather context, facility condition, booking reliability, cancellations and adaptive-sport demand.")
    st.write("This is decision-support, not a guarantee of facility availability, demand, safety, accessibility certification or equitable allocation. Use local policies, facility managers, community input and appropriate field assessment.")

st.caption("100% local processing • CSV in / CSV out • No external APIs required")
