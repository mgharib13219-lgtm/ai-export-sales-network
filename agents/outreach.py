from app.providers import ai_provider
class OutreachAgent:
    def run(self, product, matches):
        out=[]
        for m in matches:
            emails=m.get('contact',{}).get('emails',[])
            if not emails:
                continue
            a=ai_provider.analyze('outreach_writer', {'product':product,'buyer':m})
            parsed=a.get('parsed') or {}
            out.append({'market':m.get('market'),'buyer':m.get('title'),'email':emails[0], 'channel':'email','status':'draft_only','draft':parsed or a})
        return out
