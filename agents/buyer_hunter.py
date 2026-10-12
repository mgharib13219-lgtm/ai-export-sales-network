from urllib.parse import urlparse
from app.providers import search_provider
from app.settings import settings

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
        provider_configured = settings.search_provider not in ('', 'none') and bool(settings.search_api_key)
        for m in markets:
            country=m.get('country','')
            queries=[
                f'"{name}" importer {country}',
                f'"{name}" distributor wholesaler {country}',
                f'"{name}" buyer procurement {country}',
                f'"{name}" "request for quotation" {country}',
            ]
            if hs: queries.append(f'"{hs}" importer {country}')
            results=[]; error_count=0
            for q in queries:
                try:
                    rows=search_provider.search_buyers(q,country)
                    for r in rows: r['query']=q
                    results.extend(rows)
                except Exception:
                    error_count += 1
            if not results:
                if not provider_configured:
                    status='provider_not_configured'
                    reason='Configure SEARCH_PROVIDER and SEARCH_API_KEY to discover live buyers.'
                elif error_count:
                    status='search_provider_error'
                    reason=f'Search failed for {error_count} queries; check provider credentials, quota, and connectivity.'
                else:
                    status='buyer_discovery_pending'
                    reason='Search completed without buyer results; broaden product terms or target market.'
                out.append({'market':country,'status':status,'query':name,'reason':reason,
                            'queries_attempted':len(queries),'query_errors':error_count})
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
