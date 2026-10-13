from fastapi.testclient import TestClient
import app.db as db
from app.main import app

def _lead():
    return db.upsert_lead({
        'title':'Buyer Co','domain':'buyer.example','market':'Oman',
        'contact':{'emails':['sales@buyer.example']},'match_score':85
    })

def _move_to_negotiation(c, lid):
    assert c.patch(f'/crm/leads/{lid}', json={'stage':'rfq'}).status_code == 200
    assert c.patch(f'/crm/leads/{lid}', json={'stage':'negotiation'}).status_code == 200

def test_repeat_deal_protection_and_commission(monkeypatch, tmp_path):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'repeat.db')
    db.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db.init_db()
    c=TestClient(app)
    lid=_lead()
    _move_to_negotiation(c,lid)
    body={
        'product_name':'Iranian Dates','unit':'kg','quantity':1000,'currency':'USD',
        'agreed_unit_price':3.0,'incoterm':'CIF','payment_terms':'30% advance / 70% documents',
        'factory_share':2800,'network_commission':200,'approval_confirmed':True
    }
    won=c.post(f'/crm/leads/{lid}/deal',json=body)
    assert won.status_code==200
    source=won.json()['deal_id']
    source_deal=c.get(f'/crm/deals/{source}').json()
    assert source_deal['repeat_until']

    repeat={
        'product_name':'Iranian Dates','unit':'kg','quantity':500,'currency':'USD',
        'agreed_unit_price':3.2,'incoterm':'CIF','payment_terms':'30% advance / 70% documents',
        'factory_share':1490,'approval_confirmed':True
    }
    r=c.post(f'/crm/deals/{source}/repeat',json=repeat)
    assert r.status_code==200
    assert r.json()['anti_circumvention'] is True
    assert round(r.json()['network_commission'], 6) == round(200 / 3000 * 1600, 6)
    rd=c.get(f"/crm/deals/{r.json()['deal_id']}").json()
    assert rd['source_deal_id']==source
    assert rd['repeat_sequence']==1

def test_repeat_requires_human_approval(monkeypatch, tmp_path):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'repeat_approval.db')
    db.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db.init_db()
    c=TestClient(app)
    lid=_lead()
    _move_to_negotiation(c,lid)
    won=c.post(f'/crm/leads/{lid}/deal',json={
        'product_name':'Iranian Dates','unit':'kg','quantity':1000,'currency':'USD',
        'agreed_unit_price':3.0,'incoterm':'CIF','payment_terms':'TBD',
        'factory_share':2800,'network_commission':200,'approval_confirmed':True
    })
    source=won.json()['deal_id']
    r=c.post(f'/crm/deals/{source}/repeat',json={
        'product_name':'Iranian Dates','quantity':100,'currency':'USD',
        'agreed_unit_price':3.0,'incoterm':'CIF','payment_terms':'TBD',
        'factory_share':280,'approval_confirmed':False
    })
    assert r.status_code==400
    assert r.json()['detail']=='human_approval_required'


def test_invalid_repeat_window_is_clamped_to_one_day(monkeypatch, tmp_path):
    from datetime import datetime, timezone
    from types import SimpleNamespace
    import app.main as main_module

    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'repeat_window.db')
    monkeypatch.setattr(main_module, 'settings', SimpleNamespace(repeat_protection_days=-10))
    db.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db.init_db()
    c = TestClient(app)
    lid = _lead()
    _move_to_negotiation(c, lid)
    response = c.post(f'/crm/leads/{lid}/deal', json={
        'product_name':'Iranian Dates','unit':'kg','quantity':100,
        'currency':'USD','agreed_unit_price':3,'incoterm':'CIF',
        'payment_terms':'TBD','factory_share':100,'network_commission':10,
        'approval_confirmed':True
    })
    assert response.status_code == 200
    deal = c.get(f"/crm/deals/{response.json()['deal_id']}").json()
    deadline = datetime.fromisoformat(deal['repeat_until'].replace('Z', '+00:00'))
    assert deadline > datetime.now(timezone.utc)


def test_repeat_deal_rejects_different_buyer(monkeypatch, tmp_path):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'repeat_wrong_buyer.db')
    db.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db.init_db()
    c = TestClient(app)
    lid = _lead()
    _move_to_negotiation(c, lid)
    won = c.post(f'/crm/leads/{lid}/deal', json={
        'product_name':'Iranian Dates','unit':'kg','quantity':1000,
        'currency':'USD','agreed_unit_price':3,'incoterm':'CIF',
        'payment_terms':'TBD','factory_share':2800,'network_commission':200,
        'approval_confirmed':True
    })
    assert won.status_code == 200
    source_id = won.json()['deal_id']
    repeat = c.post(f'/crm/deals/{source_id}/repeat', json={
        'product_name':'Iranian Dates','unit':'kg','quantity':100,
        'currency':'USD','agreed_unit_price':3,'incoterm':'CIF',
        'payment_terms':'TBD','factory_share':280,'buyer_company':'Unrelated Buyer Ltd',
        'approval_confirmed':True
    })
    assert repeat.status_code == 409
    assert repeat.json()['detail']['policy']['identity_match'] is False
    assert len(db.list_deals(lead_id=lid)) == 1
