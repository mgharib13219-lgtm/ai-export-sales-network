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


def test_buyer_hunter_reports_missing_search_provider(monkeypatch):
    from types import SimpleNamespace
    import agents.buyer_hunter as module

    monkeypatch.setattr(module, 'settings', SimpleNamespace(search_provider='none', search_api_key=''))
    result = module.BuyerHunter().run({'name':'Dates'}, [{'country':'Oman'}])
    assert len(result) == 1
    assert result[0]['status'] == 'provider_not_configured'
    assert result[0]['queries_attempted'] == 4


def test_buyer_hunter_surfaces_provider_errors(monkeypatch):
    from types import SimpleNamespace
    import agents.buyer_hunter as module

    class BrokenSearch:
        def search_buyers(self, query, country):
            raise RuntimeError('provider unavailable')

    monkeypatch.setattr(module, 'settings', SimpleNamespace(search_provider='serpapi', search_api_key='configured'))
    monkeypatch.setattr(module, 'search_provider', BrokenSearch())
    result = module.BuyerHunter().run({'name':'Dates'}, [{'country':'Oman'}])
    assert result[0]['status'] == 'search_provider_error'
    assert result[0]['query_errors'] == 4
