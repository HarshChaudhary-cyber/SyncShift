import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.time_block import TimeBlock
from app.models.class_workspace import ClassEvent, ClassInvitation

client = TestClient(app)

@pytest.fixture(autouse=True)
def university_scope():
    global institution_id
    from app.models import Institution
    with SessionLocal() as db:
        inst=Institution(name='Class tests',code=uuid.uuid4().hex[:12]);db.add(inst);db.commit();institution_id=inst.id

def account():
    email = f"class-{uuid.uuid4().hex}@example.com"
    response = client.post('/api/v1/auth/register', json={'email':email,'password':'Password123!'})
    assert response.status_code == 200, response.text
    data = response.json()['data']
    from app.models import InstitutionMembership
    with SessionLocal() as db:
        db.add(InstitutionMembership(institution_id=institution_id,user_id=data['user_id'],role='student',status='active'));db.commit()
    return {'Authorization': 'Bearer '+data['token']}, data['user_id'], email

def create(headers, name='Design studio'):
    from datetime import date
    from app.models import InstitutionMembership, Department, AcademicCourse, AcademicTerm, AcademicSection, FacultyProfile, SectionFacultyAssignment
    user_id=client.get('/api/v1/auth/me',headers=headers).json()['data']['user_id']
    with SessionLocal() as db:
        m=db.query(InstitutionMembership).filter_by(user_id=user_id,institution_id=institution_id).one();m.role='professor'
        dept=Department(institution_id=institution_id,name='Subject',code=uuid.uuid4().hex[:8]);db.add(dept);db.flush()
        course=AcademicCourse(institution_id=institution_id,department_id=dept.id,code=uuid.uuid4().hex[:8],name=name);db.add(course);db.flush()
        term=AcademicTerm(institution_id=institution_id,name='Term',academic_year='2026',start_date=date(2026,1,1),end_date=date(2026,12,31));db.add(term);db.flush()
        section=AcademicSection(institution_id=institution_id,course_id=course.id,academic_term_id=term.id,section_code='A');db.add(section);db.flush()
        profile=db.query(FacultyProfile).filter_by(user_id=user_id,institution_id=institution_id).first()
        if not profile:
            profile=FacultyProfile(institution_id=institution_id,user_id=user_id,status='active');db.add(profile);db.flush()
        db.add(SectionFacultyAssignment(institution_id=institution_id,section_id=section.id,faculty_id=profile.id,role='instructor'));db.commit();course_id=course.id
    response = client.post('/api/v1/classes', headers=headers, json={'name':name,'institution_id':institution_id,'course_id':course_id})
    assert response.status_code == 201, response.text
    return response.json()['data']

EVENT = {'title':'Design seminar', 'event_date':'2026-10-05', 'start_time':'10:00','end_time':'11:00','location':'Studio 2'}

def test_dual_roles_codes_cannot_elevate_and_cross_workspace_access():
    a, _, _ = account(); b, _, _ = account(); outsider, _, _ = account()
    first, second = create(a), create(b,'Writing workshop')
    for headers, workspace in [(a,second),(b,first)]:
        rejected = client.post('/api/v1/classes/join',headers=headers,json={'code':workspace['join_code'],'role':'instructor'})
        assert rejected.status_code == 422
        joined = client.post('/api/v1/classes/join',headers=headers,json={'code':workspace['join_code']})
        assert joined.json()['data']['role'] == 'learner'
    roles = {row['id']:row['role'] for row in client.get('/api/v1/classes',headers=a).json()['data']}
    assert roles[first['id']] == 'instructor' and roles[second['id']] == 'learner'
    for path, payload in [('events',EVENT),('announcements',{'title':'Hi','body':'Text'}),('invitations',{'email':'new@example.com','role':'instructor'})]:
        assert client.post(f"/api/v1/classes/{first['id']}/{path}",headers=b,json=payload).status_code == 403
    assert client.get(f"/api/v1/classes/{first['id']}",headers=outsider).status_code == 404
    other_event = client.post(f"/api/v1/classes/{second['id']}/events",headers=b,json=EVENT).json()['data']
    assert client.post(f"/api/v1/classes/{first['id']}/events/{other_event['id']}/publish",headers=a).status_code == 404

def test_publication_is_read_through_private_conflicts_and_drafts_remain_private():
    teacher, teacher_id, teacher_email = account(); learner, learner_id, _ = account()
    workspace = create(teacher)
    class_id = workspace['id']
    client.post('/api/v1/classes/join',headers=learner,json={'code':workspace['join_code']})
    private = client.post('/api/v1/blocks',headers=learner,json={'type':'shift','title':'PRIVATE_JOB_SECRET','day_of_week':1,'start_time':'10:30','end_time':'12:00','effective_from':'2026-10-01'}).json()['data']
    event = client.post(f'/api/v1/classes/{class_id}/events',headers=teacher,json=EVENT).json()['data']
    assert client.get(f'/api/v1/classes/{class_id}',headers=learner).json()['data']['events'] == []
    event_path=f"/api/v1/classes/{class_id}/events/{event['id']}"
    assert client.post(event_path+'/publish',headers=learner).status_code == 403
    assert client.post(event_path+'/publish',headers=teacher).status_code == 200
    assert client.post(event_path+'/publish',headers=teacher).status_code == 200
    week = client.get('/api/v1/week?start=2026-10-05',headers=learner).json()['data']
    shared = [b for b in week['blocks'] if b.get('class_id')==class_id]
    assert len(shared)==1 and week['conflicts']
    assert shared[0]['source']=='shared_class'
    assert client.patch(f"/api/v1/blocks/{shared[0]['id']}",headers=learner,json={'start_time':'15:00'}).status_code == 403
    assert client.get(f"/api/v1/blocks/{private['id']}",headers=teacher).status_code == 404
    for endpoint in [f'/api/v1/classes/{class_id}','/api/v1/privacy/export','/api/v1/analytics/week','/api/v1/week?start=2026-10-05']:
        assert 'PRIVATE_JOB_SECRET' not in client.get(endpoint,headers=teacher).text
    from app.services.assistant_tools import tool_get_my_schedule
    from app.dependencies import CurrentUser
    with SessionLocal() as db:
        assert 'PRIVATE_JOB_SECRET' not in str(tool_get_my_schedule(db,CurrentUser(user_id=teacher_id,email=teacher_email)))
        assert db.query(TimeBlock).filter_by(user_id=learner_id).count()==1
        assert db.query(ClassEvent).filter_by(class_id=class_id).count()==1
    edited={**EVENT,'start_time':'14:00','end_time':'15:00'}
    client.patch(event_path,headers=teacher,json=edited)
    view = client.get(f'/api/v1/classes/{class_id}',headers=learner).json()['data']['events'][0]
    assert view['start_time']=='10:00' and 'pending' not in view
    client.post(event_path+'/publish',headers=teacher)
    week = client.get('/api/v1/week?start=2026-10-05',headers=learner).json()['data']
    assert len([b for b in week['blocks'] if b.get('class_id')==class_id])==1
    assert not week['conflicts']
    assert client.get('/api/v1/notifications',headers=learner).status_code==200
    client.delete(event_path,headers=teacher)
    assert not [b for b in client.get('/api/v1/week?start=2026-10-05',headers=learner).json()['data']['blocks'] if b.get('class_id')==class_id]

def test_learner_invitation_bound_to_email_single_use_and_removal():
    owner, owner_id, _=account(); invited, invited_id, email=account(); wrong, _, _=account()
    workspace=create(owner); class_id=workspace['id']
    response=client.post(f'/api/v1/classes/{class_id}/invitations',headers=owner,json={'email':email,'role':'learner'})
    token=response.json()['data']['token']
    with SessionLocal() as db:
        assert token not in str(db.query(ClassInvitation).filter_by(class_id=class_id).first().__dict__)
    assert client.post('/api/v1/classes/invitations/accept',headers=wrong,json={'token':token}).status_code==403
    assert client.post('/api/v1/classes/invitations/accept',headers=invited,json={'token':token}).json()['data']['role']=='learner'
    assert client.post('/api/v1/classes/invitations/accept',headers=invited,json={'token':token}).status_code==403
    assert client.post(f'/api/v1/classes/{class_id}/events',headers=invited,json=EVENT).status_code==403
    assert client.delete(f'/api/v1/classes/{class_id}/members/{invited_id}',headers=owner).status_code==200
    assert client.get(f'/api/v1/classes/{class_id}',headers=invited).status_code==404
    assert client.post('/api/v1/classes/join',headers=invited,json={'code':workspace['join_code']}).status_code==403
    assert client.delete(f'/api/v1/classes/{class_id}/members/{owner_id}',headers=owner).status_code==409

def test_existing_academic_enrollments_and_faculty_resolve_without_copying():
    from app.models import Institution, InstitutionMembership, Department, AcademicTerm, AcademicCourse, AcademicSection, SectionEnrollment, FacultyProfile, SectionFacultyAssignment
    from datetime import date
    faculty, faculty_id, _=account(); learner, learner_id, _=account()
    with SessionLocal() as db:
        inst=Institution(name='Compatibility university',code=uuid.uuid4().hex[:10]); db.add(inst); db.flush()
        db.add(InstitutionMembership(institution_id=inst.id,user_id=faculty_id,role='faculty',status='active'))
        db.add(InstitutionMembership(institution_id=inst.id,user_id=learner_id,role='student',status='active'))
        dept=Department(institution_id=inst.id,name='Design',code='DES');db.add(dept);db.flush()
        term=AcademicTerm(institution_id=inst.id,name='Fall',academic_year='2026-2027',start_date=date(2026,9,1),end_date=date(2026,12,31));db.add(term);db.flush()
        course=AcademicCourse(institution_id=inst.id,department_id=dept.id,code='DES1',name='Design');db.add(course);db.flush()
        section=AcademicSection(institution_id=inst.id,course_id=course.id,academic_term_id=term.id,section_code='A');db.add(section);db.flush()
        enrollment=SectionEnrollment(institution_id=inst.id,section_id=section.id,student_id=learner_id,status='active');db.add(enrollment)
        profile=FacultyProfile(institution_id=inst.id,user_id=faculty_id,status='active');db.add(profile);db.flush()
        db.add(SectionFacultyAssignment(institution_id=inst.id,section_id=section.id,faculty_id=profile.id));db.commit();enrollment_id=enrollment.id
    teaching=client.get('/api/v1/classes',headers=faculty).json()['data'];learning=client.get('/api/v1/classes',headers=learner).json()['data']
    assert teaching[0]['id']==learning[0]['id']
    assert teaching[0]['role']=='instructor' and learning[0]['role']=='learner'
    with SessionLocal() as db:
        db.get(SectionEnrollment,enrollment_id).status='dropped';db.commit()
    assert client.get('/api/v1/classes',headers=learner).json()['data']==[]
