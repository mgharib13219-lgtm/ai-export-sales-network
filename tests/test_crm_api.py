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
    assert c.patch(f'/crm/leads/{lid}',json={'stage':'repeat'}).status_code==200
