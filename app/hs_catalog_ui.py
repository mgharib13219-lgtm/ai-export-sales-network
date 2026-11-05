"""Admin UI for importing and monitoring the sourced Iranian HS catalogue."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["hs-catalog-admin-ui"])

PAGE = r"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>مدیریت کاتالوگ HS | شبکه تجارت جهانی</title>
<style>
:root{font-family:system-ui,Tahoma,Arial;color:#172b4d;background:#f3f6fa}*{box-sizing:border-box}
body{max-width:1050px;margin:auto;padding:16px}header,section{background:#fff;border:1px solid #e2e8f0;border-radius:15px;padding:18px;margin:12px 0}
h1,h2{margin-top:0}.muted{color:#64748b;font-size:14px;line-height:1.8}
nav,.actions{display:flex;gap:12px;flex-wrap:wrap}nav a{color:#155eef;text-decoration:none;font-weight:600}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:9px}
input,button{font:inherit;width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:9px;margin:4px 0}
button{background:#172b4d;color:white;border:0;cursor:pointer}button.secondary{background:#eef2f7;color:#172b4d;border:1px solid #dbe3ed}
button:disabled{opacity:.5;cursor:not-allowed}.card,.status{border:1px solid #e2e8f0;border-radius:11px;padding:12px;margin:8px 0}
.status{background:#f1f5f9;white-space:pre-wrap}.metric{font-size:25px;font-weight:700}.small{font-size:12px;color:#64748b}
[hidden]{display:none!important}@media(max-width:600px){body{padding:9px}}
</style></head><body>
<header><h1>مدیریت کاتالوگ تعرفه HS ایران</h1>
<p class="muted">ورود کنترل‌شدهٔ فایل تعرفهٔ دارای منبع، نسخه و مجوز استفاده. این ابزار هیچ کد یا تعرفه‌ای را حدس نمی‌زند و دادهٔ نمونه را به‌عنوان تعرفهٔ رسمی منتشر نمی‌کند.</p>
<nav><a href="/">داشبورد</a><a href="/market">جست‌وجوی عمومی تعرفه‌ها</a><a href="/admin/operations">مرکز عملیات مدیر</a></nav></header>
<section><h2>اتصال مدیر</h2><p class="muted">توکن فقط در sessionStorage همین نشست مرورگر ذخیره می‌شود و در صفحه نمایش داده نخواهد شد.</p>
<div class="grid"><input id="token" type="password" autocomplete="off" placeholder="ADMIN_TOKEN"><button id="connect">اتصال</button><button id="disconnect" class="secondary">خروج</button></div>
<p id="message" class="status" aria-live="polite">برای مشاهدهٔ وضعیت، توکن مدیر را وارد کنید.</p></section>
<section id="catalog" hidden><h2>وضعیت دادهٔ تعرفه</h2><div id="metrics" class="grid"></div><p id="sourceInfo" class="muted"></p><button id="refresh" class="secondary">به‌روزرسانی وضعیت</button></section>
<section id="import" hidden><h2>ورود فایل CSV رسمی/مستند</h2>
<p class="muted">ستون‌های قابل قبول: hs_code یا code، description_fa، description_en، parent_code، digits و source. سطوح کد پشتیبانی‌شده ۲، ۴، ۶ و ۸ رقم هستند. کدهای صفرابتدا حفظ می‌شوند. ورود مجدد همان کد را به‌روزرسانی می‌کند.</p>
<div class="grid"><input id="source" maxlength="300" placeholder="منبع دقیق، مثلاً سازمان گمرک جمهوری اسلامی ایران"><input id="version" maxlength="100" placeholder="نسخه / تاریخ انتشار منبع"><input id="file" type="file" accept=".csv,text/csv"></div>
<div class="actions"><button id="importBtn">اعتبارسنجی و ورود فایل</button></div>
<p id="importMessage" class="status" aria-live="polite">فایل فقط پس از فشردن دکمه ارسال می‌شود.</p></section>
<script>
(function(){
"use strict";
const $=id=>document.getElementById(id),token=()=>sessionStorage.getItem("admin_token")||"";
const say=(id,value)=>$(id).textContent=String(value||"");
async function get(path){const headers={"X-Admin-Token":token()};const r=await fetch(path,{headers,cache:"no-store"});let d={};try{d=await r.json();}catch(e){}if(r.status===401){sessionStorage.removeItem("admin_token");throw new Error("توکن مدیر معتبر نیست یا منقضی شده است.");}if(!r.ok)throw new Error(d.detail||("HTTP "+r.status));return d;}
function show(){ $("catalog").hidden=false;$("import").hidden=false; }
async function load(){say("message","در حال بررسی وضعیت کاتالوگ...");try{const d=await get("/trade/hs-catalog?limit=1");const box=$("metrics");box.replaceChildren();const values=[["ردیف فعال واردشده",d.active_catalog_rows],["ردیف نمونه در این پاسخ",(d.items||[]).length]];values.forEach(([label,value])=>{const c=document.createElement("div");c.className="card";const l=document.createElement("div");l.className="small";l.textContent=label;const v=document.createElement("div");v.className="metric";v.textContent=String(value);c.append(l,v);box.append(c);});const item=(d.items||[])[0];$("sourceInfo").textContent=item?"آخرین نمونهٔ قابل مشاهده: "+item.hs_code+" · منبع: "+item.source+" · نسخه: "+(item.source_version||"ثبت نشده"):"هنوز ردیف فعالی وارد نشده است؛ جست‌وجوی عمومی تعرفه‌ها خالی خواهد بود.";show();say("message","اتصال برقرار شد. وضعیت کاتالوگ از API خوانده شد.");}catch(e){$("catalog").hidden=true;$("import").hidden=true;say("message","اتصال انجام نشد: "+e.message);}}
$("connect").addEventListener("click",async()=>{const v=$("token").value.trim();if(v)sessionStorage.setItem("admin_token",v);$("token").value="";if(!token()){say("message","توکن مدیر را وارد کنید.");return;}await load();});
$("disconnect").addEventListener("click",()=>{sessionStorage.removeItem("admin_token");$("catalog").hidden=true;$("import").hidden=true;say("message","از نشست مدیر خارج شدید.");});
$("refresh").addEventListener("click",load);
$("importBtn").addEventListener("click",async()=>{const f=$("file").files[0],source=$("source").value.trim(),version=$("version").value.trim();if(!token()){say("importMessage","ابتدا اتصال مدیر را برقرار کنید.");return;}if(!f||!source){say("importMessage","فایل CSV و نام دقیق منبع الزامی است.");return;}if(f.size>25*1024*1024){say("importMessage","حداکثر حجم فایل ۲۵ مگابایت است.");return;}if(!f.name.toLowerCase().endsWith(".csv")){say("importMessage","فقط فایل CSV پذیرفته می‌شود.");return;}if(!confirm("فایل با منبع و نسخهٔ واردشده به کاتالوگ تعرفه افزوده/به‌روزرسانی شود؟"))return;
 $("importBtn").disabled=true;say("importMessage","در حال ارسال و اعتبارسنجی فایل...");
 try{const params=new URLSearchParams({source,source_version:version});const r=await fetch("/trade/hs-catalog/import-csv?"+params.toString(),{method:"POST",headers:{"X-Admin-Token":token(),"Content-Type":"text/csv; charset=utf-8"},body:await f.text(),cache:"no-store"});let d={};try{d=await r.json();}catch(e){}if(r.status===401){sessionStorage.removeItem("admin_token");throw new Error("توکن مدیر معتبر نیست یا منقضی شده است.");}if(!r.ok)throw new Error(d.detail||("HTTP "+r.status));say("importMessage","ورود موفق: "+d.rows_received+" ردیف پردازش شد. کل ردیف‌های فعال: "+d.active_catalog_rows+" · منبع: "+d.source+" · نسخه: "+(d.source_version||"ثبت نشده")+" · زمان: "+d.imported_at);$("file").value="";await load();
 }catch(e){say("importMessage","ورود ناموفق: "+e.message);}finally{$("importBtn").disabled=false;}
});
if(token())load();
})();
</script></body></html>"""

@router.get("/admin/hs-catalog", response_class=HTMLResponse)
def hs_catalog_admin_page():
    return HTMLResponse(PAGE, headers={
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "X-Frame-Options": "DENY",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "Cache-Control": "no-store",
    })
