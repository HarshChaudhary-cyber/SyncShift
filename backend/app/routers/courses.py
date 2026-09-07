from fastapi import APIRouter, Depends, Path

from app.dependencies import CurrentUser, get_current_user
from app.schemas.common import DataResponse, DeletedData
from app.schemas.course import CourseCreate, CourseOut, CourseUpdate

router = APIRouter(prefix="/courses", tags=["Courses"])

# In-memory store for courses
MOCK_COURSES = [
    {"id": 1, "user_id": 1, "code": "CS101", "name": "Introduction to Computer Science", "color": "#2563eb"},
    {"id": 2, "user_id": 1, "code": "MATH220", "name": "Linear Algebra", "color": "#7c3aed"},
    {"id": 3, "user_id": 1, "code": "PHYS150", "name": "Physics Mechanics Lab", "color": "#059669"},
]


@router.get("", response_model=DataResponse[list[CourseOut]])
def list_courses(current_user: CurrentUser = Depends(get_current_user)):
    """
    List all academic courses for the authenticated student.
    """
    courses = [
        CourseOut(id=c["id"], code=c["code"], name=c["name"], color=c["color"])
        for c in MOCK_COURSES
        if c.get("user_id", 1) == current_user.user_id
    ]
    return DataResponse(data=courses)


@router.post("", response_model=DataResponse[CourseOut])
def create_course(
    body: CourseCreate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Register a new academic course.
    """
    new_id = max([c["id"] for c in MOCK_COURSES], default=0) + 1
    new_course = {
        "id": new_id,
        "user_id": current_user.user_id,
        "code": body.code,
        "name": body.name,
        "color": body.color,
    }
    MOCK_COURSES.append(new_course)
    created = CourseOut(
        id=new_id,
        code=body.code,
        name=body.name,
        color=body.color,
    )
    return DataResponse(data=created)


@router.patch("/{course_id}", response_model=DataResponse[CourseOut])
def update_course(
    body: CourseUpdate,
    course_id: int = Path(..., description="ID of the course to update"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Update course code, name, or color tags.
    """
    for c in MOCK_COURSES:
        if c["id"] == course_id and c.get("user_id", 1) == current_user.user_id:
            if body.code is not None:
                c["code"] = body.code
            if body.name is not None:
                c["name"] = body.name
            if body.color is not None:
                c["color"] = body.color
            return DataResponse(
                data=CourseOut(
                    id=course_id,
                    code=c["code"],
                    name=c["name"],
                    color=c["color"],
                )
            )

    updated = CourseOut(
        id=course_id,
        code=body.code or "CS101",
        name=body.name or "Course",
        color=body.color or "#2563eb",
    )
    return DataResponse(data=updated)


@router.delete("/{course_id}", response_model=DataResponse[DeletedData])
def delete_course(
    course_id: int = Path(..., description="ID of the course to delete"),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Delete a course by ID.
    """
    global MOCK_COURSES
    MOCK_COURSES = [
        c for c in MOCK_COURSES
        if not (c["id"] == course_id and c.get("user_id", 1) == current_user.user_id)
    ]
    return DataResponse(data=DeletedData(deleted=True))

