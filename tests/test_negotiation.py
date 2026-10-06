from fastapi.testclient import TestClient
import app.db as db
from app.main import app

def test_negotiation_counteroffer_requires_human_review(monkeypatch, tmp_path):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'neg.db')
    db.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db.init_db()
    lid=db.upsert_lead({'title':'Buyer Co','domain':'buyer.example','market':'Oman','contact':{'emails':['sales@buyer.example']},'match_score':85})
    c=TestClient(app)
    assert c.patch(f'/crm/leads/{lid}',json={'stage':'rfq'}).status_code==200
    assert c.patch(f'/crm/leads/{lid}',json={'stage':'negotiation'}).status_code==200
    quote={'commercials':{'indicative_buyer_price':3.0}}
    r=c.post(f'/crm/leads/{lid}/negotiation-review',json={'quote':quote,'counter_unit_price':2.9,'max_discount_pct':5})
    assert r.status_code==200
    assert r.json()['decision']=='human_review_required'
    assert r.json()['within_approval_bounds'] is True
    assert r.json()['never_auto_accept'] is True
