"""Supplier inventory and export price-list page."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["trade-workspace-ui"])

PAGE = r"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>فضای کاری تجارت | شبکه تجارت جهانی</title>
<style>
:root{font-family:system-ui,Tahoma,Arial;color:#172b4d;background:#f3f6fa}*{box-sizing:border-box}
body{max-width:1100px;margin:auto;padding:16px}header,section{background:#fff;border:1px solid #e2e8f0;border-radius:15px;padding:18px;margin:12px 0}
h1,h2,h3{margin-top:0}.muted,.small{color:#64748b}.muted{font-size:14px;line-height:1.8}.small{font-size:12px}
nav,.actions{display:flex;gap:12px;flex-wrap:wrap}nav a{color:#155eef;text-decoration:none;font-weight:600}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:9px}
input,select,button{font:inherit;width:100%;padding:10px;border:1px solid #cbd5e1;border-radius:9px;margin:4px 0}
button{background:#172b4d;color:white;border:0;cursor:pointer}button.secondary{background:#eef2f7;color:#172b4d;border:1px solid #dbe3ed}
button:disabled{opacity:.5}.card{border:1px solid #e2e8f0;border-radius:11px;padding:12px;margin:8px 0}
.status{background:#f1f5f9;padding:10px;border-radius:9px;white-space:pre-wrap}.pill{display:inline-block;background:#eaf0ff;color:#23408e;border-radius:99px;padding:3px 9px;font-size:12px;margin:2px}
.row{display:flex;gap:8px;align-items:center}.row>*{flex:1}.actions button{width:auto;min-width:125px}[hidden]{display:none!important}
@media(max-width:600px){body{padding:9px}.row{display:block}.actions button{width:100%}}
</style></head><body>
<header><h1>فضای کاری تأمین‌کننده</h1>
<p class="muted">مدیریت موجودی انبار و لیست قیمت صادراتی در یک صفحه. اطلاعات کالا و موجودی توسط شرکت شما ثبت می‌شود و به‌تنهایی گواهی بازرسی یا تأیید مستقل موجودی نیست.</p>
<nav><a href="/">داشبورد</a><a href="/market">بازار جهانی</a><a href="/docs">مستندات API</a></nav></header>
<section id="auth"><h2>ورود به فضای کاری</h2><p class="muted">برای ادامه، از حساب تأمین‌کننده در بازار جهانی وارد شوید.</p><a href="/market">ورود یا ساخت حساب ←</a><p id="authmsg" class="status">در حال بررسی حساب...</p></section>
<section id="overview" hidden><div class="row"><div><h2>نمای کلی موجودی</h2><p class="muted">مقدار رزروشده از مقدار قابل عرضه کسر می‌شود.</p></div><button id="refresh" class="secondary">به‌روزرسانی</button></div><div id="stats" class="grid"></div></section>
<section id="inventory" hidden><h2>ثبت موجودی انبار</h2><p class="muted">قالب‌ها صرفاً تعریف نمونه کالا هستند و ادعایی درباره موجودی واقعی ایجاد نمی‌کنند.</p>
<div class="grid"><select id="template"><option value="">قالب نمونه (اختیاری)</option></select><input id="sku" placeholder="شناسه کالا / SKU"><input id="product" placeholder="نام دقیق محصول"><input id="country" placeholder="کشور محل انبار"><input id="qty" type="number" min="0" step="0.01" placeholder="مقدار"><input id="unit" placeholder="واحد، مانند kg یا ton"></div>
<button id="saveStock">ثبت موجودی</button><p id="stockmsg" class="status" aria-live="polite"></p><h3>موجودی‌های ثبت‌شده</h3><div id="stockList"></div></section>
<section id="pricing" hidden><h2>لیست قیمت صادراتی</h2><p class="muted">برای هر بازار یا دوره زمانی لیست جداگانه بسازید. قیمت نهایی معامله به حجم، مقصد، اینکوترمز، حمل و پرداخت وابسته است.</p>
<div class="grid"><input id="listName" placeholder="نام لیست، مثلاً قیمت صادراتی آلمان"><input id="currency" value="USD" maxlength="10" placeholder="ارز"><input id="from" type="date" aria-label="شروع اعتبار"><input id="until" type="date" aria-label="پایان اعتبار"></div>
<button id="newList">ایجاد پیش‌نویس لیست قیمت</button><p id="listmsg" class="status" aria-live="polite"></p>
<div id="itemEditor" hidden><h3>افزودن قلم به <span id="selectedList" class="pill"></span></h3>
<div class="grid"><input id="itemName" placeholder="نام محصول"><input id="itemUnit" placeholder="واحد"><input id="unitPrice" type="number" min="0.0001" step="0.0001" placeholder="قیمت واحد"><input id="moq" type="number" min="0.0001" step="0.01" value="1" placeholder="حداقل سفارش"><select id="incoterm"><option value="">اینکوترمز اختیاری</option><option>EXW</option><option>FCA</option><option>FOB</option><option>CFR</option><option>CIF</option><option>CPT</option><option>CIP</option><option>DAP</option><option>DPU</option><option>DDP</option></select><input id="destination" placeholder="کشور مقصد (اختیاری)"></div>
<div class="actions"><button id="addItem">افزودن قلم</button><button id="cancelSelect" class="secondary">لغو انتخاب</button></div><p id="itemmsg" class="status"></p></div>
<h3>لیست‌های قیمت شما</h3><div id="lists"></div></section>
<script>
(function(){
"use strict";
const $=id=>document.getElementById(id),token=()=>sessionStorage.getItem("market_token")||"";
let user=null,stock=[],lists=[],selected=null;
const msg=(id,s)=>$(id).textContent=String(s||"");
const node=(tag,cls,s)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(s!==undefined)n.textContent=String(s);return n;};
const btn=(s,cls,fn)=>{const b=node("button",cls,s);b.type="button";b.addEventListener("click",fn);return b;};
async function api(path,opt){
 opt=opt||{};const headers=Object.assign({},opt.headers||{});if(token())headers.Authorization="Bearer "+token();if(opt.body)headers["Content-Type"]="application/json";
 const r=await fetch(path,Object.assign({},opt,{headers}));let d={};try{d=await r.json();}catch(e){}if(!r.ok)throw new Error(d.detail||d.error||("HTTP "+r.status));return d;
}
function explain(e){const map={sku_already_exists_or_inventory_conflict:"این SKU قبلاً ثبت شده است.",inventory_item_not_found_or_quantity_below_reserved:"موجودی پیدا نشد یا مقدار جدید از مقدار رزروشده کمتر است.",draft_price_list_not_found:"پیش‌نویس پیدا نشد.",price_list_requires_at_least_one_item:"برای انتشار، ابتدا یک قلم اضافه کنید.",valid_until_before_valid_from:"تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد."};return map[e.message]||e.message;}
function renderStock(){
 const box=$("stockList");box.replaceChildren();
 if(!stock.length)box.append(node("p","muted","موجودی فعالی ثبت نشده است."));
 let total=0,reserved=0;
 stock.forEach(x=>{total+=Number(x.quantity);reserved+=Number(x.reserved_quantity);const c=node("article","card");c.append(node("strong","",x.product_name),node("span","pill","SKU: "+x.sku),node("p","muted","انبار: "+x.warehouse_country+" · مقدار: "+x.quantity+" "+x.unit+" · رزروشده: "+x.reserved_quantity+" · قابل عرضه: "+Math.max(0,Number(x.quantity)-Number(x.reserved_quantity))));
 const row=node("div","row"),v=node("input","");v.type="number";v.min=String(x.reserved_quantity||0);v.step="0.01";v.value=String(x.quantity);v.setAttribute("aria-label","مقدار جدید");
 row.append(v,btn("ذخیره مقدار","secondary",async()=>{try{await api("/trade/inventory/"+x.id+"/quantity",{method:"PATCH",body:JSON.stringify({quantity:Number(v.value)})});msg("stockmsg","موجودی به‌روزرسانی شد.");await loadStock();}catch(e){msg("stockmsg",explain(e));}}));c.append(row);box.append(c);});
 const cards=[["قلم فعال",stock.length],["مجموع مقدار",total.toLocaleString("en-US")],["رزروشده",reserved.toLocaleString("en-US")],["قابل عرضه",Math.max(0,total-reserved).toLocaleString("en-US")]];
 $("stats").replaceChildren();cards.forEach(x=>{const c=node("div","card");c.append(node("div","small",x[0]),node("strong","",x[1]));$("stats").append(c);});
}
async function loadStock(){stock=await api("/trade/inventory?status=active&limit=100");renderStock();}
function renderLists(){
 const box=$("lists");box.replaceChildren();if(!lists.length)box.append(node("p","muted","هنوز لیست قیمتی ندارید."));
 lists.forEach(x=>{const c=node("article","card");c.append(node("strong","",x.name),node("span","pill",x.status==="published"?"منتشرشده":"پیش‌نویس"),node("p","muted","ارز: "+x.currency+" · اعتبار: "+(x.valid_from||"بدون شروع")+" تا "+(x.valid_until||"بدون پایان")));
 (x.items||[]).forEach(i=>c.append(node("p","",i.product_name+" · "+i.unit_price+" "+x.currency+"/"+i.unit+" · MOQ "+i.minimum_quantity+" · "+(i.incoterm||"Incoterm نامشخص")+" · "+(i.destination_country||"بدون مقصد"))));
 if(x.status==="draft"){const a=node("div","actions");a.append(btn("افزودن قلم","secondary",()=>selectList(x)),btn("انتشار لیست", "",async()=>{if(!(x.items||[]).length){msg("listmsg","ابتدا حداقل یک قلم اضافه کنید.");return;}if(!confirm("لیست قیمت منتشر شود؟"))return;try{await api("/trade/price-lists/"+x.id+"/publish",{method:"POST"});msg("listmsg","لیست قیمت منتشر شد.");await loadLists();}catch(e){msg("listmsg",explain(e));}}));c.append(a);}box.append(c);});
}
function selectList(x){selected=x.id;$("itemEditor").hidden=false;$("selectedList").textContent=x.name;msg("itemmsg","قلم جدید به این پیش‌نویس افزوده می‌شود.");}
function clearList(){selected=null;$("itemEditor").hidden=true;}
async function loadLists(){lists=await api("/trade/price-lists");renderLists();if(selected&&!lists.some(x=>x.id===selected&&x.status==="draft"))clearList();}
async function initialize(){
 if(!token()){msg("authmsg","ابتدا در بازار جهانی وارد حساب تأمین‌کننده شوید.");return;}
 try{user=await api("/marketplace/me");if(user.role!=="producer"){msg("authmsg","این صفحه برای حساب تولیدکننده یا تأمین‌کننده است.");return;}
 $("auth").hidden=true;["overview","inventory","pricing"].forEach(id=>$(id).hidden=false);
 const templates=await api("/trade/catalog/templates");templates.forEach(x=>{const o=node("option","",x.name_fa+" · "+x.sku_template);o.value=x.sku_template;o.dataset.name=x.name_fa||x.name;o.dataset.unit=x.unit||"";$("template").append(o);});
 await Promise.all([loadStock(),loadLists()]);
 }catch(e){msg("authmsg","ورود معتبر نیست؛ دوباره از بازار جهانی وارد شوید. "+explain(e));}
}
$("template").addEventListener("change",()=>{const o=$("template").selectedOptions[0];if(o&&o.value){$("sku").value=o.value;$("product").value=o.dataset.name;$("unit").value=o.dataset.unit;}});
$("saveStock").addEventListener("click",async()=>{const p={sku:$("sku").value.trim(),product_name:$("product").value.trim(),warehouse_country:$("country").value.trim(),quantity:Number($("qty").value),unit:$("unit").value.trim()};if(!p.sku||!p.product_name||!p.warehouse_country||!p.unit||$("qty").value===""){msg("stockmsg","تمام فیلدهای موجودی را تکمیل کنید.");return;}try{await api("/trade/inventory",{method:"POST",body:JSON.stringify(p)});msg("stockmsg","موجودی ثبت شد.");["sku","product","country","qty","unit"].forEach(id=>$(id).value="");$("template").value="";await loadStock();}catch(e){msg("stockmsg",explain(e));}});
$("newList").addEventListener("click",async()=>{const p={name:$("listName").value.trim(),currency:$("currency").value.trim().toUpperCase(),valid_from:$("from").value||null,valid_until:$("until").value||null};if(p.name.length<2||p.currency.length<3){msg("listmsg","نام لیست و ارز معتبر را وارد کنید.");return;}try{const r=await api("/trade/price-lists",{method:"POST",body:JSON.stringify(p)});$("listName").value="";await loadLists();const x=lists.find(y=>y.id===r.price_list_id);if(x)selectList(x);msg("listmsg","پیش‌نویس ساخته شد؛ اقلام قیمت را اضافه کنید.");}catch(e){msg("listmsg",explain(e));}});
$("addItem").addEventListener("click",async()=>{if(!selected)return;const p={product_name:$("itemName").value.trim(),unit:$("itemUnit").value.trim(),unit_price:Number($("unitPrice").value),minimum_quantity:Number($("moq").value),incoterm:$("incoterm").value||null,destination_country:$("destination").value.trim()||null};if(p.product_name.length<2||!p.unit||!Number.isFinite(p.unit_price)||p.unit_price<=0||!Number.isFinite(p.minimum_quantity)||p.minimum_quantity<=0){msg("itemmsg","نام، واحد، قیمت مثبت و حداقل سفارش معتبر لازم است.");return;}try{await api("/trade/price-lists/"+selected+"/items",{method:"POST",body:JSON.stringify(p)});["itemName","itemUnit","unitPrice","destination"].forEach(id=>$(id).value="");$("moq").value="1";$("incoterm").value="";msg("itemmsg","قلم قیمت اضافه شد.");await loadLists();}catch(e){msg("itemmsg",explain(e));}});
$("cancelSelect").addEventListener("click",clearList);$("refresh").addEventListener("click",async()=>{try{await Promise.all([loadStock(),loadLists()]);}catch(e){msg("authmsg",explain(e));}});
initialize();
})();
</script></body></html>"""

@router.get("/trade/workspace", response_class=HTMLResponse)
def trade_workspace_page():
    return HTMLResponse(PAGE, headers={
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "X-Frame-Options": "DENY",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "Cache-Control": "no-store",
    })
