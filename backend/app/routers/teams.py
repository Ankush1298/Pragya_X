"""Team workspaces with PostgreSQL membership enforcement and contribution evidence."""
import uuid
from datetime import datetime
from typing import Optional, Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from psycopg.types.json import Jsonb
from ..database.connection import get_db, atomic_write
from ..database.repository import Repository
from ..services.auth_service import get_current_user
from ..services.notification_service import notify
from ..services import curriculum

router = APIRouter(prefix='/teams', tags=['Collaboration'])


def ident(prefix):
    return f'{prefix}_{uuid.uuid4().hex[:20]}'


def query(sql, params=(), many=False):
    with get_db() as conn:
        cur=conn.cursor();cur.execute(sql,params)
        return cur.fetchall() if many else cur.fetchone()


def member(team_id, user, owner=False):
    team=query('SELECT t.* FROM teams t JOIN team_members m ON m.team_id=t.id WHERE t.id=? AND m.user_id=?',(team_id,user['id']))
    if not team:
        raise HTTPException(404,'Team not found')
    if owner and team['owner_id'] != user['id']:
        raise HTTPException(403,'Only the team owner can perform this action')
    return team


def execute(sql,params):
    with get_db() as conn:
        conn.cursor().execute(sql,params)


def contribution(team_id,user,action,evidence):
    execute('INSERT INTO team_contributions(id,team_id,user_id,action,evidence) VALUES (?,?,?,?,?)',
            (ident('con'),team_id,user['id'],action,Jsonb(evidence)))


class NewTeam(BaseModel):
    name: str = Field(min_length=2,max_length=80)
    project_id: str


class Invite(BaseModel):
    email: str = Field(max_length=200)


class Respond(BaseModel):
    accept: bool


class Task(BaseModel):
    title: str = Field(min_length=2,max_length=200)
    assignee_id: Optional[str]=None
    deadline: Optional[datetime]=None


class TaskUpdate(BaseModel):
    status: Literal['todo','doing','done']


class Message(BaseModel):
    body: str = Field(min_length=1,max_length=4000)


class Role(BaseModel):
    project_role: str = Field(min_length=2,max_length=60)


class Submission(BaseModel):
    text: str = Field(min_length=80,max_length=20000)


@router.get('')
def list_teams(user:dict=Depends(get_current_user)):
    return {'teams':query('SELECT t.* FROM teams t JOIN team_members m ON m.team_id=t.id WHERE m.user_id=? ORDER BY t.created_at DESC',(user['id'],),True),
            'invitations':query("SELECT i.*,t.name FROM team_invitations i JOIN teams t ON t.id=i.team_id WHERE i.user_id=? AND i.status='pending'",(user['id'],),True)}


@router.post('',status_code=201)
@atomic_write
def create_team(payload:NewTeam,user:dict=Depends(get_current_user)):
    if not any(p['id']==payload.project_id for p in curriculum.PROJECTS):
        raise HTTPException(400,'Choose a curated project')
    tid=ident('team')
    execute('INSERT INTO teams(id,name,owner_id,project_id) VALUES (?,?,?,?)',(tid,payload.name.strip(),user['id'],payload.project_id))
    execute("INSERT INTO team_members(team_id,user_id,project_role) VALUES (?,?,'Project lead')",(tid,user['id']))
    return query('SELECT * FROM teams WHERE id=?',(tid,))


@router.get('/{team_id}')
def get_team(team_id:str,user:dict=Depends(get_current_user)):
    team=member(team_id,user)
    return {**team,'members':query('SELECT m.*,u.name FROM team_members m JOIN users u ON u.id=m.user_id WHERE team_id=?',(team_id,),True),
            'tasks':query('SELECT * FROM team_tasks WHERE team_id=? ORDER BY updated_at',(team_id,),True),
            'messages':query('SELECT m.*,u.name FROM team_messages m JOIN users u ON u.id=m.user_id WHERE team_id=? ORDER BY m.created_at LIMIT 200',(team_id,),True),
            'contributions':query('SELECT c.*,u.name FROM team_contributions c JOIN users u ON u.id=c.user_id WHERE team_id=? ORDER BY c.created_at DESC LIMIT 200',(team_id,),True)}


@router.post('/{team_id}/invitations')
@atomic_write
def invite(team_id:str,payload:Invite,user:dict=Depends(get_current_user)):
    team=member(team_id,user,True);target=Repository.get_user_by_email(payload.email)
    if not target:raise HTTPException(404,'Student not found')
    if query('SELECT 1 FROM team_members WHERE team_id=? AND user_id=?',(team_id,target['id'])):
        raise HTTPException(409,'Student is already a team member')
    row=query("INSERT INTO team_invitations(id,team_id,user_id) VALUES (?,?,?) ON CONFLICT(team_id,user_id) DO UPDATE SET status='pending' RETURNING *",(ident('tinv'),team_id,target['id']))
    notify(target['id'],'project','Team invitation',f"You were invited to {team['name']}",'/teams',f"team-invite:{row['id']}")
    return row


@router.post('/invitations/{invitation_id}/respond')
@atomic_write
def respond(invitation_id:str,payload:Respond,user:dict=Depends(get_current_user)):
    inv=query("SELECT * FROM team_invitations WHERE id=? AND user_id=? AND status='pending'",(invitation_id,user['id']))
    if not inv:raise HTTPException(404,'Pending invitation not found')
    if payload.accept:
        if query('SELECT COUNT(*) AS n FROM team_members WHERE team_id=?',(inv['team_id'],))['n']>=5:
            raise HTTPException(409,'Teams can have at most five students')
        execute('INSERT INTO team_members(team_id,user_id) VALUES (?,?) ON CONFLICT DO NOTHING',(inv['team_id'],user['id']))
    execute('UPDATE team_invitations SET status=? WHERE id=?',('accepted' if payload.accept else 'declined',invitation_id))
    return {'team_id':inv['team_id'],'accepted':payload.accept}


@router.put('/{team_id}/members/{user_id}/role')
@atomic_write
def assign_role(team_id:str,user_id:str,payload:Role,user:dict=Depends(get_current_user)):
    member(team_id,user,True)
    row=query('UPDATE team_members SET project_role=? WHERE team_id=? AND user_id=? RETURNING *',(payload.project_role,team_id,user_id))
    if not row:raise HTTPException(404,'Member not found')
    return row


@router.post('/{team_id}/tasks')
@atomic_write
def new_task(team_id:str,payload:Task,user:dict=Depends(get_current_user)):
    member(team_id,user)
    if payload.assignee_id and not query('SELECT 1 FROM team_members WHERE team_id=? AND user_id=?',(team_id,payload.assignee_id)):
        raise HTTPException(400,'Assignee must belong to the team')
    row=query('INSERT INTO team_tasks(id,team_id,title,assignee_id,deadline,created_by) VALUES (?,?,?,?,?,?) RETURNING *',
              (ident('task'),team_id,payload.title,payload.assignee_id,payload.deadline,user['id']))
    contribution(team_id,user,'task_created',{'task_id':row['id'],'title':row['title']})
    return row


@router.patch('/{team_id}/tasks/{task_id}')
@atomic_write
def update_task(team_id:str,task_id:str,payload:TaskUpdate,user:dict=Depends(get_current_user)):
    team=member(team_id,user);task=query('SELECT * FROM team_tasks WHERE id=? AND team_id=?',(task_id,team_id))
    if not task:raise HTTPException(404,'Task not found')
    if task['assignee_id'] and user['id'] not in (task['assignee_id'],team['owner_id']):
        raise HTTPException(403,'Only the assignee or project lead can update this task')
    row=query('UPDATE team_tasks SET status=?,updated_at=now() WHERE id=? RETURNING *',(payload.status,task_id))
    contribution(team_id,user,'task_status',{'task_id':task_id,'status':payload.status})
    return row


@router.post('/{team_id}/messages')
@atomic_write
def message(team_id:str,payload:Message,user:dict=Depends(get_current_user)):
    member(team_id,user)
    if not payload.body.strip():raise HTTPException(400,'Message cannot be blank')
    return query('INSERT INTO team_messages(id,team_id,user_id,body) VALUES (?,?,?,?) RETURNING *',(ident('tmsg'),team_id,user['id'],payload.body.strip()))


@router.post('/{team_id}/submit')
@atomic_write
def submit(team_id:str,payload:Submission,user:dict=Depends(get_current_user)):
    member(team_id,user,True)
    if query('SELECT COUNT(*) AS n FROM team_members WHERE team_id=?',(team_id,))['n']<4:
        raise HTTPException(400,'Invite at least four students before submitting a team project')
    tasks=query('SELECT * FROM team_tasks WHERE team_id=?',(team_id,),True)
    if not tasks or any(t['status']!='done' for t in tasks):
        raise HTTPException(400,'Complete all shared tasks before submitting')
    execute('UPDATE teams SET submission=?,submitted_at=now() WHERE id=?',(payload.text,team_id))
    contribution(team_id,user,'project_submitted',{'text':payload.text,'evidence_type':'team-submitted, not independently evaluated'})
    return {'status':'submitted','evidence_type':'team-submitted, not independently evaluated'}
