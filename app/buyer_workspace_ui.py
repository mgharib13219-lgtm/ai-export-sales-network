"""Buyer workspace UI for purchase requests and supplier discovery."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["buyer-workspace-ui"])

PAGE = r"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>فضای کاری خریدار | شبکه تجارت جهانی</title>
<style>
:root{font-family:system-ui,Tahoma,Arial;color:#172b4d;background:#f3f6fa}*{box-sizing:border-box}
body{max-width:1100px;margin:auto;padding:16px}header,section{background:#fff;border:1px solid #e2e8f0;border-radius:15px;padding:18px;margin:12px 0}
h1,h2,h3{margin-top:0}.muted,.small{color:#64748b}.muted{font-size:14px;line-height:1.8}
nav,.actions{display:flex;gap:12px;flex-wrap:wrap}nav a{color:#155eef;text-decoration:none;font-weight:600}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:9px}
input,textarea,button{font:inherit;width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:9px;margin:4px 0}
textarea{min-height:115px}button{background:#172b4d;color:white;border:0;cursor:pointer}button.secondary{background:#eef2f7;color:#172b4d;border:1px solid #dbe3ed}
.card{border:1px solid #e2e8f0;border-radius:11px;padding:12px;margin:8px 0}.status{background:#f1f5f9;padding:10px;border-radius:9px;white-space:pre-wrap}
.pill{display:inline-block;background:#eaf0ff;color:#23408e;border-radius:99px;padding:3px 9px;font-size:12px;margin:2px}
.actions button{width:auto;min-width:130px}[hidden]{display:none!important}
@media(max-width:600px){body{padding:9px}.actions button{width:100%}}
</style></head><body>
<header><div class="actions"><button id="langToggle" class="secondary" type="button">English</button></div><h1>فضای کاری خریدار</h1>
<p class="muted">درخواست‌های خرید خود را مدیریت کنید و تأمین‌کنندگان احتمالی را بر اساس مشخصات کالا ببینید. امتیاز تطبیق صرفاً ابزار کشف است؛ هویت، کیفیت، گواهی‌ها و امکان صادرات باید جداگانه بررسی شوند.</p>
<nav><a href="/market">بازار جهانی</a><a href="/trade/workspace">فضای تأمین‌کننده</a></nav></header>
<section id="auth"><h2>ورود به حساب خریدار</h2><p class="muted">ابتدا در بازار جهانی با نقش خریدار وارد شوید.</p><a href="/market">ورود یا ساخت حساب ←</a><p id="authmsg" class="status">در حال بررسی حساب...</p></section>
<section id="create" hidden><h2>ثبت درخواست خرید جدید</h2><div class="grid">
<input id="title" placeholder="نام کالا، مثلاً کشمش طلایی"><input id="category" placeholder="دسته‌بندی دقیق">
<input id="destination" placeholder="کشور مقصد"><input id="quantity" placeholder="مقدار و واحد، مثلاً ۲۰ تن">
</div><textarea id="spec" placeholder="مشخصات فنی، درجه کیفیت، بسته‌بندی، استانداردها، زمان تحویل و شرایط موردنیاز"></textarea>
<label><input id="share" type="checkbox" style="width:auto"> اجازه می‌دهم نام شرکت، کشور و ایمیل کاری فقط در صورت دسترسی مجاز پلن Premium و با رعایت تنظیم رضایت من نمایش داده شود.</label>
<button id="submit">ثبت درخواست خرید</button><p id="createMsg" class="status" aria-live="polite"></p></section>
<section id="requests" hidden><div class="actions"><h2>درخواست‌های من و تأمین‌کنندگان پیشنهادی</h2><button id="refresh" class="secondary">به‌روزرسانی</button></div><div id="requestList"></div></section>
<script>
(function(){
"use strict";
const $=id=>document.getElementById(id),token=()=>sessionStorage.getItem("market_token")||"";
const node=(tag,cls,value)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(value!==undefined)n.textContent=String(value);return n;};
const msg=(id,value)=>$(id).textContent=String(value||"");
const copy={fa:{title:"فضای کاری خریدار",auth:"ورود به حساب خریدار",create:"ثبت درخواست خرید جدید",requests:"درخواست‌های من و تأمین‌کنندگان پیشنهادی",market:"بازار جهانی",supplier:"فضای تأمین‌کننده",login:"ابتدا در بازار جهانی با نقش خریدار وارد شوید.",loginLink:"ورود یا ساخت حساب ←",refresh:"به‌روزرسانی",submit:"ثبت درخواست خرید",product:"نام کالا، مثلاً کشمش طلایی",category:"دسته‌بندی دقیق",destination:"کشور مقصد",quantity:"مقدار و واحد، مثلاً ۲۰ تن",spec:"مشخصات فنی، درجه کیفیت، بسته‌بندی، استانداردها، زمان تحویل و شرایط موردنیاز",share:"اجازه می‌دهم نام شرکت، کشور و ایمیل کاری فقط در صورت دسترسی مجاز پلن Premium و با رعایت تنظیم رضایت من نمایش داده شود."},en:{title:"Buyer workspace",auth:"Buyer sign in",create:"Create a purchase request",requests:"My requests and suggested suppliers",market:"Global marketplace",supplier:"Supplier workspace",login:"Sign in to the global marketplace with a buyer account first.",loginLink:"Sign in or create an account →",refresh:"Refresh",submit:"Submit purchase request",product:"Product name, e.g. golden raisins",category:"Specific category",destination:"Destination country",quantity:"Quantity and unit, e.g. 20 tonnes",spec:"Technical specifications, grade, packaging, standards, delivery date and requirements",share:"I consent to sharing company name, country and business email only where permitted by the Premium plan and my consent settings."}};
function setLanguage(lang){const en=lang==="en",d=en?copy.en:copy.fa;document.documentElement.lang=lang;document.documentElement.dir=en?"ltr":"rtl";$("langToggle").textContent=en?"فارسی":"English";$("langToggle").setAttribute("aria-label",en?"Switch to Persian":"Switch to English");document.querySelector("header h1").textContent=d.title;$("#auth h2").textContent=d.auth;$("#create h2").textContent=d.create;$("#requests h2").textContent=d.requests;const links=document.querySelectorAll("nav a");[d.market,d.supplier].forEach((v,i)=>{if(links[i])links[i].textContent=v;});$("#auth .muted").textContent=d.login;$("#auth a").textContent=d.loginLink;$("#refresh").textContent=d.refresh;$("#submit").textContent=d.submit;$("#title").placeholder=d.product;$("#category").placeholder=d.category;$("#destination").placeholder=d.destination;$("#quantity").placeholder=d.quantity;$("#spec").placeholder=d.spec;$("#share").parentElement.lastChild.textContent=d.share;localStorage.setItem("buyer_workspace_lang",lang);}

async function api(path,options){options=options||{};const headers=Object.assign({},options.headers||{});if(token())headers.Authorization="Bearer "+token();if(options.body)headers["Content-Type"]="application/json";const r=await fetch(path,Object.assign({},options,{headers}));let d={};try{d=await r.json();}catch(e){}if(!r.ok)throw new Error(d.detail||d.error||("HTTP "+r.status));return d;}
function render(items){
 const box=$("requestList");box.replaceChildren();
 if(!items.length){box.append(node("p","muted","هنوز درخواست خریدی ثبت نکرده‌اید."));return;}
 items.forEach(r=>{
  const c=node("article","card");c.append(node("h3","",r.title),node("span","pill",r.status==="open"?"باز":"بسته"),node("p","muted",r.category+" · مقصد: "+r.destination+" · مقدار: "+(r.quantity||"تعیین نشده")),node("p","",r.specification));
  const matches=node("div","");matches.append(node("h3","","تأمین‌کنندگان پیشنهادی ("+r.matches.length+")"));
  if(!r.matches.length)matches.append(node("p","muted","فعلاً محصول منطبق پیدا نشد؛ با تکمیل مشخصات یا بررسی دوباره ممکن است گزینه‌های جدیدی ظاهر شوند."));
  r.matches.forEach(m=>{
   const card=node("div","card");card.append(node("strong","",m.product_name+" · "+m.supplier_company),node("span","pill","امتیاز کشف: "+m.score+"/100"),node("p","muted",m.category+" · مبدأ: "+m.origin+" · کشور تأمین‌کننده: "+m.supplier_country),node("p","",m.description),node("p","muted","ظرفیت: "+(m.capacity||"نامشخص")+" · حداقل سفارش: "+(m.moq||"نامشخص")));
   if(m.reasons.length)card.append(node("p","small","دلایل تطبیق: "+m.reasons.join("؛ ")));
   if(m.information_gaps.length)card.append(node("p","small","اطلاعات ناقص: "+m.information_gaps.join("؛ ")));
   card.append(node("p","small","بررسی‌های ضروری: "+m.mandatory_holds.join("، ")+" · تأیید خودکار: خیر"));matches.append(card);
  });
  c.append(matches);
  if(r.status==="open"){const close=node("button","secondary","بستن درخواست");close.addEventListener("click",async()=>{if(!confirm("این درخواست بسته شود؟"))return;close.disabled=true;try{await api("/marketplace/requests/"+r.id,{method:"DELETE"});await load();}catch(e){close.disabled=false;c.append(node("p","status",e.message));}});c.append(close);}
  box.append(c);
 });
}
async function load(){try{const items=await api("/marketplace/requests/mine");render(items);}catch(e){msg("authmsg","بارگذاری اطلاعات انجام نشد: "+e.message);}}
async function init(){if(!token()){msg("authmsg","ابتدا از بازار جهانی وارد حساب خریدار شوید.");return;}try{const u=await api("/marketplace/me");if(u.role!=="buyer"){msg("authmsg","این صفحه برای حساب خریدار است.");return;}$("auth").hidden=true;$("create").hidden=false;$("requests").hidden=false;await load();}catch(e){msg("authmsg","نشست معتبر نیست؛ دوباره وارد شوید. "+e.message);}}
$("submit").addEventListener("click",async()=>{const p={title:$("title").value.trim(),category:$("category").value.trim(),specification:$("spec").value.trim(),destination:$("destination").value.trim(),quantity:$("quantity").value.trim()||null,share_contact:$("share").checked};if(p.title.length<2||p.category.length<2||p.specification.length<10||p.destination.length<2){msg("createMsg","نام کالا، دسته‌بندی، مشخصات حداقل ۱۰ نویسه و مقصد را کامل کنید.");return;}const b=$("submit");b.disabled=true;try{await api("/marketplace/requests",{method:"POST",body:JSON.stringify(p)});["title","category","spec","destination","quantity"].forEach(id=>$(id).value="");$("share").checked=false;msg("createMsg","درخواست ثبت شد. تأمین‌کنندگان پیشنهادی در پایین صفحه نمایش داده می‌شوند.");await load();}catch(e){msg("createMsg",e.message);}finally{b.disabled=false;}});
$("refresh").addEventListener("click",load);$("langToggle").addEventListener("click",()=>setLanguage(document.documentElement.lang==="fa"?"en":"fa"));setLanguage(localStorage.getItem("buyer_workspace_lang")==="en"?"en":"fa");init();
})();
</script></body></html>"""

@router.get("/buyer/workspace", response_class=HTMLResponse)
def buyer_workspace_page():
    return HTMLResponse(PAGE, headers={
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "X-Frame-Options": "DENY",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
    })
