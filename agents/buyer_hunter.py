from urllib.parse import urlparse
from app.providers import search_provider

class BuyerHunter:
    def _domain(self, url):
        try:
            h = urlparse(url).netloc.lower().split(':')[0]
            return h[4:] if h.startswith('www.') else h
        except Exception:
            return ''

    def run(self, product, markets):
        out=[]; seen_domains=set()
        name=product.get('name',''); hs=product.get('hs_code') or ''
        for m in markets:
            country=m.get('country','')
            queries=[
                f'"{name}" importer {country}',
                f'"{name}" distributor wholesaler {country}',
                f'"{name}" buyer procurement {country}',
                f'"{name}" "request for quotation" {country}',
            ]
            if hs: queries.append(f'"{hs}" importer {country}')
            results=[]
            for q in queries:
                try:
                    rows=search_provider.search_buyers(q,country)
                    for r in rows: r['query']=q
                    results.extend(rows)
                except Exception:
                    continue
            if not results:
                out.append({'market':country,'status':'buyer_discovery_pending','query':name})
                continue
            for r in results:
                url=r.get('url') or ''
                domain=self._domain(url)
                if not domain or domain in seen_domains: continue
                seen_domains.add(domain)
                out.append({
                    'market':country,'query':r.get('query',name),'title':r.get('title'),
                    'url':url,'domain':domain,'snippet':r.get('snippet',''),
                    'source':r.get('source','search'),'status':'candidate'
                })
        return out
