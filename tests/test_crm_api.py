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
