from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from app.workflow import run_opportunity_pipeline
from app.db import init_db, add_opportunity, list_opportunities, list_leads, get_lead, update_lead, due_followups, add_activity, list_activities, crm_stats, LEAD_STAGES, claim_idempotency, complete_idempotency, fail_idempotency, add_audit_event, list_audit_events
from app.auth import require_admin
from app.settings import settings
from agents.followup import FollowUpAgent
from agents.rfq import RFQAgent
from agents.quote import QuoteAgent
from app.rate_limit import pipeline_limiter

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(); yield

app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

class Product(BaseModel):
    name: str = Field(min_length=2)
    description: str = ''
    hs_code: Optional[str] = None
    origin: str = ''
    unit: str = ''
    base_price: Optional[float] = None
    currency: str = 'USD'
    moq: Optional[float] = None
    capacity_per_month: Optional[float] = None
    certificates: List[str] = Field(default_factory=list)
    target_countries: List[str] = Field(default_factory=list)
    shipping: Optional[float] = Field(default=None, ge=0)
    insurance: Optional[float] = Field(default=None, ge=0)
    duties: Optional[float] = Field(default=None, ge=0)
    taxes: Optional[float] = Field(default=None, ge=0)
    payment_fees: Optional[float] = Field(default=None, ge=0)
    inspection: Optional[float] = Field(default=None, ge=0)
    warehousing: Optional[float] = Field(default=None, ge=0)
    financing: Optional[float] = Field(default=None, ge=0)
    returns_or_waste: Optional[float] = Field(default=None, ge=0)

class LeadUpdate(BaseModel):
    stage: Optional[str] = None
    next_follow_up: Optional[str] = None
    last_contacted_at: Optional[str] = None

class ActivityCreate(BaseModel):
    kind: str = Field(min_length=2)
    subject: str = ''
    body: str = ''
    status: str = 'draft'

@app.get('/health')
def health(): return {'status':'ok','service':'ai-export-sales-network','version':settings.app_version,'environment':settings.environment}

@app.get('/ready')
def ready():
    try:
        from app.db import _con, _execute
        con = _con(); _execute(con, 'SELECT 1').fetchone(); con.close()
        return {'status':'ready','database':'ok','version':settings.app_version}
    except Exception as exc:
        raise HTTPException(status_code=503, detail={'status':'not_ready','database':'error','error':str(exc)})

@app.get('/', response_class=HTMLResponse)
def dashboard():
    return '''<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI Export Sales Network</title><style>body{font-family:system-ui,Arial;max-width:1150px;margin:auto;padding:18px;background:#f5f7fa;color:#17202a}section{background:white;padding:18px;border-radius:16px;margin:12px 0;box-shadow:0 2px 12px #0001}input,textarea,button,select{width:100%;box-sizing:border-box;padding:11px;margin:5px 0;border:1px solid #ddd;border-radius:10px}button{background:#111;color:#fff;cursor:pointer}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}.card{padding:12px;border:1px solid #eee;border-radius:12px;background:#fff}.num{font-size:26px;font-weight:700}.muted{color:#667085}.pill{display:inline-block;padding:4px 8px;border-radius:99px;background:#eef2ff;margin:2px}.row{display:flex;gap:8px;align-items:center}.row>*{flex:1}.small{font-size:12px}</style></head><body><h1>AI Export Sales Network</h1><p class="muted">داشبورد عملیاتی جذب خریدار خارجی — v1.0</p><section><h2>CRM</h2><div id="stats" class="cards"></div><div class="grid"><select id="stage"><option value="">همه مراحل</option><option>discovered</option><option>verified</option><option>matched</option><option>contacted</option><option>replied</option><option>rfq</option><option>negotiation</option><option>won</option><option>lost</option><option>repeat</option></select><button onclick="loadLeads()">به‌روزرسانی لیدها</button></div><div id="leads">در حال بارگذاری...</div></section><section><h2>افزودن محصول و اجرای شکار خریدار</h2><div class="grid"><input id="name" placeholder="نام محصول"><input id="price" type="number" placeholder="قیمت پایه USD"><input id="hs" placeholder="HS Code"><input id="countries" placeholder="کشورهای هدف: Oman, Turkey"></div><textarea id="desc" placeholder="مشخصات، ظرفیت، MOQ، گواهی‌ها و مزیت محصول"></textarea><button onclick="run()">اجرای Pipeline</button><pre id="out"></pre></section><script>
const headers=()=>{const t=sessionStorage.getItem('admin_token');return t?{'X-Admin-Token':t}:{} };
async function api(url,opt={}){opt.headers={...(opt.headers||{}),...headers()};let r=await fetch(url,opt);if(r.status===401){const t=prompt('ADMIN_TOKEN را وارد کنید');if(t){sessionStorage.setItem('admin_token',t);opt.headers={'Content-Type':'application/json','X-Admin-Token':t,...(opt.headers||{})};r=await fetch(url,opt)}}return r}
async function run(){out.textContent='در حال پردازش...';const p={name:name.value,description:desc.value,hs_code:hs.value||null,base_price:price.value?Number(price.value):null,target_countries:countries.value.split(',').map(x=>x.trim()).filter(Boolean)};const r=await api('/opportunities/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});out.textContent=JSON.stringify(await r.json(),null,2);loadLeads();loadStats()}
async function loadStats(){const r=await api('/crm/stats');if(!r.ok)return;const s=await r.json();stats.innerHTML=`<div class=card><div class=num>${s.total}</div>کل لید</div><div class=card><div class=num>${s.due_followups}</div>پیگیری سررسید</div><div class=card><div class=num>${s.contacted_or_beyond}</div>در مسیر فروش</div><div class=card><div class=small>${Object.entries(s.by_stage).map(([k,v])=>`<span class=pill>${k}: ${v}</span>`).join(' ')||'بدون لید'}</div></div>`}
function esc(v){return String(v??'').replace(/[&<>\"']/g,s=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[s]));}\nasync function loadLeads(){const q=stage.value?`?stage=${encodeURIComponent(stage.value)}`:'';const r=await api('/crm/leads'+q);if(!r.ok){leads.textContent='برای مشاهده CRM توکن لازم است.';return}const a=await r.json();leads.innerHTML=a.map(x=>`<div class=card><b>${esc(x.company_name||'-')}</b> <span class=pill>${esc(x.stage)}</span><br><span class=small>${esc(x.country||'-')} | امتیاز ${esc(x.score||0)} | ${esc(x.email||'بدون ایمیل')}</span><br><span class=small>${esc(x.domain||'')}</span><div class=row><select onchange="changeStage(${x.id},this.value)">${['discovered','verified','matched','contacted','replied','rfq','negotiation','won','lost','repeat'].map(s=>`<option ${s===x.stage?'selected':''}>${s}</option>`).join('')}</select><button onclick="draft(${x.id})">پیش‌نویس پیگیری</button></div></div>`).join('')||'لیدی ثبت نشده است'}
async function changeStage(id,s){await api('/crm/leads/'+id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({stage:s})});loadStats()}
async function draft(id){const r=await api('/crm/leads/'+id+'/follow-up',{method:'POST'});alert(JSON.stringify(await r.json(),null,2));loadStats()}
loadStats();loadLeads();
</script></body></html>'''

@app.post('/opportunities/run', dependencies=[Depends(require_admin)])
def run(product: Product, request: Request, x_idempotency_key: Optional[str] = Header(default=None)):
    client_key = request.client.host if request.client else 'unknown'
    if not pipeline_limiter.allow(client_key):
        raise HTTPException(429, 'rate_limit_exceeded')
    if not x_idempotency_key:
        raise HTTPException(400, 'X-Idempotency-Key is required')
    try:
        claim = claim_idempotency(x_idempotency_key)
    except ValueError:
        raise HTTPException(400, 'invalid_idempotency_key')
    if not claim['claimed']:
        if claim['status'] == 'completed':
            return claim['payload']
        raise HTTPException(409, 'request_already_in_progress')
    request_id = x_idempotency_key
    try:
        result=run_opportunity_pipeline(product.model_dump())
        opps=result.get('opportunities') if isinstance(result,dict) else None
        if opps:
            for o in opps: add_opportunity({'product_name':product.name,**o})
        else:
            first=(product.target_countries or [''])[0]
            add_opportunity({'product_name':product.name,'country':first,'buyer':'pending provider connection','score':0,'payload':result})
        add_audit_event('pipeline.completed','admin',request_id,'product',product.name,
                        {'target_countries':product.target_countries,'lead_ids':result.get('lead_ids',[])})
        complete_idempotency(x_idempotency_key,result)
        return result
    except Exception as exc:
        payload={'status':'error','request_id':request_id,'error':str(exc)}
        try:
            fail_idempotency(x_idempotency_key,payload)
            add_audit_event('pipeline.failed','admin',request_id,'product',product.name,{'error':str(exc)})
        finally:
            raise

@app.get('/opportunities', dependencies=[Depends(require_admin)])
def opportunities(): return list_opportunities()

@app.get('/audit/events', dependencies=[Depends(require_admin)])
def audit_events(limit:int=100): return list_audit_events(limit)

@app.get('/crm/stats', dependencies=[Depends(require_admin)])
def crm_stats_api(): return crm_stats()

@app.get('/crm/leads', dependencies=[Depends(require_admin)])
def crm_leads(stage: Optional[str]=None, limit:int=200):
    if stage and stage not in LEAD_STAGES: raise HTTPException(400,'invalid_stage')
    return list_leads(stage=stage,limit=max(1,min(limit,500)))

@app.get('/crm/leads/{lead_id}', dependencies=[Depends(require_admin)])
def crm_lead(lead_id:int):
    lead=get_lead(lead_id)
    if not lead: raise HTTPException(404,'lead_not_found')
    lead['activities']=list_activities(lead_id)
    return lead

@app.patch('/crm/leads/{lead_id}', dependencies=[Depends(require_admin)])
def crm_update_lead(lead_id:int, data:LeadUpdate):
    if data.stage and data.stage not in LEAD_STAGES: raise HTTPException(400,'invalid_stage')
    current=get_lead(lead_id)
    if not current: raise HTTPException(404,'lead_not_found')
    if data.stage and current['stage'] in ('won','lost','repeat') and data.stage != current['stage']:
        raise HTTPException(400,'terminal_stage_locked')
    allowed = {('rfq','negotiation'), ('negotiation','won'), ('negotiation','lost'), ('won','repeat')}
    if data.stage and current['stage'] not in ('discovered','verified','matched','contacted','replied','rfq','negotiation','won','lost','repeat'):
        raise HTTPException(400,'invalid_current_stage')
    if data.stage and current['stage'] == 'rfq' and data.stage not in ('rfq','negotiation'):
        raise HTTPException(400,'invalid_deal_transition')
    if data.stage and current['stage'] == 'negotiation' and data.stage not in ('negotiation','won','lost'):
        raise HTTPException(400,'invalid_deal_transition')
    if data.stage and current['stage'] == 'won' and data.stage != 'repeat':
        raise HTTPException(400,'invalid_deal_transition')
    if not update_lead(lead_id,stage=data.stage,next_follow_up=data.next_follow_up,last_contacted_at=data.last_contacted_at): raise HTTPException(404,'lead_not_found')
    if data.stage:
        add_audit_event('crm.stage_changed','admin',str(lead_id),'lead',str(lead_id),
                        {'from_stage':current['stage'],'to_stage':data.stage})
    return {'status':'ok','lead_id':lead_id}

@app.get('/crm/followups/due', dependencies=[Depends(require_admin)])
def crm_due_followups(limit:int=100): return due_followups(max(1,min(limit,300)))

@app.post('/crm/followups/process', dependencies=[Depends(require_admin)])
def crm_process_followups(limit:int=50):
    due=due_followups(max(1,min(limit,100)))
    results=[]
    agent=FollowUpAgent()
    for lead in due:
        results.append({'lead_id':lead['id'], **agent.create_draft(lead)})
    return {'processed':len(results),'results':results,'mode':'draft_only'}

@app.post('/crm/leads/{lead_id}/follow-up', dependencies=[Depends(require_admin)])
def crm_followup(lead_id:int):
    lead=get_lead(lead_id)
    if not lead: raise HTTPException(404,'lead_not_found')
    if lead.get('stage') in ('won','lost','repeat'): raise HTTPException(400,'terminal_stage')
    return FollowUpAgent().create_draft(lead)

@app.post('/crm/leads/{lead_id}/rfq-draft', dependencies=[Depends(require_admin)])
def crm_rfq_draft(lead_id:int, product: Product):
    lead=get_lead(lead_id)
    if not lead:
        raise HTTPException(404,'lead_not_found')
    if lead.get('stage') in ('won','lost','repeat'):
        raise HTTPException(400,'terminal_stage')
    result=RFQAgent().create_draft(product.model_dump(), lead)
    if result.get('status') == 'draft_only':
        add_audit_event('rfq.draft_created','admin',str(lead_id),'lead',str(lead_id),
                        {'product':product.name,'activity_id':result.get('activity_id')})
    return result

@app.post('/crm/leads/{lead_id}/quote-draft', dependencies=[Depends(require_admin)])
def crm_quote_draft(lead_id:int, product: Product, target_margin_pct: float = 10.0,
                    incoterm: str = 'TBD', payment_terms: str = 'TBD', validity_days: int = 7):
    lead=get_lead(lead_id)
    if not lead:
        raise HTTPException(404,'lead_not_found')
    if lead.get('stage') in ('won','lost','repeat'):
        raise HTTPException(400,'terminal_stage')
    result=QuoteAgent().create_draft(
        product.model_dump(), lead,
        target_margin_pct=target_margin_pct,
        incoterm=incoterm,
        payment_terms=payment_terms,
        validity_days=validity_days,
    )
    if result.get('status') == 'draft_only':
        activity_id=add_activity(
            lead_id, 'quote', 'Commercial quote draft',
            __import__('json').dumps(result, ensure_ascii=False), 'draft'
        )
        result['activity_id']=activity_id
        add_audit_event('quote.draft_created','admin',str(lead_id),'lead',str(lead_id),
                        {'product':product.name,'activity_id':activity_id})
    return result

@app.post('/crm/leads/{lead_id}/activity', dependencies=[Depends(require_admin)])
def crm_activity(lead_id:int, data:ActivityCreate):
    if not get_lead(lead_id): raise HTTPException(404,'lead_not_found')
    return {'activity_id':add_activity(lead_id,data.kind,data.subject,data.body,data.status)}
