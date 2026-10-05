from typing import Any
import ipaddress
import json
import re
import socket
from urllib.parse import urljoin, urlparse
import httpx
from .settings import settings

COUNTRY_CODES = {
    'turkey':'tr','oman':'om','uae':'ae','united arab emirates':'ae','qatar':'qa',
    'saudi arabia':'sa','iraq':'iq','kuwait':'kw','azerbaijan':'az','germany':'de',
    'italy':'it','spain':'es','portugal':'pt','france':'fr','netherlands':'nl',
    'poland':'pl','india':'in','pakistan':'pk','russia':'ru','kazakhstan':'kz',
    'georgia':'ge','armenia':'am','afghanistan':'af','china':'cn','malaysia':'my',
    'indonesia':'id'
}

def _safe_public_url(url: str) -> bool:
    try:
        p = urlparse(url)
        if p.scheme not in ('http', 'https') or not p.hostname:
            return False
        host = p.hostname.strip().lower()
        if host in {'localhost', 'localhost.localdomain'} or host.endswith('.localhost'):
            return False
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
                return False
        return True
    except Exception:
        return False

class SearchProvider:
    def search_buyers(self, query: str, country: str) -> list[dict[str, Any]]:
        if settings.search_provider != 'serpapi' or not settings.search_api_key:
            return []
        gl = COUNTRY_CODES.get(country.lower().strip())
        params = {'engine':'google','q':query,'api_key':settings.search_api_key,'num':10}
        if gl:
            params['gl'] = gl
        r = httpx.get(settings.search_base_url or 'https://serpapi.com/search.json',
                      params=params, timeout=30, follow_redirects=True)
        r.raise_for_status()
        data = r.json()
        return [{'title':x.get('title'),'url':x.get('link'),'snippet':x.get('snippet',''),'source':'google'}
                for x in data.get('organic_results',[])]

class ContactExtractor:
    PATHS = ('/contact','/contact-us','/about','/about-us','/company','/en/contact')

    def _public_host(self, url: str) -> bool:
        return _safe_public_url(url)

    def _fetch(self, url: str):
        current = url
        try:
            for _ in range(4):
                if not _safe_public_url(current):
                    return None
                r = httpx.get(current,
                              headers={'User-Agent':'AI-Export-Sales-Network/1.0'},
                              timeout=10, follow_redirects=False)
                if 300 <= r.status_code < 400 and r.headers.get('location'):
                    current = urljoin(current, r.headers['location'])
                    continue
                if r.status_code < 400 and 'text/html' in r.headers.get('content-type','') and _safe_public_url(str(r.url)):
                    return r
                return None
        except Exception:
            return None

    def extract(self, url: str):
        if not _safe_public_url(url):
            return {'website':{'reachable':False,'final_url':url,'status_code':None},
                    'contact':{'emails':[],'phones':[],'contact_pages':[]},'buyer_signals':[]}
        parsed = urlparse(url)
        base = f'{parsed.scheme}://{parsed.netloc}'
        r = self._fetch(url)
        pages, html = [], ''
        if r:
            html = r.text
            pages.append(str(r.url))
        for path in self.PATHS:
            u = urljoin(base, path)
            if u in pages:
                continue
            rr = self._fetch(u)
            if rr:
                html += '\n' + rr.text
                pages.append(str(rr.url))
                if len(pages) >= 4:
                    break
        emails = sorted(set(re.findall(r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}', html, re.I)))
        emails = [e for e in emails if not any(x in e.lower() for x in ('example.com','sentry.io','wixpress.com'))]
        phones = sorted(set(re.findall(r'(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)', html)))[:8]
        text = re.sub(r'<[^>]+>', ' ', html).lower()
        terms = ['importer','import','distributor','wholesale','wholesaler','procurement','purchasing','buyer','rfq','request for quotation','supplier']
        signals = [t for t in terms if t in text]
        return {'website':{'reachable':bool(r),'final_url':str(r.url) if r else url,'status_code':r.status_code if r else None},
                'contact':{'emails':emails[:10],'phones':phones,'contact_pages':pages[1:]},
                'buyer_signals':signals[:12]}

class AIProvider:
    def _parse(self, text):
        if not text:
            return None
        m = re.search(r'\{.*\}', text, re.S)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except Exception:
            return None

    def analyze(self, task, payload):
        if settings.ai_provider == 'openai' and settings.ai_api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=settings.ai_api_key, base_url=settings.ai_base_url or None)
                schema = ('Return JSON only. buyer_verification: company_name,buyer_type,score(0-100),'
                          'risk_flags,evidence. buyer_match: fit_score,reasons. outreach_writer: subject,body.')
                prompt = f'You are the {task} agent. {schema}\nINPUT:\n{json.dumps(payload,ensure_ascii=False)}'
                response = client.responses.create(
                    model=settings.ai_model,
                    input=prompt,
                    tools=[{'type':'web_search'}] if settings.ai_web_search else []
                )
                txt = response.output_text
                return {'status':'ok','task':task,'text':txt,'parsed':self._parse(txt)}
            except Exception as exc:
                return {'status':'error','task':task,'error':str(exc)}
        return {'status':'not_configured','task':task}

class EmailProvider:
    def send(self, to, subject, body):
        return {'status':'draft_only','to':to,'subject':subject,'body':body}

search_provider = SearchProvider()
contact_extractor = ContactExtractor()
ai_provider = AIProvider()
email_provider = EmailProvider()
