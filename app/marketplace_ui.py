"""Small public-facing UI for the product-agnostic marketplace MVP."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["marketplace-ui"])

PAGE = r"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>بازار تجارت جهانی</title>
<style>
:root{font-family:system-ui,Tahoma,Arial;color:#182230;background:#f4f6f8}
body{max-width:1080px;margin:auto;padding:18px} nav{display:flex;gap:12px;flex-wrap:wrap;align-items:center} nav a{color:#155eef;text-decoration:none;font-weight:600} header nav{margin:10px 0} header nav a{padding:7px 10px;border-radius:8px;background:#f0f4f8} button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #84adff;outline-offset:2px} @media(max-width:600px){body{padding:8px}header,section{padding:13px}nav{gap:6px}nav a{font-size:13px}}
header,section{background:#fff;border:1px solid #e5e9ef;border-radius:14px;padding:18px;margin:12px 0}
h1,h2{margin-top:0}.muted{color:#667085;font-size:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}
input,textarea,select,button{font:inherit;width:100%;box-sizing:border-box;padding:10px;border:1px solid #ccd3dc;border-radius:9px;margin:4px 0}
textarea{min-height:90px}button{background:#172b4d;color:white;cursor:pointer;border:0}
button.secondary{background:#eef2f6;color:#182230;border:1px solid #d7dde5}
.card{border:1px solid #e5e9ef;border-radius:10px;padding:12px;margin:8px 0}
.status{padding:8px;background:#f0f4f8;border-radius:8px;white-space:pre-wrap}
[hidden]{display:none!important}
</style></head><body>
<header><h1>بازار تجارت جهانی</h1>
<div class="grid" style="align-items:center"><span class="muted" id="language-label">زبان / Language</span><select id="language" aria-label="Language"><option value="fa">فارسی</option><option value="en">English</option></select></div><nav aria-label="ناوبری اصلی"><a href="/dashboard">داشبورد عملیاتی</a><a href="/market">بازار جهانی</a><a href="/trade/workspace">انبار و لیست قیمت صادراتی</a><a href="/buyer/workspace">پنل خریدار</a></nav>
<p class="muted">ثبت محصول، درخواست خرید و کشف تأمین‌کننده برای هر نوع کالا. تطبیق‌ها پیشنهادی‌اند و به‌معنای تأیید هویت یا مجوز تجاری نیستند.</p>
<div class="grid"><button id="logout" class="secondary" hidden>خروج از حساب</button><span id="account" class="status">برای شروع وارد شوید یا حساب بسازید.</span></div></header>
<section id="auth"><h2>ورود یا ثبت‌نام</h2><div class="grid">
<input id="email" type="email" placeholder="ایمیل کاری">
<input id="password" type="password" placeholder="گذرواژه (حداقل ۱۲ نویسه)">
<input id="company" placeholder="نام شرکت">
<input id="country" placeholder="کشور">
<select id="role"><option value="producer">تولیدکننده / تأمین‌کننده</option><option value="buyer">خریدار</option></select>
</div><div class="grid"><button id="register">ایجاد حساب</button><button id="login" class="secondary">ورود</button></div><p id="authmsg" class="status" aria-live="polite"></p></section>
<section id="account-settings" hidden><h2>امنیت حساب</h2><div class="grid"><input id="currentpass" type="password" placeholder="گذرواژه فعلی"><input id="newpass" type="password" placeholder="گذرواژه جدید (حداقل ۱۲ نویسه)"></div><button id="changepass">تغییر گذرواژه و خروج از همه دستگاه‌ها</button><p id="passwordmsg" class="status"></p></section>
<section id="subscription" hidden><h2>پلن و امکانات حساب</h2><p id="subscriptionstate" class="status">در حال بارگذاری...</p><div id="plans" class="grid"></div><p id="upgradeMessage" class="status" aria-live="polite"></p>
<h2>جست‌وجوی خریدار با ایجنت</h2><p class="muted">جست‌وجو فقط در نتایج عمومی موتور جست‌وجو انجام می‌شود. هیچ وب‌سایتی خزش نمی‌شود، اطلاعات تماس برداشت نمی‌شود و پیامی ارسال نمی‌شود. هر نتیجه باید پیش از تماس از نظر ارتباط، شرایط سایت و قوانین حریم خصوصی و بازاریابی بررسی شود.</p>
<div class="grid"><input id="buyerterms" placeholder="محصول یا کلمه کلیدی، مثلاً قطعات پمپ صنعتی"><input id="buyercountry" placeholder="کشور هدف، مثلاً آلمان"><button id="discoverbuyers">جست‌وجوی خریداران</button></div><p id="agentcredits" class="status"></p><button id="refreshBuyerCandidates" class="secondary" type="button">نمایش سرنخ‌های ذخیره‌شده</button><div id="buyerCandidates" aria-live="polite"></div></section>
<section><h2>فهرست جامع تعرفه‌های گمرکی ایران (HS)</h2>
<p class="muted">جست‌وجو بر اساس کد تعرفه یا شرح فارسی/انگلیسی؛ نمایش فقط ردیف‌هایی که از منبع رسمی/مستند وارد شده‌اند.</p>
<div class="grid"><input id="hscodeq" placeholder="کد تعرفه یا نام کالا"><select id="hslevel"><option value="">همه سطوح</option><option value="2">۲ رقمی</option><option value="4">۴ رقمی</option><option value="6">۶ رقمی</option><option value="8">۸ رقمی</option></select><button id="hscodebtn">جست‌وجوی تعرفه</button></div>
<p id="hscount" class="muted" aria-live="polite">برای مشاهده، جست‌وجو کنید.</p><div id="hscatalog" aria-live="polite"></div></section>
<section><h2>جست‌وجوی محصولات</h2><div class="grid"><input id="search" placeholder="نام یا مشخصات محصول"><input id="category" placeholder="دسته‌بندی"><button id="searchbtn">جست‌وجو</button></div><div id="products" aria-live="polite"></div></section>
<section id="producer" hidden><h2>ثبت محصول</h2><div class="grid">
<input id="pname" placeholder="نام محصول"><input id="pcategory" placeholder="دسته‌بندی">
<input id="porigin" placeholder="کشور مبدأ"><input id="pcapacity" placeholder="ظرفیت تولید">
<input id="pmoq" placeholder="حداقل سفارش"><input id="pmarkets" placeholder="بازارهای هدف">
</div><textarea id="pdesc" placeholder="مشخصات واقعی، استانداردها و توضیحات محصول"></textarea>
<button id="publish">انتشار محصول</button><p id="productmsg" class="status"></p>
<h2>درخواست‌های خرید باز</h2><button id="loadrequests" class="secondary">بارگذاری درخواست‌ها</button><div id="requests"></div></section>
<section id="buyer" hidden><h2>ثبت درخواست خرید</h2><div class="grid">
<input id="rtitle" placeholder="نام کالا"><input id="rcategory" placeholder="دسته‌بندی">
<input id="rdestination" placeholder="کشور مقصد"><input id="rquantity" placeholder="مقدار موردنیاز">
</div><textarea id="rspec" placeholder="مشخصات، کیفیت، بسته‌بندی و الزامات"></textarea>
<label><input id="rshare" type="checkbox" style="width:auto"> اجازه می‌دهم نام شرکت، کشور و ایمیل کاری من فقط برای تأمین‌کنندگان Premium نمایش داده شود.</label>
<button id="submitrequest">ثبت درخواست</button><p id="requestmsg" class="status"></p></section>
<script>
const $=id=>document.getElementById(id);
let user=null;
const token=()=>sessionStorage.getItem('market_token')||'';
async function api(path,options={}) {
 const headers={...(options.headers||{})};
 if(token()) headers.Authorization='Bearer '+token();
 if(options.body) headers['Content-Type']='application/json';
 const response=await fetch(path,{...options,headers});
 let data={};try{data=await response.json()}catch{}
 if(!response.ok) throw new Error(data.detail||data.error||('HTTP '+response.status));
 return data;
}

const languageCopy={
 en:{
  title:'Global Trade Marketplace',nav:['Dashboard','Global marketplace','Export inventory & price lists','Buyer workspace'],
  headings:['Global Trade Marketplace','Sign in or create an account','Account security','Plan and account features','Buyer discovery agent','Iran Customs Tariff Directory (HS)','Product search','Publish a product','Open purchase requests','Create a purchase request'],
  ids:{account:'Sign in or create an account to begin.',register:'Create account',login:'Sign in',changepass:'Change password and sign out all devices',discoverbuyers:'Find buyers',refreshBuyerCandidates:'Show saved leads',hscodebtn:'Search tariffs',searchbtn:'Search',publish:'Publish product',loadrequests:'Load requests',submitrequest:'Submit request',logout:'Sign out'},
  placeholders:{email:'Business email',password:'Password (at least 12 characters)',company:'Company name',country:'Country',hscodeq:'Tariff code or product name',search:'Product name or specifications',category:'Category',buyerterms:'Product or keyword, e.g. industrial pump parts',buyercountry:'Target country, e.g. Germany',pname:'Product name',pcategory:'Category',porigin:'Country of origin',pcapacity:'Production capacity',pmoq:'Minimum order quantity',pmarkets:'Target markets',rtitle:'Product name',rcategory:'Category',rdestination:'Destination country',rquantity:'Required quantity'},
  intro:'List products, submit buying requests and discover suppliers worldwide. Matches are suggestions, not proof of identity or trade authorization.',
  tariff:'Search by HS code or Persian/English description. Only rows imported from documented sources are displayed.',
  start:'For account access, sign in or create an account.',
  role:['Producer / Supplier','Buyer'],levels:['All levels','2 digits','4 digits','6 digits','8 digits']
 },
 fa:{
  title:'بازار تجارت جهانی',nav:['داشبورد','بازار جهانی','انبار و لیست قیمت صادراتی','پنل خریدار'],
  headings:['بازار تجارت جهانی','ورود یا ثبت‌نام','امنیت حساب','پلن و امکانات حساب','جست‌وجوی خریدار با ایجنت','فهرست جامع تعرفه‌های گمرکی ایران (HS)','جست‌وجوی محصولات','ثبت محصول','درخواست‌های خرید باز','ثبت درخواست خرید'],
  ids:{account:'برای شروع وارد شوید یا حساب بسازید.',register:'ایجاد حساب',login:'ورود',changepass:'تغییر گذرواژه و خروج از همه دستگاه‌ها',discoverbuyers:'جست‌وجوی خریداران',refreshBuyerCandidates:'نمایش سرنخ‌های ذخیره‌شده',hscodebtn:'جست‌وجوی تعرفه',searchbtn:'جست‌وجو',publish:'انتشار محصول',loadrequests:'بارگذاری درخواست‌ها',submitrequest:'ثبت درخواست',logout:'خروج از حساب'},
  placeholders:{email:'ایمیل کاری',password:'گذرواژه (حداقل ۱۲ نویسه)',company:'نام شرکت',country:'کشور',hscodeq:'کد تعرفه یا نام کالا',search:'نام یا مشخصات محصول',category:'دسته‌بندی',buyerterms:'محصول یا کلمه کلیدی، مثلاً قطعات پمپ صنعتی',buyercountry:'کشور هدف، مثلاً آلمان',pname:'نام محصول',pcategory:'دسته‌بندی',porigin:'کشور مبدأ',pcapacity:'ظرفیت تولید',pmoq:'حداقل سفارش',pmarkets:'بازارهای هدف',rtitle:'نام کالا',rcategory:'دسته‌بندی',rdestination:'کشور مقصد',rquantity:'مقدار موردنیاز'},
  intro:'ثبت محصول، درخواست خرید و کشف تأمین‌کننده برای هر نوع کالا. تطبیق‌ها پیشنهادی‌اند و به‌معنای تأیید هویت یا مجوز تجاری نیستند.',
  tariff:'جست‌وجو بر اساس کد تعرفه یا شرح فارسی/انگلیسی؛ نمایش فقط ردیف‌هایی که از منبع رسمی/مستند وارد شده‌اند.',
  start:'برای شروع وارد شوید یا حساب بسازید.',
  role:['تولیدکننده / تأمین‌کننده','خریدار'],levels:['همه سطوح','۲ رقمی','۴ رقمی','۶ رقمی','۸ رقمی']
 }
};
function applyLanguage(lang){
 const t=languageCopy[lang]||languageCopy.fa,english=lang==='en';
 document.documentElement.lang=english?'en':'fa';document.documentElement.dir=english?'ltr':'rtl';
 document.title=t.title;
 document.querySelector('header h1').textContent=t.headings[0];
 document.querySelector('header .muted').textContent=t.intro;
 document.querySelectorAll('header nav a').forEach((a,i)=>a.textContent=t.nav[i]||a.textContent);
 document.querySelectorAll('h2').forEach((e,i)=>{if(t.headings[i+1])e.textContent=t.headings[i+1];});
 Object.entries(t.ids).forEach(([id,value])=>{const e=$(id);if(e)e.textContent=value;});
 Object.entries(t.placeholders).forEach(([id,value])=>{const e=$(id);if(e)e.placeholder=value;});
 const role=$('role');role.options[0].textContent=t.role[0];role.options[1].textContent=t.role[1];
 const levels=$('hslevel');t.levels.forEach((v,i)=>levels.options[i].textContent=v);
 $('language-label').textContent=english?'Language / زبان':'زبان / Language';
 $('hscount').textContent=english?'Search to view tariff entries.':'برای مشاهده، جست‌وجو کنید.';
 $('language').value=lang;
 try{localStorage.setItem('market_language',lang);}catch{}
}

function node(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=String(text);return e;}
function showMessage(id,value){$(id).textContent=typeof value==='string'?value:JSON.stringify(value,null,2);}
async function loadHsCatalog(){
 const params=new URLSearchParams();if($('hscodeq').value.trim())params.set('q',$('hscodeq').value.trim());
 if($('hslevel').value)params.set('level',$('hslevel').value);
 params.set('limit','50');
 const data=await api('/trade/hs-catalog?'+params.toString());
 const box=$('hscatalog');box.replaceChildren();
 $('hscount').textContent='کل ردیف‌های فعال واردشده: '+data.active_catalog_rows+' · نمایش: '+data.items.length;
 if(!data.items.length){box.append(node('p','muted','ردیفی یافت نشد؛ ممکن است فایل تعرفه هنوز وارد نشده باشد.'));return;}
 const table=node('div','card');
 data.items.forEach(item=>{
  const row=node('div','card');
  row.append(node('strong','',item.hs_code),node('p','',item.description_fa||'شرح فارسی ثبت نشده'),node('p','muted',(item.description_en||'')+' · والد: '+(item.parent_code||'—')+' · منبع: '+item.source+' · نسخه: '+(item.source_version||'—')));
  table.append(row);
 });
 box.append(table);
}
async function loadProducts(){
 const params=new URLSearchParams();if($('search').value)params.set('q',$('search').value);
 if($('category').value)params.set('category',$('category').value);
 const data=await api('/marketplace/products?'+params.toString());
 const box=$('products');box.replaceChildren();
 if(!data.length){box.append(node('p','muted','محصولی یافت نشد.'));return;}
 data.forEach(p=>{const card=node('article','card');card.append(node('h3','',p.name),node('p','',p.category+' · '+p.origin),node('p','',p.description),node('p','muted','شرکت: '+p.company_name+' | کشور: '+p.country+' | ظرفیت: '+(p.capacity||'نامشخص')+' | MOQ: '+(p.moq||'نامشخص')));box.append(card);});
}
async function loadSubscription(){
 const [current,plans,credits]=await Promise.all([
  api('/marketplace/subscription/me'),api('/marketplace/subscription/plans'),api('/marketplace/subscription/credits')
 ]);
 const ent=current.entitlements||{};
 $('subscriptionstate').textContent='پلن فعلی: '+(ent.name||current.plan_code)+' · آگهی فعال مجاز: '+(ent.published_listing_limit||0)+' · اعتبار جست‌وجوی ماهانه: '+credits.used+'/'+credits.limit+' · اعتبار باقی‌مانده: '+credits.remaining;
 $('agentcredits').textContent='اعتبار جست‌وجوی این ماه: '+credits.remaining+' از '+credits.limit+' باقی مانده است.';
 const box=$('plans');box.replaceChildren();
 if(current.billing_provider==='stripe'){
  const manage=node('button','secondary','مدیریت یا لغو اشتراک');
  manage.addEventListener('click',async()=>{
   try{
    const result=await api('/marketplace/subscription/billing/portal',{method:'POST'});
    window.location.assign(result.portal_url);
   }catch(e){showMessage('upgradeMessage',e.message);}
  });
  box.append(manage);
 }
 (plans.plans||[]).forEach(p=>{
  const card=node('article','card');
  card.append(node('h3','',p.name),node('p','',p.monthly_price_display||'قیمت هنوز تعیین نشده'));
  card.append(node('p','', 'آگهی فعال: '+p.published_listing_limit+' · اعتبار ایجنت در ماه: '+p.agent_sourcing_credits));
  card.append(node('p','muted','دسترسی سرنخ: '+p.lead_access+' · دیده‌شدن: '+p.visibility));
  (p.features||[]).forEach(feature=>card.append(node('p','muted',feature)));
  if(p.code!=='free'){
   const btn=node('button',p.billing_enabled?'':'secondary',p.billing_enabled?'پرداخت امن و ارتقا':'درخواست بررسی ارتقا');
   btn.addEventListener('click',async()=>{
    try{
     if(p.billing_enabled){
      const checkout=await api('/marketplace/subscription/billing/checkout?plan_code='+encodeURIComponent(p.code),{method:'POST'});
      window.location.assign(checkout.checkout_url);
     }else{
      const result=await api('/marketplace/subscription/upgrade-requests',{method:'POST',body:JSON.stringify({plan_code:p.code,note:''})});
      showMessage('upgradeMessage','درخواست ارتقا ثبت شد. شماره پیگیری: '+result.request_id+'؛ پلن تا تأیید تغییر نمی‌کند.');
     }
    }catch(e){showMessage('upgradeMessage',e.message);}
   });
   card.append(btn);
  }
  box.append(card);
 });
}
async function discoverBuyers(){
 const terms=$('buyerterms').value.trim(),country=$('buyercountry').value.trim();
 if(!terms||!country){showMessage('buyerCandidates','نام محصول و کشور هدف را وارد کنید.');return;}
 $('discoverbuyers').disabled=true;showMessage('buyerCandidates','در حال جست‌وجو در منابع عمومی مجاز...');
 try{
  const result=await api('/marketplace/agent/buyer-discovery',{method:'POST',body:JSON.stringify({product_terms:terms,target_country:country})});
  $('agentcredits').textContent='اعتبار باقی‌مانده: '+result.credits.remaining+' از '+result.credits.limit;
  const box=$('buyerCandidates');box.replaceChildren();
  if(!result.candidates.length)box.append(node('p','muted','نتیجه جدیدی پیدا نشد.'));
  result.candidates.forEach(item=>{
   const card=node('article','card');
   card.append(node('h3','',item.title),node('p','',item.snippet),node('p','muted','وضعیت: بررسی دستی لازم است · منبع: '+item.source_provider));
   const link=node('a','', 'بازکردن منبع عمومی');link.href=item.source_url;link.target='_blank';link.rel='noopener noreferrer';card.append(link);
   const relevant=node('button','secondary','مرتبط است');relevant.addEventListener('click',async()=>{try{await api('/marketplace/agent/buyer-candidates/'+item.id,{method:'PATCH',body:JSON.stringify({relevant:true,note:'Reviewed by supplier'})});relevant.disabled=true;relevant.textContent='علامت‌گذاری شد';}catch(e){card.append(node('p','status',e.message));}});
   const reject=node('button','secondary','نامرتبط');reject.addEventListener('click',async()=>{try{await api('/marketplace/agent/buyer-candidates/'+item.id,{method:'PATCH',body:JSON.stringify({relevant:false,note:'Not relevant'})});card.remove();}catch(e){card.append(node('p','status',e.message));}});
   card.append(relevant,reject);box.append(card);
  });
 }catch(e){showMessage('buyerCandidates',e.message);try{const c=await api('/marketplace/subscription/credits');$('agentcredits').textContent='اعتبار باقی‌مانده: '+c.remaining+' از '+c.limit;}catch{}}
 finally{$('discoverbuyers').disabled=false;}
}


async function loadSavedBuyerCandidates(){
 const box=$('buyerCandidates');
 box.replaceChildren();
 try{
  const items=await api('/marketplace/agent/buyer-candidates?limit=100');
  if(!items.length){box.append(node('p','muted','هنوز سرنخ ذخیره‌شده‌ای ندارید. یک جست‌وجوی جدید انجام دهید.'));return;}
  items.forEach(item=>{
   const card=node('article','card');
   card.append(node('h3','',item.title),node('p','',item.snippet||'خلاصه‌ای از منبع ارائه نشده است.'));
   card.append(node('p','muted','وضعیت: '+({needs_supplier_review:'نیازمند بررسی شما',supplier_marked_relevant:'مرتبط علامت‌گذاری شده',rejected:'نامرتبط'}[item.review_status]||item.review_status)+' · کشور هدف: '+item.target_country+' · منبع: '+item.source_provider));
   const link=node('a','', 'بازکردن منبع عمومی');link.href=item.source_url;link.target='_blank';link.rel='noopener noreferrer';card.append(link);
   if(item.review_status==='needs_supplier_review'){
    const relevant=node('button','secondary','مرتبط است');
    relevant.addEventListener('click',async()=>{
     relevant.disabled=true;
     try{await api('/marketplace/agent/buyer-candidates/'+item.id,{method:'PATCH',body:JSON.stringify({relevant:true,note:'Reviewed by supplier'})});await loadSavedBuyerCandidates();}
     catch(e){relevant.disabled=false;card.append(node('p','status',e.message));}
    });
    const reject=node('button','secondary','نامرتبط');
    reject.addEventListener('click',async()=>{
     reject.disabled=true;
     try{await api('/marketplace/agent/buyer-candidates/'+item.id,{method:'PATCH',body:JSON.stringify({relevant:false,note:'Not relevant'})});await loadSavedBuyerCandidates();}
     catch(e){reject.disabled=false;card.append(node('p','status',e.message));}
    });
    card.append(relevant,reject);
   }
   box.append(card);
  });
 }catch(e){box.append(node('p','status','بارگذاری سرنخ‌های ذخیره‌شده ناموفق بود: '+e.message));}
}

async function register(){
 try{const data=await api('/marketplace/register',{method:'POST',body:JSON.stringify({email:$('email').value,company_name:$('company').value,country:$('country').value,role:$('role').value,password:$('password').value})});showMessage('authmsg',data.next_step);}
 catch(e){showMessage('authmsg',e.message);}
}
async function login(){
 try{const data=await api('/marketplace/login',{method:'POST',body:JSON.stringify({email:$('email').value,password:$('password').value})});sessionStorage.setItem('market_token',data.access_token);user=data.user;renderAccount();}
 catch(e){showMessage('authmsg',e.message);}
}
function renderAccount(){
 $('account').textContent=user?user.company_name+' · '+user.role+' · '+user.country:'برای شروع وارد شوید یا حساب بسازید.';
 $('logout').hidden=!user;$('auth').hidden=!!user;
 $('producer').hidden=!user||user.role!=='producer';$('buyer').hidden=!user||user.role!=='buyer';$('account-settings').hidden=!user;
 $('subscription').hidden=!user||user.role!=='producer';
 if(user&&user.role==='producer'){
  const billingState=new URLSearchParams(window.location.search).get('billing');
  if(billingState==='success')showMessage('upgradeMessage','از صفحهٔ پرداخت برگشته‌اید؛ پلن فقط پس از تأیید امن وب‌هوک به‌روزرسانی می‌شود.');
  else if(billingState==='cancel')showMessage('upgradeMessage','پرداخت لغو شد؛ پلن فعلی شما بدون تغییر باقی ماند.');
  loadSubscription().catch(e=>showMessage('subscriptionstate',e.message));
  loadSavedBuyerCandidates();
 }
}
async function changePassword(){
 try{const data=await api('/marketplace/password',{method:'POST',body:JSON.stringify({current_password:$('currentpass').value,new_password:$('newpass').value})});showMessage('passwordmsg',data);sessionStorage.removeItem('market_token');user=null;renderAccount();}
 catch(e){showMessage('passwordmsg',e.message);}
}
async function publish(){
 try{const data=await api('/marketplace/products',{method:'POST',body:JSON.stringify({name:$('pname').value,category:$('pcategory').value,description:$('pdesc').value,origin:$('porigin').value,capacity:$('pcapacity').value||null,moq:$('pmoq').value||null,target_markets:$('pmarkets').value||null})});showMessage('productmsg',data);await loadProducts();}
 catch(e){showMessage('productmsg',e.message);}
}
async function submitRequest(){
 try{const data=await api('/marketplace/requests',{method:'POST',body:JSON.stringify({title:$('rtitle').value,category:$('rcategory').value,specification:$('rspec').value,destination:$('rdestination').value,quantity:$('rquantity').value||null,share_contact:$('rshare').checked})});showMessage('requestmsg',data);}
 catch(e){showMessage('requestmsg',e.message);}
}
async function loadRequests(){
 try{
  const data=await api('/marketplace/requests');
  const box=$('requests');box.replaceChildren();
  (data||[]).forEach(r=>{
   const card=node('article','card');
   card.append(node('h3','',r.title),node('p','',r.category+' · '+r.destination));
   const details=r.specification||r.specification_preview||'برای مشاهده مشخصات کامل، پلن خود را ارتقا دهید.';
   card.append(node('p','',details+' · مقدار: '+(r.quantity||'در پلن فعلی نمایش داده نمی‌شود')));
   if(r.buyer_company){
    card.append(node('p','muted','شرکت خریدار: '+r.buyer_company+' · '+(r.buyer_country||'')+' · '+(r.buyer_email||'')));
   }
   const btn=node('button','secondary','پیدا کردن محصولات من');
   btn.addEventListener('click',async()=>{
    try{
     const m=await api('/marketplace/matches/requests/'+r.id);
     card.append(node('pre','status',JSON.stringify(m.matches,null,2)));
    }catch(e){card.append(node('p','status',e.message));}
   });
   card.append(btn);box.append(card);
  });
  if(!data.length)box.append(node('p','muted','درخواست خرید بازی وجود ندارد.'));
 }catch(e){showMessage('requests',e.message);}
}
$('language').addEventListener('change',e=>applyLanguage(e.target.value));
$('register').addEventListener('click',register);$('login').addEventListener('click',login);$('changepass').addEventListener('click',changePassword);
$('publish').addEventListener('click',publish);$('submitrequest').addEventListener('click',submitRequest);
$('searchbtn').addEventListener('click',()=>loadProducts().catch(e=>showMessage('products',e.message)));
$('hscodebtn').addEventListener('click',()=>loadHsCatalog().catch(e=>showMessage('hscatalog',e.message)));
$('hscodeq').addEventListener('keydown',e=>{if(e.key==='Enter')loadHsCatalog().catch(err=>showMessage('hscatalog',err.message));});
$('loadrequests').addEventListener('click',loadRequests);
$('discoverbuyers').addEventListener('click',discoverBuyers);
$('refreshBuyerCandidates').addEventListener('click',loadSavedBuyerCandidates);
$('logout').addEventListener('click',async()=>{try{await api('/marketplace/logout',{method:'POST'});}catch{}sessionStorage.removeItem('market_token');user=null;renderAccount();});
loadProducts().catch(e=>showMessage('products',e.message));
let initialLanguage='fa';try{initialLanguage=localStorage.getItem('market_language')||'fa';}catch{}applyLanguage(initialLanguage);
if(token())api('/marketplace/me').then(data=>{user=data;renderAccount();}).catch(()=>{sessionStorage.removeItem('market_token');renderAccount();});
</script></body></html>"""


@router.get("/market", response_class=HTMLResponse)
def marketplace_home():
    return HTMLResponse(PAGE, headers={
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "X-Frame-Options": "DENY",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "Cache-Control": "no-store",
    })
