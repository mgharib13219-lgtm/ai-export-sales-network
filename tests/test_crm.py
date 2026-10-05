from app.db import init_db, add_opportunity, upsert_lead, list_leads, update_lead

def test_crm_roundtrip(tmp_path, monkeypatch):
    import app.db as db
    monkeypatch.setattr(db,'DB_PATH',tmp_path/'test.db')
    db.DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    init_db()
    oid=add_opportunity({'product_name':'Test Product','country':'Oman'})
    lid=upsert_lead({'title':'Example Buyer','domain':'example.com','market':'Oman','contact':{'emails':['sales@example.com'],'phones':['+1 555 000']},'match_score':82},oid)
    assert list_leads()[0]['id']==lid
    assert update_lead(lid,stage='contacted',next_follow_up='2099-01-01T00:00:00+00:00')
    assert list_leads(stage='contacted')[0]['email']=='sales@example.com'
