from fastapi.testclient import TestClient
import app.db as db
from app.main import app

def test_crm_api(monkeypatch,tmp_path):
    monkeypatch.setattr(db,'DB_PATH',tmp_path/'api.db')
    db.DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    db.init_db()
    lid=db.upsert_lead({'title':'Buyer Co','domain':'buyer.example','market':'Oman','contact':{'emails':['sales@buyer.example']},'match_score':85})
    c=TestClient(app)
    r=c.get('/crm/stats'); assert r.status_code==200 and r.json()['total']==1
    r=c.get(f'/crm/leads/{lid}'); assert r.status_code==200 and r.json()['company_name']=='Buyer Co'
    r=c.patch(f'/crm/leads/{lid}',json={'stage':'contacted'}); assert r.status_code==200
    r=c.post(f'/crm/leads/{lid}/follow-up'); assert r.status_code==200 and r.json()['status']=='draft_only'
    r=c.get(f'/crm/leads/{lid}'); assert len(r.json()['activities'])==1


def test_rfq_to_negotiation_to_won_to_repeat(monkeypatch,tmp_path):
    monkeypatch.setattr(db,'DB_PATH',tmp_path/'deal.db')
    db.DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    db.init_db()
    lid=db.upsert_lead({'title':'Buyer Co','domain':'buyer.example','market':'Oman','contact':{'emails':['sales@buyer.example']},'match_score':85})
    c=TestClient(app)
    assert c.patch(f'/crm/leads/{lid}',json={'stage':'rfq'}).status_code==200
    assert c.patch(f'/crm/leads/{lid}',json={'stage':'negotiation'}).status_code==200
    deal = c.post(f'/crm/leads/{lid}/deal', json={
        'product_name':'Iranian Dates','unit':'kg','quantity':1000,'currency':'USD',
        'agreed_unit_price':3.0,'incoterm':'CIF','payment_terms':'TBD',
        'factory_share':2800,'network_commission':200,'approval_confirmed':True
    })
    assert deal.status_code == 200
    source_id=deal.json()['deal_id']
    assert c.patch(f'/crm/leads/{lid}',json={'stage':'repeat'}).status_code==400
    currency_mismatch = c.post(f'/crm/deals/{source_id}/repeat', json={
        'product_name':'Iranian Dates','unit':'kg','quantity':1000,'currency':'EUR',
        'agreed_unit_price':2.9,'incoterm':'CIF','payment_terms':'TBD',
        'factory_share':2500,'network_commission':None,'buyer_company':'Buyer Co',
        'country':'Oman','approval_confirmed':True
    })
    assert currency_mismatch.status_code == 400
    repeat = c.post(f'/crm/deals/{source_id}/repeat', json={
        'product_name':'Iranian Dates','unit':'kg','quantity':1000,'currency':'USD',
        'agreed_unit_price':2.9,'incoterm':'CIF','payment_terms':'TBD',
        'factory_share':2500,'network_commission':None,'buyer_company':'Buyer Co',
        'country':'Oman','approval_confirmed':True
    })
    assert repeat.status_code == 200, repeat.text
    body=repeat.json()
    assert body['source_deal_id']==source_id
    assert body['repeat_sequence']==1
    assert body['anti_circumvention'] is True
    assert body['network_commission'] > 0
    assert len(c.get('/crm/deals').json()) == 2
