from app.providers import ai_provider
class MatchAgent:
    def run(self, product, buyers):
        out=[]
        for b in buyers:
            a=ai_provider.analyze('buyer_match', {'product':product,'buyer':b})
            parsed=a.get('parsed') or {}
            score=b.get('verification',{}).get('score',0)
            fit=parsed.get('fit_score') if isinstance(parsed.get('fit_score'),(int,float)) else 0
            final=round(score*0.6+fit*0.4)
            out.append({**b,'fit':a,'match_score':final,'match_reasons':parsed.get('reasons',[])})
        return out
