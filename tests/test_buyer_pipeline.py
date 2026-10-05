from agents.verifier import VerificationAgent
from agents.matcher import MatchAgent

def test_verification_without_url():
    r=VerificationAgent().run([{'market':'Turkey','title':'x'}])[0]
    assert r['verification']['score']==0
    assert 'no_url' in r['verification']['risk_flags']

def test_match_uses_verification_score(monkeypatch):
    class A:
        def analyze(self,*a,**k): return {'status':'ok','parsed':{'fit_score':80,'reasons':['product fit']}}
    monkeypatch.setattr('agents.matcher.ai_provider',A())
    r=MatchAgent().run({},[{'verification':{'score':90}}])[0]
    assert r['match_score']==86
