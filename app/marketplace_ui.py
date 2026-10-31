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
body{max-width:1080px;margin:auto;padding:18px}
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
<p class="muted">ثبت محصول، درخواست خرید و کشف تأمین‌کننده برای هر نوع کالا. تطبیق‌ها پیشنهادی‌اند و به‌معنای تأیید هویت یا مجوز تجاری نیستند.</p>
<div class="grid"><button id="logout" class="secondary" hidden>خروج از حساب</button><span id="account" class="status">برای شروع وارد شوید یا حساب بسازید.</span></div></header>
<section id="auth"><h2>ورود یا ثبت‌نام</h2><div class="grid">
<input id="email" type="email" placeholder="ایمیل کاری">
<input id="password" type="password" placeholder="گذرواژه (حداقل ۱۲ نویسه)">
<input id="company" placeholder="نام شرکت">
<input id="country" placeholder="کشور">
<select id="role"><option value="producer">تولیدکننده / تأمین‌کننده</option><option value="buyer">خریدار</option></select>
</div><div class="grid"><button id="register">ایجاد حساب</button><button id="login" class="secondary">ورود</button></div><p id="authmsg" class="status" aria-live="polite"></p></section>
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
function node(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=String(text);return e;}
function showMessage(id,value){$(id).textContent=typeof value==='string'?value:JSON.stringify(value,null,2);}
async function loadProducts(){
 const params=new URLSearchParams();if($('search').value)params.set('q',$('search').value);
 if($('category').value)params.set('category',$('category').value);
 const data=await api('/marketplace/products?'+params.toString());
 const box=$('products');box.replaceChildren();
 if(!data.length){box.append(node('p','muted','محصولی یافت نشد.'));return;}
 data.forEach(p=>{const card=node('article','card');card.append(node('h3','',p.name),node('p','',p.category+' · '+p.origin),node('p','',p.description),node('p','muted','شرکت: '+p.company_name+' | کشور: '+p.country+' | ظرفیت: '+(p.capacity||'نامشخص')+' | MOQ: '+(p.moq||'نامشخص')));box.append(card);});
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
 $('producer').hidden=!user||user.role!=='producer';$('buyer').hidden=!user||user.role!=='buyer';
}
async function publish(){
 try{const data=await api('/marketplace/products',{method:'POST',body:JSON.stringify({name:$('pname').value,category:$('pcategory').value,description:$('pdesc').value,origin:$('porigin').value,capacity:$('pcapacity').value||null,moq:$('pmoq').value||null,target_markets:$('pmarkets').value||null})});showMessage('productmsg',data);await loadProducts();}
 catch(e){showMessage('productmsg',e.message);}
}
async function submitRequest(){
 try{const data=await api('/marketplace/requests',{method:'POST',body:JSON.stringify({title:$('rtitle').value,category:$('rcategory').value,specification:$('rspec').value,destination:$('rdestination').value,quantity:$('rquantity').value||null})});showMessage('requestmsg',data);}
 catch(e){showMessage('requestmsg',e.message);}
}
async function loadRequests(){
 try{const data=await api('/marketplace/requests');const box=$('requests');box.replaceChildren();
 data.forEach(r=>{const card=node('article','card');card.append(node('h3','',r.title),node('p','',r.category+' · '+r.destination),node('p','',r.specification+' · مقدار: '+(r.quantity||'نامشخص')));
 const btn=node('button','secondary','پیدا کردن محصولات من');btn.addEventListener('click',async()=>{try{const m=await api('/marketplace/matches/requests/'+r.id);card.append(node('pre','status',JSON.stringify(m.matches,null,2)));}catch(e){card.append(node('p','status',e.message));}});card.append(btn);box.append(card);});
 if(!data.length)box.append(node('p','muted','درخواست خرید بازی وجود ندارد.'));
 }catch(e){showMessage('requests',e.message);}
}
$('register').addEventListener('click',register);$('login').addEventListener('click',login);
$('publish').addEventListener('click',publish);$('submitrequest').addEventListener('click',submitRequest);
$('searchbtn').addEventListener('click',()=>loadProducts().catch(e=>showMessage('products',e.message)));
$('loadrequests').addEventListener('click',loadRequests);
$('logout').addEventListener('click',async()=>{try{await api('/marketplace/logout',{method:'POST'});}catch{}sessionStorage.removeItem('market_token');user=null;renderAccount();});
loadProducts().catch(e=>showMessage('products',e.message));
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
    })
