from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user
from app.models.course import Course
from app.schemas.common import DataResponse, DeletedData
from app.schemas.course import CourseCreate, CourseOut, CourseUpdate

router = APIRouter(prefix="/courses", tags=["Courses"])

# Deprecated in-memory fallback maintained for backwards compatibility
MOCK_COURSES: list[dict] = []


@router.get("", response_model=DataResponse[list[CourseOut]])
def list_courses(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all academic courses for the authenticated student from the database.
    Strictly isolated by current_user.user_id.
    """
    courses = (
        db.query(Course)
        .filter(Course.user_id == current_user.user_id)
        .order_by(Course.code)
        .all()
    )
    return DataResponse(
        data=[
            CourseOut(id=c.id, code=c.code, name=c.name, color=c.color)
            for c in courses
        ]
    )


@router.post("", response_model=DataResponse[CourseOut], status_code=status.HTTP_201_CREATED)
def create_course(
    body: CourseCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Register a new academic course persisted in the database.
    """
    new_course = Course(
        user_id=current_user.user_id,
        code=body.code,
        name=body.name,
        color=body.color,
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)

    return DataResponse(
        data=CourseOut(
            id=new_course.id,
            code=new_course.code,
            name=new_course.name,
            color=new_course.color,
        )
    )


@router.patch("/{course_id}", response_model=DataResponse[CourseOut])
def update_course(
    body: CourseUpdate,
    course_id: int = Path(..., description="ID of the course to update"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update course code, name, or color tags in the database.
    """
    course = (
        db.query(Course)
        .filter(Course.id == course_id, Course.user_id == current_user.user_id)
        .first()
    )
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found",
        )

    if body.code is not None:
        course.code = body.code
    if body.name is not None:
        course.name = body.name
    if body.color is not None:
        course.color = body.color

    db.commit()
    db.refresh(course)

    return DataResponse(
        data=CourseOut(
            id=course.id,
            code=course.code,
            name=course.name,
            color=course.color,
        )
    )


@router.delete("/{course_id}", response_model=DataResponse[DeletedData])
def delete_course(
    course_id: int = Path(..., description="ID of the course to delete"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a course by ID for the authenticated student.
    """
    course = (
        db.query(Course)
        .filter(Course.id == course_id, Course.user_id == current_user.user_id)
        .first()
    )
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course with id {course_id} not found",
        )

    db.delete(course)
    db.commit()
    return DataResponse(data=DeletedData(deleted=True))
