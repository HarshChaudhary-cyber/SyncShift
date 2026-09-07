from app.schemas.common import DataResponse, ErrorResponse, ErrorDetail, DeletedResponse, DeletedData
from app.schemas.auth import UserRegister, UserLogin, AuthResponseData, UserProfileData
from app.schemas.course import CourseCreate, CourseUpdate, CourseOut
from app.schemas.block import BlockCreate, BlockUpdate, BlockDuplicate, BlockOut
from app.schemas.conflict import ConflictItem, WeeklyTotals, ConflictsResponseData
from app.schemas.week import WeekViewData
from app.schemas.import_ics import (
    IcsPreviewItem,
    IcsUnmatchedItem,
    IcsPreviewResponseData,
    IcsConfirmBlock,
    IcsConfirmRequest,
    IcsConfirmResponseData,
)

__all__ = [
    "DataResponse",
    "ErrorResponse",
    "ErrorDetail",
    "DeletedResponse",
    "DeletedData",
    "UserRegister",
    "UserLogin",
    "AuthResponseData",
    "UserProfileData",
    "CourseCreate",
    "CourseUpdate",
    "CourseOut",
    "BlockCreate",
    "BlockUpdate",
    "BlockDuplicate",
    "BlockOut",
    "ConflictItem",
    "WeeklyTotals",
    "ConflictsResponseData",
    "WeekViewData",
    "IcsPreviewItem",
    "IcsUnmatchedItem",
    "IcsPreviewResponseData",
    "IcsConfirmBlock",
    "IcsConfirmRequest",
    "IcsConfirmResponseData",
]
