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

/* Unified responsive navigation and visual polish */
:root{font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Tahoma,Arial,sans-serif;color:#10243e;background:#edf2f8;--brand:#0759a6;--ink:#10243e;--line:#dce5ef;--surface:#fff}
body{max-width:1200px;padding:clamp(10px,2.2vw,26px);line-height:1.65}
header,section{border:1px solid var(--line);border-radius:20px;box-shadow:0 8px 28px rgba(15,42,75,.055);padding:clamp(16px,2.3vw,26px);margin:16px 0}
header{position:relative;background:linear-gradient(145deg,#fff 55%,#f2f8ff)}
h1{font-size:clamp(25px,3vw,36px);letter-spacing:-.5px;color:#0b315c}
h2{font-size:clamp(19px,2.2vw,25px);color:#123c69}
nav{align-items:center;gap:8px;margin:14px 0}
nav a{display:inline-flex;align-items:center;padding:9px 14px;border-radius:12px;background:#eaf3ff;color:#0759a6!important;border:1px solid #d8e9ff;transition:background .18s,transform .18s}
nav a:hover{background:#d9eaff;transform:translateY(-1px)}
.grid{gap:12px}
input,textarea,select{background:#fff;border:1px solid #cbd8e7;border-radius:12px;padding:12px;transition:border-color .18s,box-shadow .18s}
input:focus,textarea:focus,select:focus{border-color:#3984d6;box-shadow:0 0 0 3px #3984d61a;outline:none}
button{border-radius:12px;padding:11px 16px;background:linear-gradient(135deg,#0759a6,#0b76c9);font-weight:700;box-shadow:0 4px 10px #0759a61a;transition:transform .15s,filter .15s}
button:hover{filter:brightness(1.06);transform:translateY(-1px)}button.secondary{background:#edf4fb;color:#17446f;border:1px solid #d5e3f1;box-shadow:none}
.card{border-radius:15px;border-color:#e1eaf3;background:linear-gradient(180deg,#fff,#fbfdff);padding:16px}
.status{border:1px solid #e1eaf3;background:#f4f8fc;border-radius:12px}
#siteMenuToggle{display:none;width:auto;min-width:48px;font-size:22px;line-height:1;padding:10px 13px;margin:10px 0;background:#eaf3ff;color:#0759a6;border:1px solid #d5e7fb;box-shadow:none}
@media(max-width:680px){body{padding:8px}header,section{border-radius:16px;padding:15px;margin:10px 0}#siteMenuToggle{display:inline-flex;align-items:center;justify-content:center}header nav{display:none;flex-direction:column;align-items:stretch;gap:6px;margin:8px 0}header nav.nav-open{display:flex}header nav a{width:100%;padding:12px 14px;font-size:15px}h1{font-size:25px}button{min-height:44px}.grid{grid-template-columns:1fr}}
@media(min-width:681px){header nav{display:flex!important}}

/* Accessibility, page identity and navigation consistency */
html{scroll-behavior:smooth;scroll-padding-top:18px}body{min-height:100vh}body>footer{margin-top:24px}
#skip-to-content{position:absolute;top:-100px;right:12px;z-index:1000;padding:10px 14px;background:#102f52;color:#fff;border-radius:10px}#skip-to-content:focus{top:12px}
header nav a[aria-current=page]{background:#0759a6;color:#fff!important;border-color:#0759a6;box-shadow:0 5px 14px #0759a622}
footer.site-footer{display:grid;grid-template-columns:1.3fr 1fr;gap:18px;padding:20px 22px;margin:18px 0 4px;background:#102f52;color:#e8f2ff;border-radius:18px}
footer.site-footer p{margin:4px 0;color:#c5d8ec;font-size:13px;line-height:1.8}footer.site-footer strong{color:#fff}footer.site-footer nav{display:flex;flex-wrap:wrap;align-content:start;gap:8px;margin:0}footer.site-footer nav a{display:inline-flex;padding:7px 10px;border-radius:9px;background:#ffffff14;color:#e8f2ff;text-decoration:none;font-size:13px}footer.site-footer nav a:hover{background:#ffffff25}
section{scroll-margin-top:16px}section h2{display:flex;align-items:center;gap:9px}section h2:before{content:"";display:inline-block;width:4px;height:22px;border-radius:4px;background:#1684cf}
@media(max-width:680px){footer.site-footer{grid-template-columns:1fr;gap:12px;padding:17px}footer.site-footer nav{flex-direction:column}footer.site-footer nav a{width:100%}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*:before,*:after{transition:none!important;animation:none!important}}
</style></head><body><a id="skip-to-content" href="#main-content">رفتن به محتوای اصلی</a>
<header><div class="actions"><button id="langToggle" class="secondary" type="button">English</button></div><h1>فضای کاری خریدار</h1>
<p class="muted">درخواست‌های خرید خود را مدیریت کنید و تأمین‌کنندگان احتمالی را بر اساس مشخصات کالا ببینید. امتیاز تطبیق صرفاً ابزار کشف است؛ هویت، کیفیت، گواهی‌ها و امکان صادرات باید جداگانه بررسی شوند.</p>
<button id="siteMenuToggle" type="button" aria-label="باز کردن منوی ناوبری" aria-controls="siteMainNav" aria-expanded="false">☰</button><nav id="siteMainNav"><a href="/market">بازار جهانی</a><a href="/buyer/workspace">فضای خریدار</a><a href="/trade/workspace">فضای تأمین‌کننده</a></nav></header>
<main id="main-content"><section id="auth"><h2>ورود به حساب خریدار</h2><p class="muted">ابتدا در بازار جهانی با نقش خریدار وارد شوید.</p><a href="/market">ورود یا ساخت حساب ←</a><p id="authmsg" class="status">در حال بررسی حساب...</p></section>
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
</script><script>
(function(){const b=document.getElementById("siteMenuToggle"),n=document.querySelector("header nav");if(!b||!n)return;b.addEventListener("click",function(){const open=n.classList.toggle("nav-open");b.setAttribute("aria-expanded",String(open));b.textContent=open?"×":"☰";});n.addEventListener("click",function(e){if(e.target.closest("a")&&window.matchMedia("(max-width:680px)").matches){n.classList.remove("nav-open");b.setAttribute("aria-expanded","false");b.textContent="☰";}});})();
</script></main><footer class="site-footer"><div><strong>شبکه تجارت جهانی</strong><p>ابزار کشف فرصت، مدیریت درخواست خرید و معرفی تأمین‌کننده. اطلاعات تجاری و تطبیق‌ها نیازمند بررسی مستقل هستند.</p><p>© شبکه تجارت جهانی</p></div><nav aria-label="پیوندهای پایانی"><a href="/market">بازار جهانی</a><a href="/buyer/workspace">فضای خریدار</a><a href="/trade/workspace">فضای تأمین‌کننده</a><a href="/docs">مستندات</a></nav></footer><script>
(function(){const nav=document.querySelector("header nav");if(!nav)return;const links=nav.querySelectorAll("a[href]");links.forEach(a=>{try{const target=new URL(a.href,location.href);if(target.pathname.replace(/\\/$/,"")===location.pathname.replace(/\\/$/,""))a.setAttribute("aria-current","page");}catch(_){}});document.addEventListener("keydown",e=>{if(e.key==="Escape"&&nav.classList.contains("nav-open")){nav.classList.remove("nav-open");const b=document.getElementById("siteMenuToggle");if(b){b.setAttribute("aria-expanded","false");b.textContent="☰";b.focus();}}});})();
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
