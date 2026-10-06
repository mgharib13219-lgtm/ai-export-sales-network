from fastapi.testclient import TestClient
import app.db as db
from app.main import app

def test_human_approved_deal_and_repeat(monkeypatch, tmp_path):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'deal.db')
    db.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db.init_db()
    lid = db.upsert_lead({'title':'Buyer Co','domain':'buyer.example','market':'Oman','contact':{'emails':['sales@buyer.example']},'match_score':85})
    c = TestClient(app)
    assert c.patch(f'/crm/leads/{lid}', json={'stage':'rfq'}).status_code == 200
    assert c.patch(f'/crm/leads/{lid}', json={'stage':'negotiation'}).status_code == 200
    body = {'product_name':'Iranian Dates','unit':'kg','quantity':1000,'currency':'USD','agreed_unit_price':2.9,'incoterm':'CIF','payment_terms':'30% advance / 70% against documents','factory_share':2500,'network_commission':200,'approval_confirmed':False}
    assert c.post(f'/crm/leads/{lid}/deal', json=body).status_code == 400
    body['approval_confirmed'] = True
    r = c.post(f'/crm/leads/{lid}/deal', json=body)
    assert r.status_code == 200 and r.json()['status'] == 'won'
    deal_id = r.json()['deal_id']
    deal = c.get(f'/crm/deals/{deal_id}')
    assert deal.status_code == 200 and deal.json()['network_commission'] == 200
    assert c.post(f'/crm/deals/{deal_id}/repeat').status_code == 200
    assert c.get(f'/crm/leads/{lid}').json()['stage'] == 'repeat'
