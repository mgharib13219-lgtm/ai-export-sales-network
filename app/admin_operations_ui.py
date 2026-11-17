"""Read-only admin operations workspace for CRM, deals, and audit visibility."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["admin-operations-ui"])

PAGE = r"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>مرکز عملیات مدیر | شبکه تجارت جهانی</title>
<style>
:root{font-family:system-ui,Tahoma,Arial;color:#172b4d;background:#f3f6fa}*{box-sizing:border-box}
body{max-width:1180px;margin:auto;padding:16px}header,section{background:#fff;border:1px solid #e2e8f0;border-radius:15px;padding:18px;margin:12px 0}
h1,h2,h3{margin-top:0}.muted,.small{color:#64748b}.muted{font-size:14px;line-height:1.8}.small{font-size:12px}
nav,.actions{display:flex;gap:12px;flex-wrap:wrap}nav a{color:#155eef;text-decoration:none;font-weight:600}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:9px}
input,button,select{font:inherit;width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:9px;margin:4px 0}
button{background:#172b4d;color:white;border:0;cursor:pointer}button.secondary{background:#eef2f7;color:#172b4d;border:1px solid #dbe3ed}
.card{border:1px solid #e2e8f0;border-radius:11px;padding:12px;margin:8px 0}.status{background:#f1f5f9;padding:10px;border-radius:9px;white-space:pre-wrap}
.pill{display:inline-block;background:#eaf0ff;color:#23408e;border-radius:99px;padding:3px 9px;font-size:12px;margin:2px}
.metric{font-size:25px;font-weight:700}.actions button{width:auto;min-width:130px}[hidden]{display:none!important}
@media(max-width:600px){body{padding:9px}.actions button{width:100%}}
</style></head><body>
<header><h1>مرکز عملیات مدیر</h1>
<p class="muted">نمای یکپارچه CRM، معاملات ثبت‌شده و ردپای رویدادها. این صفحه در این نسخه فقط خواندنی است؛ ارسال پیام، تغییر مرحله معامله یا تأیید تجاری از این داشبورد انجام نمی‌شود.</p>
<nav><a href="/">داشبورد اصلی</a><a href="/market">بازار جهانی</a><a href="/buyer/workspace">پنل خریدار</a><a href="/trade/workspace">پنل تأمین‌کننده</a><a href="/admin/hs-catalog">مدیریت کاتالوگ HS</a></nav></header>
<section><h2>دسترسی مدیر</h2><p class="muted">توکن مدیر فقط در حافظه نشست همین مرورگر نگهداری می‌شود و در رابط کاربری نمایش داده نخواهد شد.</p>
<div class="grid"><input id="token" type="password" autocomplete="off" placeholder="ADMIN_TOKEN"><button id="connect">اتصال امن</button><button id="disconnect" class="secondary">خروج مدیر</button></div>
<p id="message" class="status" aria-live="polite">برای مشاهده اطلاعات، توکن مدیر را وارد کنید.</p></section>
<section id="overview" hidden><div class="actions"><h2>نمای کلی عملیات</h2><button id="refresh" class="secondary">به‌روزرسانی همه بخش‌ها</button></div><div id="stats" class="grid"></div></section>
<section id="deals" hidden><h2>معاملات ثبت‌شده</h2><div id="dealList"></div></section>
<section id="leads" hidden><h2>مسیر فروش و سرنخ‌ها</h2><div id="leadList"></div></section>
<section id="audit" hidden><h2>رویدادهای حسابرسی</h2><div id="auditList"></div></section>
<script>
(function(){
"use strict";
const $=id=>document.getElementById(id),sections=["overview","deals","leads","audit"];
const node=(tag,cls,value)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(value!==undefined)n.textContent=String(value);return n;};
const say=value=>$("message").textContent=String(value||"");
const token=()=>sessionStorage.getItem("admin_token")||"";
async function api(path){const headers={};if(token())headers["X-Admin-Token"]=token();const r=await fetch(path,{headers,cache:"no-store"});let d={};try{d=await r.json();}catch(e){}if(r.status===401){sessionStorage.removeItem("admin_token");throw new Error("توکن مدیر معتبر نیست یا منقضی شده است.");}if(!r.ok)throw new Error(d.detail||("HTTP "+r.status));return d;}
function show(){sections.forEach(id=>$(id).hidden=false);}
function renderStats(s){const box=$("stats");box.replaceChildren();const values=[["کل سرنخ‌ها",s.total],["پیگیری سررسید",s.due_followups],["در مسیر فروش",s.contacted_or_beyond],["مراحل فروش",Object.entries(s.by_stage||{}).map(([k,v])=>k+": "+v).join(" · ")||"بدون داده"]];values.forEach(([label,value])=>{const c=node("div","card");c.append(node("div","small",label),node("div","metric",value));box.append(c);});}
function renderDeals(items){const box=$("dealList");box.replaceChildren();if(!items.length){box.append(node("p","muted","معامله‌ای ثبت نشده است."));return;}items.forEach(d=>{const c=node("article","card");c.append(node("strong","",d.product_name+" · "+d.buyer_company),node("span","pill",d.status),node("p","muted","مقصد: "+(d.country||"نامشخص")+" · مقدار: "+(d.quantity??"—")+" "+(d.unit||"")+" · ارزش واحد: "+(d.agreed_unit_price??"—")+" "+(d.currency||"")),node("p","small","اینکوترمز: "+(d.incoterm||"—")+" · شرایط پرداخت: "+(d.payment_terms||"—")),node("p","small","سهم شبکه: "+(d.network_commission??"—")+" "+(d.currency||"")+" · شناسه سرنخ: "+d.lead_id));box.append(c);});}
function renderLeads(items){const box=$("leadList");box.replaceChildren();if(!items.length){box.append(node("p","muted","سرنخی ثبت نشده است."));return;}items.forEach(x=>{const c=node("article","card");c.append(node("strong","",x.company_name||"شرکت نامشخص"),node("span","pill",x.stage),node("p","muted",(x.country||"کشور نامشخص")+" · امتیاز "+(x.score||0)+" · "+(x.domain||"بدون دامنه")),node("p","small","پیگیری بعدی: "+(x.next_follow_up||"تعیین نشده")+" · آخرین تماس: "+(x.last_contacted_at||"ثبت نشده")));box.append(c);});}
function renderAudit(items){const box=$("auditList");box.replaceChildren();if(!items.length){box.append(node("p","muted","رویدادی برای نمایش وجود ندارد."));return;}items.forEach(x=>{const c=node("article","card");c.append(node("strong","",x.event_type),node("span","pill",x.entity_type||"event"),node("p","small","عامل: "+(x.actor||"نامشخص")+" · شناسه: "+(x.entity_id||"—")+" · زمان: "+(x.created_at||"—")));box.append(c);});}
async function load(){say("در حال دریافت داده‌های مدیریتی...");try{const [s,d,l,a]=await Promise.all([api("/crm/stats"),api("/crm/deals?limit=200"),api("/crm/leads?limit=200"),api("/audit/events?limit=100")]);renderStats(s);renderDeals(d);renderLeads(l);renderAudit(a);show();say("اتصال برقرار است. داده‌ها با دسترسی مدیر بارگذاری شدند.");}catch(e){sections.forEach(id=>$(id).hidden=true);say("بارگذاری انجام نشد: "+e.message);}}
$("connect").addEventListener("click",async()=>{const entered=$("token").value.trim();if(entered)sessionStorage.setItem("admin_token",entered);$("token").value="";if(!token()){say("توکن مدیر را وارد کنید.");return;}await load();});
$("disconnect").addEventListener("click",()=>{sessionStorage.removeItem("admin_token");sections.forEach(id=>$(id).hidden=true);say("از نشست مدیر خارج شدید.");});
$("refresh").addEventListener("click",load);
if(token())load();
})();
</script></body></html>"""

@router.get("/admin/operations", response_class=HTMLResponse)
def admin_operations_page():
    return HTMLResponse(PAGE, headers={
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "X-Frame-Options": "DENY",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "Cache-Control": "no-store",
    })
