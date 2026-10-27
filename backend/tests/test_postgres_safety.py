"""Real production repository concurrency, rollback and battle response security."""
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
import pytest
from backend.app.main import app
from backend.app.database.connection import get_db
from backend.app.database.competition_repository import CompetitionRepository as C
from backend.app.database.learning_repository import LearningRepository
from backend.tests.learning_helpers import register as register_email,new_chat,diagnostic,complete_first_mission

client=TestClient(app)


def register(client,name):
    headers,_=register_email(client,name)
    return headers,client.get('/api/auth/me',headers=headers).json()



def match():
    a,ua=register(client,'Alpha');b,ub=register(client,'Beta')
    invitation=client.post('/api/battles/invite',headers=a,json={'recipient_identifier':ub['email']}).json()['invitation']
    accept=client.post('/api/battles/invite/respond',headers=b,json={'invitation_id':invitation['id'],'accept':True})
    assert accept.status_code==200
    bid=accept.json()['battle_id']
    return a,ua,b,ub,bid,accept


def test_all_battle_mutation_reads_hide_answers():
    a,ua,b,ub,bid,accept=match()
    for response in [accept,client.post(f'/api/battles/{bid}/ready',headers=a),client.post(f'/api/battles/{bid}/ready',headers=b),client.get('/api/battles/my-battles',headers=a)]:
        for hidden in ['correct_option','explanation','questions_json','player_one_answers','player_two_answers']:
            assert hidden not in response.text
    outsider,_=register(client,'Outsider')
    assert client.get(f'/api/battles/{bid}',headers=outsider).status_code==400
    r=client.post(f'/api/battles/{bid}/submit',headers=a,json={'battle_id':bid,'answers':{'unknown':'A'}})
    assert r.status_code==400


def test_simultaneous_production_battle_submissions_complete_once():
    from backend.app.services.battle_service import BattleService
    a,ua,b,ub,bid,_=match()
    BattleService.set_player_ready(ua['id'],bid);BattleService.set_player_ready(ub['id'],bid)
    questions=C.get_battle_by_id(bid)['questions']
    correct={q['question_id']:q['correct_option'] for q in questions}
    wrong={q['question_id']:('A' if q['correct_option']!='A' else 'B') for q in questions}
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs=[pool.submit(BattleService.submit_battle_answers,ua['id'],bid,correct),pool.submit(BattleService.submit_battle_answers,ub['id'],bid,wrong)]
        results=[j.result() for j in jobs]
    assert all('error' not in r for r in results)
    battle=C.get_battle_by_id(bid)
    assert battle['status']=='COMPLETED' and battle['winner_id']==ua['id']
    assert C.get_battle_stats(ua['id'])['total_battles']==1
    xp=C.get_user_total_xp(ua['id'])
    assert 'error' in BattleService.submit_battle_answers(ua['id'],bid,correct)
    assert C.get_user_total_xp(ua['id'])==xp


def test_production_redemptions_cannot_overspend():
    _,user=register(client,'Rewards')
    C.record_xp_event(user['id'],'fund.'+user['id'],350,'Test funding','test','fund')
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:C.redeem_reward(user['id'],'rwd_pro_badge'),range(2)))
    assert sum('error' not in r for r in results)==1
    assert C.get_user_total_xp(user['id'])==0


def test_learning_transaction_rolls_back_progress_and_reward(monkeypatch):
    from backend.app.services.learning_service import LearningService
    from backend.app.services import curriculum
    h,user=register(client,'Rollback');chat=new_chat(client,h)
    diagnostic(client,h,chat['id'],'A')
    state=client.get('/api/learn/chats/'+chat['id'],headers=h).json()
    mid=next(m['id'] for m in state['roadmap']['modules'] if m['status']=='unlocked')
    client.get(f"/api/learn/chats/{chat['id']}/modules/{mid}",headers=h)
    answers={q['id']:q['answer'] for q in curriculum.get_module(mid)['questions']}
    def fail(*args,**kwargs):raise RuntimeError('injected ledger failure')
    monkeypatch.setattr(C,'record_xp_event',fail)
    with pytest.raises(RuntimeError,match='injected ledger failure'):
        LearningService.submit_practice(user,LearningService.get_owned_chat(user,chat['id']),mid,answers)
    assert mid not in LearningRepository.completed_module_ids(chat['id'])


def test_team_membership_capacity_tasks_and_contributions():
    from backend.app.services import curriculum
    h,owner=register(client,'Team owner')
    created=client.post('/api/teams',headers=h,json={'name':'Demo Learning Team','project_id':curriculum.PROJECTS[0]['id']})
    assert created.status_code==201,created.text
    tid=created.json()['id'];outsider,_=register(client,'Outsider')
    assert client.get('/api/teams/'+tid,headers=outsider).status_code==404
    assert client.post('/api/teams/'+tid+'/submit',headers=h,json={'text':'Evidence '*20}).status_code==400
    members=[]
    for i in range(5):
        mh,mu=register(client,f'Member {i}')
        invitation=client.post(f'/api/teams/{tid}/invitations',headers=h,json={'email':mu['email']}).json()
        response=client.post('/api/teams/invitations/'+invitation['id']+'/respond',headers=mh,json={'accept':True})
        assert response.status_code==(200 if i<4 else 409)
        members.append((mh,mu))
    task=client.post(f'/api/teams/{tid}/tasks',headers=h,json={'title':'Document experiment','assignee_id':members[0][1]['id']}).json()
    assert client.patch(f"/api/teams/{tid}/tasks/{task['id']}",headers=members[1][0],json={'status':'done'}).status_code==403
    assert client.patch(f"/api/teams/{tid}/tasks/{task['id']}",headers=members[0][0],json={'status':'done'}).status_code==200
    assert client.post(f'/api/teams/{tid}/messages',headers=members[0][0],json={'body':'Demo discussion'}).status_code==200
    assert client.post(f'/api/teams/{tid}/submit',headers=h,json={'text':'Our team prepared and reviewed the project deliverables and documented the results. '*3}).status_code==200
    state=client.get('/api/teams/'+tid,headers=h).json()
    assert len(state['members'])==5 and state['messages'][0]['body']=='Demo discussion'
    assert any(c['user_id']==members[0][1]['id'] and c['action']=='task_status' for c in state['contributions'])


def test_certificate_signature_binds_recipient_and_description():
    from backend.app.services.certificate_service import CertificateService
    _,user=register(client,'Signed Learner')
    c=CertificateService.issue_certificate(user['id'],user['name'],'ASSESSMENT','Demo achievement','Original description',{'assessment_id':'signature.test'})
    assert CertificateService.verify_certificate(c['verification_id'])['is_valid']
    with get_db() as conn:
        conn.cursor().execute('UPDATE certificates SET user_name=? WHERE verification_id=?',('Forged recipient',c['verification_id']))
    assert CertificateService.verify_certificate(c['verification_id'])['is_valid'] is False


def test_profile_update_requires_authentication_and_is_persisted():
    h,user=register(client,'Profile Learner')
    assert client.patch('/api/auth/profile',json={'name':'Changed'}).status_code==401
    assert client.patch('/api/auth/profile',headers=h,json={'name':'   '}).status_code==400
    assert client.patch('/api/auth/profile',headers=h,json={'name':'Updated Demo Name'}).status_code==200
    assert client.get('/api/auth/me',headers=h).json()['name']=='Updated Demo Name'


def test_platform_challenge_creation_requires_admin():
    h,_=register(client,'Ordinary Student')
    data={'title':'Unauthorized','topic':'Python','description':'Test','code_snippet':'print(1)','option_a':'1','option_b':'2','option_c':'3','option_d':'4','correct_option':'A','explanation':'One'}
    assert client.post('/api/challenges/create',headers=h,json=data).status_code==403


def test_hosted_competitions_hide_keys_register_and_conclude():
    from datetime import datetime,timedelta,timezone
    owner,ou=register(client,'Demo Organizer');student,su=register(client,'Demo Participant')
    org=client.post('/api/competitions/organizations',headers=owner,json={'name':'Demo Student Club','org_type':'STUDENT','description':'Local test club'}).json()['organization']
    now=datetime.now(timezone.utc)
    payload={'org_id':org['id'],'title':'Demo Hosted Quiz','description':'Server graded demo','start_time':(now-timedelta(hours=1)).isoformat(),'end_time':(now+timedelta(hours=1)).isoformat(),
             'questions':[{'question_text':'Which option is first?','option_a':'First','option_b':'Second','option_c':'Third','option_d':'Fourth','correct_option':'A','explanation':'A is first'}]}
    created=client.post('/api/competitions/create',headers=owner,json=payload)
    assert created.status_code==200,created.text
    cid=created.json()['competition']['id']
    detail=client.get('/api/competitions/'+cid,headers=student)
    listing=client.get('/api/competitions/list')
    for response in [detail,listing]:
        assert 'questions_json' not in response.text and 'correct_option' not in response.text and 'explanation' not in response.text
    assert detail.json()['registration']['user_id']==su['id']
    qid=detail.json()['questions'][0]['id']
    submitted=client.post(f'/api/competitions/{cid}/submit',headers=student,json={'answers':{qid:'A'},'time_taken_seconds':-999999})
    assert submitted.status_code==200,submitted.text
    assert submitted.json()['submission']['time_taken_seconds']>=0
    assert client.post(f'/api/competitions/{cid}/announce-winners',headers=owner).status_code==200
    assert client.get('/api/competitions/'+cid,headers=student).json()['status']=='COMPLETED'
    other,_=register(client,'Late Participant')
    assert client.post(f'/api/competitions/{cid}/submit',headers=other,json={'answers':{qid:'A'}}).status_code==400
    payload.update(title='Future demo quiz',start_time=(now+timedelta(hours=1)).isoformat(),end_time=(now+timedelta(hours=2)).isoformat())
    future=client.post('/api/competitions/create',headers=owner,json=payload).json()['competition']['id']
    public=next(c for c in client.get('/api/competitions/list').json() if c['id']==future)
    assert public['questions']==[] and 'questions_json' not in public
