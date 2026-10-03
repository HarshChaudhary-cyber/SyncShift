"""Exercise real authorization, publication, progress, sharing, and tenant boundaries."""
import uuid
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import Institution, InstitutionMembership, Department, AcademicCourse, AcademicTerm, AcademicSection, FacultyProfile, SectionFacultyAssignment, SectionEnrollment
from app.models.class_workspace import ClassWorkspace, ClassEvent
from app.models.academic_experience import AcademicInvitation
from app.services.class_workspaces import ensure_legacy_workspaces

client=TestClient(app)


def account():
    email=f'{uuid.uuid4().hex}@example.edu'
    response=client.post('/api/v1/auth/register',json={'email':email,'password':'Password123!'})
    assert response.status_code==200,response.text
    d=response.json()['data']
    return {'Authorization':'Bearer '+d['token']},d['user_id'],email


@pytest.fixture
def university():
    admin=account();prof=account();student=account();other=account()
    with SessionLocal() as db:
        inst=Institution(name='Test university',code=uuid.uuid4().hex[:12],email_domain='example.edu');db.add(inst);db.flush()
        for acc,role in [(admin,'super_admin'),(prof,'professor'),(student,'student'),(other,'student')]:
            db.add(InstitutionMembership(institution_id=inst.id,user_id=acc[1],role=role,status='active'))
        dep=Department(institution_id=inst.id,name='Science',code='SCI');db.add(dep);db.flush()
        course=AcademicCourse(institution_id=inst.id,department_id=dep.id,name='Physics',code='PHY',credits=4);db.add(course);db.flush()
        term=AcademicTerm(institution_id=inst.id,name='Term',academic_year='2026',start_date=date.today()-timedelta(days=30),end_date=date.today()+timedelta(days=60));db.add(term);db.flush()
        sec=AcademicSection(institution_id=inst.id,course_id=course.id,academic_term_id=term.id,section_code='A');db.add(sec);db.flush()
        faculty=FacultyProfile(institution_id=inst.id,user_id=prof[1],department_id=dep.id,employee_code='PRIVATE_STAFF_ID',title='Professor',status='active');db.add(faculty);db.flush()
        db.add(SectionFacultyAssignment(institution_id=inst.id,section_id=sec.id,faculty_id=faculty.id,role='primary_instructor'))
        db.add(SectionEnrollment(institution_id=inst.id,section_id=sec.id,student_id=student[1],status='active'))
        db.flush();ensure_legacy_workspaces(db);db.flush()
        w=db.query(ClassWorkspace).filter_by(section_id=sec.id).one();db.commit()
        return {'admin':admin,'prof':prof,'student':student,'other':other,'id':inst.id,'course':course.id,'class':w.id,'section':sec.id}


def event(university, day=None):
    day=day or date.today()-timedelta(days=1)
    data={'title':'Physics lecture','event_date':str(day),'start_time':'10:00','end_time':'11:00','location':'Science 1'}
    p=f"/api/v1/classes/{university['class']}/events"
    r=client.post(p,headers=university['prof'][0],json=data);assert r.status_code==201,r.text
    eid=r.json()['data']['id']
    r=client.post(f'{p}/{eid}/publish',headers=university['prof'][0]);assert r.status_code==200,r.text
    return eid,data


def test_public_signup_and_student_cannot_elevate(university):
    u=university;h=u['student'][0]
    forged=client.post('/api/v1/auth/register',json={'email':'forged@example.edu','password':'Password123!','role':'super_admin'})
    assert forged.status_code==200 and not forged.json()['data'].get('institution_role')
    assert client.post('/api/v1/institutions',headers=h,json={'name':'Forged','code':'FORGED'}).status_code==403
    assert client.post('/api/v1/classes',headers=h,json={'name':'Forged','institution_id':u['id'],'course_id':u['course']}).status_code==403
    assert client.patch('/api/v1/students/me',headers=h,json={'student_number':'FORGED'}).status_code==403
    assert client.post('/api/v1/students/me/enrollments',headers=h,json={'section_id':u['section']}).status_code==403
    assert client.get(f"/api/v1/academic-admin/{u['id']}/users",headers=h).status_code==403
    assert client.patch(f"/api/v1/academic-admin/{u['id']}/users/{u['student'][1]}",headers=h,json={'role':'super_admin','status':'active'}).status_code==403


def test_official_event_readonly_private_tasks_and_draft_publication(university):
    u=university;eid,e=event(u);student=u['student'][0];prof=u['prof'][0]
    path=f"/api/v1/classes/{u['class']}/events/{eid}"
    for method,suffix,payload in [('patch','',e),('post','/publish',None),('delete','',None)]:
        r=client.request(method,path+suffix,headers=student,json=payload);assert r.status_code==403,r.text
    private=client.post('/api/v1/blocks',headers=student,json={'type':'shift','title':'PRIVATE_STUDENT_SECRET','day_of_week':1,'start_time':'12:00','end_time':'13:00'}).json()['data']
    assert client.get(f"/api/v1/blocks/{private['id']}",headers=u['admin'][0]).status_code==404
    for h in (prof,u['admin'][0]):
        for path2 in (f"/api/v1/classes/{u['class']}",'/api/v1/privacy/export','/api/v1/academic/teaching'):
            assert 'PRIVATE_STUDENT_SECRET' not in client.get(path2,headers=h).text
    assert client.patch(path,headers=prof,json={**e,'start_time':'14:00','end_time':'15:00'}).status_code==200
    assert client.get(f"/api/v1/classes/{u['class']}",headers=student).json()['data']['events'][0]['start_time']=='10:00'
    assert client.post(path+'/publish',headers=prof).status_code==200
    week=client.get('/api/v1/week?start='+e['event_date'],headers=student).json()['data']
    blocks=[b for b in week['blocks'] if b.get('class_id')==u['class']]
    assert len(blocks)==1 and blocks[0]['start_time']=='14:00'
    assert client.patch(f"/api/v1/blocks/{blocks[0]['id']}",headers=student,json={'start_time':'16:00'}).status_code==403


def test_scoped_professor_and_revocation(university):
    u=university
    response=client.post('/api/v1/classes',headers=u['prof'][0],json={'name':'Lab','institution_id':u['id'],'course_id':u['course']})
    assert response.status_code==201,response.text
    assert client.post('/api/v1/classes',headers=u['prof'][0],json={'name':'Outside','institution_id':u['id']+99999,'course_id':u['course']}).status_code==403
    assert client.post(f"/api/v1/classes/{u['class']}/invitations",headers=u['prof'][0],json={'email':u['other'][2],'role':'instructor'}).status_code==403
    r=client.post(f"/api/v1/academic-admin/{u['id']}/assignments",headers=u['admin'][0],json={'user_id':u['prof'][1],'section_id':u['section'],'active':False})
    assert r.status_code==200,r.text
    assert client.post(f"/api/v1/classes/{u['class']}/events",headers=u['prof'][0],json={'title':'X','event_date':str(date.today()),'start_time':'09:00','end_time':'10:00'}).status_code==404


def test_completion_not_inferred_and_reschedule_is_unique(university):
    u=university;eid,e=event(u);p=f"/api/v1/academic/classes/{u['class']}"
    assert client.get(p,headers=u['student'][0]).json()['data']['progress']['delivered_lectures']==0
    body={'event_key':f'event:{eid}','event_date':e['event_date'],'status':'delivered'}
    assert client.post(p+'/records',headers=u['student'][0],json=body).status_code==403
    for _ in range(2):
        r=client.post(p+'/records',headers=u['prof'][0],json=body);assert r.status_code==200,r.text
        assert r.json()['data']['progress']['delivered_hours']==1
    body.update(status='rescheduled',replacement={**e,'start_time':'12:00','end_time':'13:00'})
    r=client.post(p+'/records',headers=u['prof'][0],json=body);assert r.status_code==200,r.text
    assert client.post(p+'/records',headers=u['prof'][0],json=body).status_code==409
    week=client.get('/api/v1/week?start='+e['event_date'],headers=u['student'][0]).json()['data']
    assert len([b for b in week['blocks'] if b.get('class_id')==u['class']])==1


def test_selected_audience_private_default_and_stop_sharing(university):
    u=university;day=str(date.today());body={'title':'PRIVATE_APPOINTMENT','event_date':day,'start_time':'16:00','end_time':'17:00','location':'','class_ids':[]}
    second=client.post('/api/v1/classes',headers=u['prof'][0],json={'name':'Second audience','institution_id':u['id'],'course_id':u['course']}).json()['data']
    assert client.post('/api/v1/classes/join',headers=u['other'][0],json={'code':second['join_code']}).status_code==200
    r=client.post('/api/v1/academic/appointments',headers=u['prof'][0],json=body);assert r.status_code==200,r.text
    aid=r.json()['data']['id'];path=f'/api/v1/academic/appointments/{aid}'
    week='/api/v1/week?start='+day
    assert body['title'] not in client.get(week,headers=u['student'][0]).text


    assert client.put(path,headers=u['other'][0],json=body).status_code==404
    body.update(share_with_students=True,class_ids=[u['class']])
    assert client.put(path,headers=u['prof'][0],json=body).status_code==200
    assert body['title'] in client.get(week,headers=u['student'][0]).text
    assert body['title'] not in client.get(week,headers=u['other'][0]).text
    assert client.get('/api/v1/academic/appointments',headers=u['admin'][0]).json()['data']==[]
    body['share_with_students']=False
    assert client.put(path,headers=u['prof'][0],json=body).status_code==200
    assert body['title'] not in client.get(week,headers=u['student'][0]).text


def test_professional_profile_visibility_and_invitation_lifecycle(university):
    u=university
    r=client.patch('/api/v1/academic/profile/me',headers=u['prof'][0],json={'introduction':'Physics lecturer','professional_phone':'PUBLIC_WORK_PHONE'})
    assert r.status_code==200,r.text
    profile=client.get(f"/api/v1/academic/profile/{u['prof'][1]}",headers=u['student'][0]);assert profile.status_code==200,profile.text
    assert 'PUBLIC_WORK_PHONE' in profile.text and 'PRIVATE_STAFF_ID' not in profile.text
    assert client.get(f"/api/v1/academic/profile/{u['student'][1]}",headers=u['admin'][0]).status_code==404
    outsider=account()
    assert client.get(f"/api/v1/academic/profile/{u['prof'][1]}",headers=outsider[0]).status_code==404
    assert client.patch('/api/v1/academic/profile/me',headers=u['student'][0],json={'role':'professor'}).status_code==422
    r=client.post(f"/api/v1/academic-admin/{u['id']}/invitations",headers=u['admin'][0],json={'email':outsider[2],'role':'professor'});assert r.status_code==201,r.text
    token=r.json()['data']['token']
    with SessionLocal() as db:
        assert token not in str(db.query(AcademicInvitation).filter_by(email=outsider[2]).one().__dict__)
    assert client.post('/api/v1/academic-admin/accept',headers=u['other'][0],json={'token':token}).status_code==403
    assert client.post('/api/v1/academic-admin/accept',headers=outsider[0],json={'token':token}).status_code==200
    assert client.post('/api/v1/academic-admin/accept',headers=outsider[0],json={'token':token}).status_code==403
    assert client.patch(f"/api/v1/academic-admin/{u['id']}/users/{u['admin'][1]}",headers=u['admin'][0],json={'role':'student','status':'active'}).status_code==409


def test_both_planner_roles_treat_official_time_as_fixed(university):
    from app.services.smart_planner.context import ScheduleContextBuilder
    u=university;_,e=event(u,date.today()+timedelta(days=1))
    with SessionLocal() as db:
        for acc in (u['prof'],u['student']):
            context=ScheduleContextBuilder.build(acc[1],date.fromisoformat(e['event_date']),db)
            assert any(x.title=='Physics lecture' and x.is_fixed for x in context.events)


def test_official_conflicts_and_demoted_professor(university):
    u=university;_,e=event(u)
    p=f"/api/v1/classes/{u['class']}/events"
    r=client.post(p,headers=u['prof'][0],json={**e,'title':'Conflicting lecture'})
    assert client.post(f"{p}/{r.json()['data']['id']}/publish",headers=u['prof'][0]).status_code==409
    assert client.patch(f"/api/v1/academic-admin/{u['id']}/users/{u['prof'][1]}",headers=u['admin'][0],json={'role':'student','status':'active'}).status_code==200
    assert client.post(p,headers=u['prof'][0],json=e).status_code==404


def test_calendar_and_teaching_timezone_conversion(university):
    from app.models.user import User
    from app.store import get_occurrences_for_range
    u=university;eid,e=event(u,date(2026,10,5))
    with SessionLocal() as db:
        db.get(User,u['prof'][1]).timezone='Asia/Kolkata'
        db.get(User,u['student'][1]).timezone='Asia/Kolkata'
        db.commit()
        blocks=get_occurrences_for_range(u['student'][1],date(2026,10,5),date(2026,10,5),db=db)
        lecture=next(b for b in blocks if b.id==-(1_000_000_000+eid))
        assert lecture.start_time=='14:30' and lecture.end_time=='15:30'
    view=client.get('/api/v1/academic/teaching',headers=u['prof'][0]).json()['data']
    assert view['timezone']=='Asia/Kolkata'
