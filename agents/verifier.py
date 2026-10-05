from app.providers import ai_provider, contact_extractor

class VerificationAgent:
    def _score(self, b, analysis):
        a=(analysis or {}).get('parsed') or {}
        evidence=0
        evidence += 15 if b.get('contact',{}).get('emails') else 0
        evidence += 10 if b.get('contact',{}).get('phones') else 0
        evidence += 15 if b.get('contact',{}).get('contact_pages') else 0
        evidence += 10 if b.get('website',{}).get('reachable') else 0
        evidence += 10 if b.get('buyer_signals') else 0
        ai_score=a.get('score') if isinstance(a.get('score'),(int,float)) else 0
        return max(0,min(100, round(evidence + ai_score*0.4)))

    def run(self, buyers):
        out=[]
        for b in buyers:
            if not b.get('url'):
                out.append({**b,'verification':{'status':'pending','score':0,'risk_flags':['no_url']}})
                continue
            contact=contact_extractor.extract(b['url'])
            enriched={**b,'website':contact.get('website',{}),'contact':contact.get('contact',{}),
                      'buyer_signals':contact.get('buyer_signals',[])}
            a=ai_provider.analyze('buyer_verification', enriched)
            score=self._score(enriched,a)
            parsed=a.get('parsed') or {}
            out.append({**enriched,'verification':{
                'status':'ai_reviewed' if a.get('status')=='ok' else 'pending',
                'score':score,'company_name':parsed.get('company_name') or b.get('title'),
                'buyer_type':parsed.get('buyer_type'),'risk_flags':parsed.get('risk_flags',[]),
                'evidence':parsed.get('evidence',[]),'analysis':a
            }})
        return out
