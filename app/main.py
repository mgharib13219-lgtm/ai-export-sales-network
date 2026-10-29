from contextlib import asynccontextmanager
import hmac
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from app.workflow import run_opportunity_pipeline
from app.db import init_db, add_opportunity, list_opportunities, list_leads, get_lead, update_lead, due_followups, add_activity, list_activities, crm_stats, LEAD_STAGES, claim_idempotency, complete_idempotency, fail_idempotency, add_audit_event, list_audit_events, create_deal, get_deal, list_deals, update_deal, save_agent_profile, list_agent_profiles, list_due_agent_profiles, get_agent_profile, record_agent_run, list_agent_runs
from app.auth import require_admin
from app.settings import settings
from app.providers import email_provider
from agents.followup import FollowUpAgent
from agents.rfq import RFQAgent
from agents.quote import QuoteAgent
from agents.negotiation import NegotiationAgent
from app.rate_limit import pipeline_limiter
from agents.repeat_deal import RepeatDealEngine

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

class AgentProfileCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    product: Product
    interval_minutes: int = Field(default=1440, ge=60, le=10080)
    enabled: bool = True

class LeadUpdate(BaseModel):
    stage: Optional[str] = None
    next_follow_up: Optional[str] = None
    last_contacted_at: Optional[str] = None

class CounterOffer(BaseModel):
    quote: dict
    counter_unit_price: float = Field(gt=0)
    max_discount_pct: float = Field(default=5.0, ge=0, lt=100)

class DealCreate(BaseModel):
    product_name: str = Field(min_length=2)
    unit: str = ''
    quantity: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=10)
    agreed_unit_price: float = Field(gt=0)
    incoterm: str = Field(min_length=2)
    payment_terms: str = Field(min_length=2)
    factory_share: float = Field(ge=0)
    network_commission: float = Field(ge=0)
    quote_activity_id: Optional[int] = None
    approval_confirmed: bool = False
class RepeatDealCreate(BaseModel):
    product_name: str = Field(min_length=2)
    unit: str = ''
    quantity: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=10)
    agreed_unit_price: float = Field(gt=0)
    incoterm: str = Field(min_length=2)
    payment_terms: str = Field(min_length=2)
    factory_share: float = Field(ge=0)
    network_commission: Optional[float] = Field(default=None, ge=0)
    buyer_company: Optional[str] = None
    country: Optional[str] = None
    approval_confirmed: bool = False

class ActivityCreate(BaseModel):
    kind: str = Field(min_length=2)
    subject: str = ''
    body: str = ''
    status: str = 'draft'

class EmailSendRequest(BaseModel):
    subject: str = Field(min_length=2, max_length=250)
    body: str = Field(min_length=1, max_length=20000)
    approval_confirmed: bool = False

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

@app.get('/system/integrations', dependencies=[Depends(require_admin)])
def integration_status():
    search_configured = settings.search_provider == 'serpapi' and bool(settings.search_api_key)
    ai_mode = (settings.ai_provider or 'none').lower()
    ai_providers = []
    if settings.ai_api_key and ai_mode in ('openai', 'ensemble'):
        ai_providers.append('openai')
    if getattr(settings, 'anthropic_api_key', '') and ai_mode in ('anthropic', 'ensemble'):
        ai_providers.append('anthropic')
    if getattr(settings, 'gemini_api_key', '') and ai_mode in ('gemini', 'ensemble'):
        ai_providers.append('gemini')
    ai_configured = bool(ai_providers)
    email_configured = (settings.email_provider or '').lower() == 'smtp' and all((getattr(settings, 'smtp_host', ''), getattr(settings, 'smtp_user', ''), getattr(settings, 'smtp_password', '')))
    return {
        'status': 'ready' if search_configured and ai_configured else 'action_required',
        'search': {
            'provider': settings.search_provider or 'none',
            'configured': search_configured,
            'status': 'configured' if search_configured else 'provider_not_configured',
            'next_action': None if search_configured else 'Set SEARCH_PROVIDER=serpapi and add SEARCH_API_KEY in the deployment environment.'
        },
        'ai': {
            'provider': ai_mode,
            'configured': ai_configured,
            'active_providers': ai_providers,
            'provider_count': len(ai_providers),
            'status': 'configured' if ai_configured else 'not_configured',
            'next_action': None if ai_configured else 'Add at least one supported AI key. For independent multi-model review, configure AI_API_KEY, ANTHROPIC_API_KEY and/or GEMINI_API_KEY with AI_PROVIDER=ensemble.'
        },
        'email': {
            'provider': settings.email_provider or 'none',
            'configured': bool(email_configured),
            'status': 'configured' if email_configured else 'draft_only',
            'credentials_configured': bool(email_configured),
            'next_action': None if email_configured else 'Set EMAIL_PROVIDER=smtp and configure SMTP_HOST, SMTP_USER and SMTP_PASSWORD. Drafts are not sent until SMTP is configured.'
        },
        'secrets_exposed': False
    }

@app.get('/', response_class=HTMLResponse)
def dashboard():
    return '''<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI Export Sales Network</title><style>body{font-family:system-ui,Arial;max-width:1150px;margin:auto;padding:18px;background:#f5f7fa;color:#17202a}section{background:white;padding:18px;border-radius:16px;margin:12px 0;box-shadow:0 2px 12px #0001}input,textarea,button,select{width:100%;box-sizing:border-box;padding:11px;margin:5px 0;border:1px solid #ddd;border-radius:10px}button{background:#111;color:#fff;cursor:pointer}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}.card{padding:12px;border:1px solid #eee;border-radius:12px;background:#fff}.num{font-size:26px;font-weight:700}.muted{color:#667085}.pill{display:inline-block;padding:4px 8px;border-radius:99px;background:#eef2ff;margin:2px}.row{display:flex;gap:8px;align-items:center}.row>*{flex:1}.small{font-size:12px}</style></head><body><h1>AI Export Sales Network</h1><p class="muted">داشبورد عملیاتی جذب خریدار خارجی — v1.0</p><section><h2>وضعیت اتصال سرویس‌ها</h2><div id="integrations" class="cards">در حال بررسی اتصال‌ها...</div><p class="small muted">کلیدهای API نمایش داده نمی‌شوند.</p></section><section><h2>CRM</h2><div id="stats" class="cards"></div><div class="grid"><select id="stage"><option value="">همه مراحل</option><option>discovered</option><option>verified</option><option>matched</option><option>contacted</option><option>replied</option><option>rfq</option><option>negotiation</option><option>won</option><option>lost</option><option>repeat</option></select><button onclick="loadLeads()">به‌روزرسانی لیدها</button></div><div id="leads">در حال بارگذاری...</div></section><section><h2>افزودن محصول و اجرای شکار خریدار</h2><div class="grid"><input id="name" placeholder="نام محصول"><input id="price" type="number" placeholder="قیمت پایه USD"><input id="hs" placeholder="HS Code"><input id="countries" placeholder="کشورهای هدف: Oman, Turkey"></div><textarea id="desc" placeholder="مشخصات، ظرفیت، MOQ، گواهی‌ها و مزیت محصول"></textarea><button onclick="run()">اجرای Pipeline</button><pre id="out"></pre></section><script>
let tokenPromptPromise=null;
const headers=()=>{const t=sessionStorage.getItem('admin_token');return t?{'X-Admin-Token':t}:{} };
async function api(url,opt={}){
  const originalHeaders={...(opt.headers||{})};
  let token=sessionStorage.getItem('admin_token')||'';
  let r=await fetch(url,{...opt,headers:{...originalHeaders,...(token?{'X-Admin-Token':token}:{})}});
  if(r.status===401){
    sessionStorage.removeItem('admin_token');
    if(!tokenPromptPromise){
      tokenPromptPromise=(async()=>{const entered=prompt('ADMIN_TOKEN را وارد کنید');if(entered){sessionStorage.setItem('admin_token',entered);return entered;}return '';})().finally(()=>{tokenPromptPromise=null;});
    }
    token=await tokenPromptPromise;
    if(token){r=await fetch(url,{...opt,headers:{...originalHeaders,'X-Admin-Token':token}});}
  }
  return r;
}
async function run(){out.textContent='در حال پردازش...';const p={name:name.value,description:desc.value,hs_code:hs.value||null,base_price:price.value?Number(price.value):null,target_countries:countries.value.split(',').map(x=>x.trim()).filter(Boolean)};if(!p.name||p.name.trim().length<2){out.textContent='ابتدا نام محصول را وارد کنید.';return}if(!p.target_countries.length){out.textContent='حداقل یک کشور هدف وارد کنید.';return}const idem=(globalThis.crypto&&crypto.randomUUID)?crypto.randomUUID():('run-'+Date.now()+'-'+Math.random().toString(16).slice(2));try{const r=await api('/opportunities/run',{method:'POST',headers:{'Content-Type':'application/json','X-Idempotency-Key':idem},body:JSON.stringify(p)});const data=await r.json();out.textContent=JSON.stringify(data,null,2);if(r.ok){loadLeads();loadStats()}}catch(e){out.textContent='اجرای فرایند ناموفق بود؛ اتصال را بررسی کنید. '+String(e)}}
async function loadStats(){const r=await api('/crm/stats');if(!r.ok)return;const s=await r.json();stats.innerHTML=`<div class=card><div class=num>${s.total}</div>کل لید</div><div class=card><div class=num>${s.due_followups}</div>پیگیری سررسید</div><div class=card><div class=num>${s.contacted_or_beyond}</div>در مسیر فروش</div><div class=card><div class=small>${Object.entries(s.by_stage).map(([k,v])=>`<span class=pill>${k}: ${v}</span>`).join(' ')||'بدون لید'}</div></div>`}
function esc(v){return String(v??'').replace(/[&<>\"']/g,s=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[s]));}\nasync function loadLeads(){const q=stage.value?`?stage=${encodeURIComponent(stage.value)}`:'';const r=await api('/crm/leads'+q);if(!r.ok){leads.textContent='برای مشاهده CRM توکن لازم است.';return}const a=await r.json();leads.innerHTML=a.map(x=>`<div class=card><b>${esc(x.company_name||'-')}</b> <span class=pill>${esc(x.stage)}</span><br><span class=small>${esc(x.country||'-')} | امتیاز ${esc(x.score||0)} | ${esc(x.email||'بدون ایمیل')}</span><br><span class=small>${esc(x.domain||'')}</span><div class=row><select onchange="changeStage(${x.id},this.value)">${['discovered','verified','matched','contacted','replied','rfq','negotiation','won','lost','repeat'].map(s=>`<option ${s===x.stage?'selected':''}>${s}</option>`).join('')}</select><button onclick="draft(${x.id})">پیش‌نویس پیگیری</button>${x.email?`<button onclick="sendEmail(${x.id})">ارسال ایمیل با تأیید</button>`:'' }</div></div>`).join('')||'لیدی ثبت نشده است'}
async function changeStage(id,s){await api('/crm/leads/'+id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({stage:s})});loadStats()}
async function draft(id){const r=await api('/crm/leads/'+id+'/follow-up',{method:'POST'});alert(JSON.stringify(await r.json(),null,2));loadStats()}
async function sendEmail(id){const subject=prompt('موضوع ایمیل را وارد کنید');if(!subject)return;const body=prompt('متن کامل ایمیل را وارد کنید');if(!body)return;if(!confirm('ایمیل واقعی برای خریدار ثبت‌شده ارسال شود؟ این اقدام پس از تأیید قابل برگشت نیست.'))return;const r=await api('/crm/leads/'+id+'/send-email',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({subject,body,approval_confirmed:true})});const result=await r.json();alert(JSON.stringify(result,null,2));loadLeads()}
async function loadIntegrations(){const box=document.getElementById('integrations');try{const r=await api('/system/integrations');if(!r.ok){box.textContent='برای مشاهده وضعیت اتصال‌ها، توکن مدیر لازم است.';return}const d=await r.json();const items=[['جست‌وجوی خریدار',d.search],['تحلیل هوش مصنوعی',d.ai],['ارسال ایمیل',d.email]];box.innerHTML=items.map(([label,x])=>`<div class=card><b>${esc(label)}</b><br><span class=pill>${x.status==='draft_only'?'ارسال غیرفعال؛ فقط پیش‌نویس':(label==='ارسال ایمیل'?'ارسال SMTP پیکربندی شده':'تنظیم شده')}</span><div class=small>سرویس: ${esc(x.provider)}</div><div class=small>${esc(x.next_action||'تنظیمات ثبت شده است؛ اتصال زنده هنوز جداگانه باید آزموده شود.')}</div></div>`).join('')}catch(e){box.textContent='بررسی اتصال‌ها ناموفق بود.'}}
loadStats();loadLeads();loadIntegrations();
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

@app.get('/agent/profiles', dependencies=[Depends(require_admin)])
def agent_profiles():
    return list_agent_profiles()

@app.post('/agent/profiles', dependencies=[Depends(require_admin)])
def agent_profile_create(data: AgentProfileCreate):
    profile_id = save_agent_profile(data.name, data.product.model_dump(),
                                    data.interval_minutes, enabled=data.enabled)
    add_audit_event('agent.profile_created','admin',str(profile_id),'agent_profile',str(profile_id),
                    {'name':data.name,'enabled':data.enabled,'interval_minutes':data.interval_minutes})
    return get_agent_profile(profile_id)

@app.patch('/agent/profiles/{profile_id}', dependencies=[Depends(require_admin)])
def agent_profile_update(profile_id: int, data: AgentProfileCreate):
    if not get_agent_profile(profile_id):
        raise HTTPException(404, 'agent_profile_not_found')
    save_agent_profile(data.name, data.product.model_dump(), data.interval_minutes,
                       profile_id=profile_id, enabled=data.enabled)
    add_audit_event('agent.profile_updated','admin',str(profile_id),'agent_profile',str(profile_id),
                    {'enabled':data.enabled,'interval_minutes':data.interval_minutes})
    return get_agent_profile(profile_id)


@app.post('/agent/cron/run')
def agent_cron_run(x_agent_cron_token: Optional[str] = Header(default=None)):
    expected = getattr(settings, 'agent_cron_token', '')
    if not expected or not x_agent_cron_token or not hmac.compare_digest(expected, x_agent_cron_token):
        raise HTTPException(401, 'invalid_agent_cron_token')
    return agent_run_cycle()

@app.get('/agent/runs', dependencies=[Depends(require_admin)])
def agent_run_history(limit: int = 50):
    return list_agent_runs(limit)

@app.post('/agent/run-cycle', dependencies=[Depends(require_admin)])
def agent_run_cycle():
    # Explicitly bounded: one request can process at most three enabled profiles.
    profiles = list_due_agent_profiles(limit=3)
    if not profiles:
        return {'status':'idle','processed':0,'message':'No enabled profiles are due for a run.'}
    results = []
    for profile in profiles:
        run_id = None
        try:
            result = run_opportunity_pipeline(profile['product'])
            # The orchestrator persists verified/matched leads itself. Never create
            # placeholder buyers from provider diagnostics or empty search results.
            run_id = record_agent_run(profile['id'],'completed',result)
            add_audit_event('agent.cycle_completed','admin',str(run_id),'agent_profile',
                            str(profile['id']),{'profile_name':profile['name']})
            results.append({'profile_id':profile['id'],'run_id':run_id,'status':'completed',
                            'lead_ids':result.get('lead_ids',[]) if isinstance(result,dict) else []})
        except Exception:
            # Keep provider secrets and raw exception text out of API responses.
            run_id = record_agent_run(profile['id'],'failed',None,'pipeline_error')
            add_audit_event('agent.cycle_failed','admin',str(run_id),'agent_profile',
                            str(profile['id']),{'error_code':'pipeline_error'})
            results.append({'profile_id':profile['id'],'run_id':run_id,'status':'failed',
                            'error_code':'pipeline_error'})
    return {'status':'completed','processed':len(results),'results':results,
            'safety':'Draft/research only; no outbound messages, quotes, contracts, purchases, or payments are sent automatically.'}

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
    if data.stage and current['stage'] == 'negotiation' and data.stage == 'won':
        raise HTTPException(400,'deal_creation_requires_human_approval')
    if data.stage and current['stage'] == 'negotiation' and data.stage not in ('negotiation','lost'):
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

@app.post('/crm/leads/{lead_id}/send-email', dependencies=[Depends(require_admin)])
def crm_send_email(lead_id:int, data:EmailSendRequest):
    lead=get_lead(lead_id)
    if not lead:
        raise HTTPException(404,'lead_not_found')
    if lead.get('stage') in ('won','lost','repeat'):
        raise HTTPException(400,'terminal_stage')
    if not data.approval_confirmed:
        raise HTTPException(400,'human_approval_required')
    recipient=(lead.get('email') or '').strip()
    if '@' not in recipient or recipient.startswith('@') or recipient.endswith('@'):
        raise HTTPException(400,'valid_buyer_email_required')
    result=email_provider.send(recipient, data.subject, data.body)
    activity_id=add_activity(lead_id,'outbound_email',data.subject,
        __import__('json').dumps({'to':recipient,'body':data.body,'result':result},ensure_ascii=False),
        result.get('status','unknown'))
    add_audit_event('email.outbound_attempt','admin',str(lead_id),'lead',str(lead_id),
        {'activity_id':activity_id,'to':recipient,'status':result.get('status'),
         'human_approved':True})
    return {**result,'activity_id':activity_id,'human_approved':True}

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

@app.get('/crm/deals', dependencies=[Depends(require_admin)])
def crm_deals(lead_id: Optional[int]=None, status: Optional[str]=None, limit: int=200):
    return list_deals(lead_id=lead_id, status=status, limit=max(1,min(limit,500)))

@app.get('/crm/deals/{deal_id}', dependencies=[Depends(require_admin)])
def crm_deal(deal_id:int):
    deal=get_deal(deal_id)
    if not deal: raise HTTPException(404,'deal_not_found')
    return deal

@app.post('/crm/leads/{lead_id}/deal', dependencies=[Depends(require_admin)])
def crm_create_deal(lead_id:int, data:DealCreate):
    lead=get_lead(lead_id)
    if not lead: raise HTTPException(404,'lead_not_found')
    if lead.get('stage') != 'negotiation': raise HTTPException(400,'deal_requires_negotiation_stage')
    if not data.approval_confirmed: raise HTTPException(400,'human_approval_required')
    if data.factory_share + data.network_commission > data.agreed_unit_price * data.quantity:
        raise HTTPException(400,'commercial_shares_exceed_deal_value')
    protection_days = max(1, int(settings.repeat_protection_days))
    repeat_until = datetime.now(timezone.utc) + timedelta(days=protection_days)
    deal_id=create_deal({
        'lead_id':lead_id, 'quote_activity_id':data.quote_activity_id,
        'product_name':data.product_name, 'buyer_company':lead.get('company_name') or '',
        'country':lead.get('country'), 'unit':data.unit, 'quantity':data.quantity,
        'currency':data.currency, 'agreed_unit_price':data.agreed_unit_price,
        'incoterm':data.incoterm, 'payment_terms':data.payment_terms,
        'factory_share':data.factory_share, 'network_commission':data.network_commission,
        'status':'won', 'won_reason':'human_approved_commercial_deal', 'repeat_eligible':True,
        'repeat_until':repeat_until.isoformat(), 'repeat_sequence':0,
        'commission_basis':data.network_commission / (data.agreed_unit_price * data.quantity),
        'commission_currency':data.currency
    })
    update_lead(lead_id, stage='won')
    activity_id=add_activity(lead_id,'deal','Deal won',__import__('json').dumps({'deal_id':deal_id},ensure_ascii=False),'approved')
    add_audit_event('deal.won','admin',str(deal_id),'deal',str(deal_id),{'lead_id':lead_id,'activity_id':activity_id,'human_approved':True})
    return {'status':'won','deal_id':deal_id,'lead_id':lead_id,'activity_id':activity_id,'repeat_eligible':True}

@app.post('/crm/deals/{deal_id}/repeat', dependencies=[Depends(require_admin)])
def crm_repeat_deal(deal_id:int, data: Optional[RepeatDealCreate] = None):
    deal=get_deal(deal_id)
    if not deal: raise HTTPException(404,'deal_not_found')
    if deal.get('status') != 'won' or not deal.get('repeat_eligible'): raise HTTPException(400,'repeat_not_eligible')
    if data is None:
        raise HTTPException(400,'human_approval_required')
    if not data.approval_confirmed:
        raise HTTPException(400,'human_approval_required')
    if data.currency.upper() != str(deal.get('currency') or '').upper():
        raise HTTPException(400,'repeat_currency_must_match_source_deal')
    lead=get_lead(deal['lead_id'])
    if not lead: raise HTTPException(404,'lead_not_found')
    engine=RepeatDealEngine(settings.repeat_protection_days)
    policy=engine.evaluate(deal,lead,data.product_name,data.buyer_company,data.country)
    if not policy['protected']:
        raise HTTPException(409, {'error':'repeat_protection_not_active','policy':policy})
    commission=engine.commission(deal,data.quantity,data.agreed_unit_price,data.network_commission)
    total=data.quantity * data.agreed_unit_price
    if data.factory_share + commission['network_commission'] > total:
        raise HTTPException(400,'commercial_shares_exceed_deal_value')
    existing=list_deals(lead_id=deal['lead_id'])
    sequence=max([int(x.get('repeat_sequence') or 0) for x in existing] + [0]) + 1
    new_id=create_deal({
        'lead_id':lead['id'],'product_name':data.product_name,
        'buyer_company':data.buyer_company or lead.get('company_name') or '',
        'country':data.country or lead.get('country'),'unit':data.unit,
        'quantity':data.quantity,'currency':data.currency,
        'agreed_unit_price':data.agreed_unit_price,'incoterm':data.incoterm,
        'payment_terms':data.payment_terms,'factory_share':data.factory_share,
        'network_commission':commission['network_commission'],'status':'won',
        'won_reason':'human_approved_repeat_deal','repeat_eligible':True,
        'repeat_until':deal.get('repeat_until'),'source_deal_id':deal_id,
        'repeat_sequence':sequence,'commission_basis':commission['commission_basis'],
        'commission_currency':commission['commission_currency']
    })
    activity_id=add_activity(lead['id'],'repeat_deal','Repeat deal won',
        __import__('json').dumps({'deal_id':new_id,'source_deal_id':deal_id,'policy':policy,'commission':commission},ensure_ascii=False),'approved')
    add_audit_event('deal.repeat_won','admin',str(new_id),'deal',str(new_id),
                    {'source_deal_id':deal_id,'lead_id':lead['id'],'human_approved':True,
                     'anti_circumvention':True,'commission':commission})
    return {'status':'won','deal_id':new_id,'source_deal_id':deal_id,'lead_id':lead['id'],
            'repeat_sequence':sequence,'repeat_until':deal.get('repeat_until'),
            'anti_circumvention':True,'network_commission':commission['network_commission'],
            'commission_basis':commission['commission_basis'],'activity_id':activity_id}

@app.get('/crm/deals/{deal_id}/repeat-policy', dependencies=[Depends(require_admin)])
def crm_repeat_policy(deal_id:int, product_name:str, buyer_company:Optional[str]=None, country:Optional[str]=None):
    deal=get_deal(deal_id)
    if not deal: raise HTTPException(404,'deal_not_found')
    lead=get_lead(deal['lead_id'])
    if not lead: raise HTTPException(404,'lead_not_found')
    return RepeatDealEngine(settings.repeat_protection_days).evaluate(deal,lead,product_name,buyer_company,country)

@app.post('/crm/leads/{lead_id}/negotiation-review', dependencies=[Depends(require_admin)])
def crm_negotiation_review(lead_id:int, data:CounterOffer):
    lead=get_lead(lead_id)
    if not lead: raise HTTPException(404,'lead_not_found')
    if lead.get('stage') != 'negotiation': raise HTTPException(400,'negotiation_stage_required')
    result=NegotiationAgent().evaluate_counteroffer(data.quote,data.counter_unit_price,data.max_discount_pct)
    activity_id=add_activity(lead_id,'negotiation','Buyer counteroffer review',__import__('json').dumps(result,ensure_ascii=False),'draft')
    result['activity_id']=activity_id
    add_audit_event('negotiation.counteroffer_reviewed','admin',str(lead_id),'lead',str(lead_id),{'activity_id':activity_id,'auto_accept':False})
    return result
