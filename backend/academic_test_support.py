"""Explicit operator provisioning for tests; never patches production authorization."""
import jwt
import httpx
from sqlalchemy import func
from app.config import settings
from app.database import SessionLocal
from app.models.institution import Institution, InstitutionMembership
from app.schemas.institution import InstitutionOut


def bootstrap_institution(*, headers, json):
    payload = jwt.decode(headers['Authorization'].split(' ',1)[1],settings.JWT_SECRET,algorithms=['HS256'])
    with SessionLocal() as db:
        if db.query(Institution).filter(func.lower(Institution.code)==json['code'].lower()).first():
            return httpx.Response(409,json={'error':{'code':'institution_code_exists'}})
        inst=Institution(**json)
        db.add(inst);db.flush()
        db.add(InstitutionMembership(user_id=int(payload['sub']),institution_id=inst.id,role='super_admin',status='active'))
        db.commit()
        return httpx.Response(201,json={'data':InstitutionOut.model_validate(inst).model_dump(mode='json')})


def administrator_enroll(*,headers,json):
    return _student_assignment(headers,json=json)


def administrator_drop(enrollment_id,*,headers):
    return _student_assignment(headers,enrollment_id=enrollment_id)


def _student_assignment(headers,json=None,enrollment_id=None):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.dependencies import create_access_token
    from app.models.user import User
    payload=jwt.decode(headers['Authorization'].split(' ',1)[1],settings.JWT_SECRET,algorithms=['HS256'])
    student_id=int(payload['sub'])
    with SessionLocal() as db:
        m=db.query(InstitutionMembership).filter_by(user_id=student_id,status='active',deleted_at=None).first()
        admin=db.query(InstitutionMembership).filter_by(institution_id=m.institution_id,role='super_admin',status='active',deleted_at=None).first()
        owner=db.get(User,admin.user_id)
        authorized={'Authorization':'Bearer '+create_access_token(owner.id,owner.email)}
        path=f'/api/v1/academic-admin/{m.institution_id}/students/{student_id}/enrollments'
    client=TestClient(app)
    return client.delete(f'{path}/{enrollment_id}',headers=authorized) if enrollment_id else client.post(path,headers=authorized,json=json)
