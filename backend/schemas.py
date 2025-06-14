from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# ✅ 기존: 대량 삭제용 요청 스키마
class BulkDeleteRequest(BaseModel):
    user_id: str
    logo_ids: List[int]

# ✅ 추가: 즐겨찾기용 기본 스키마
class FavoriteBase(BaseModel):
    logo_id: int

# ✅ 추가: 즐겨찾기 생성 요청용
class FavoriteCreate(FavoriteBase):
    pass

# ✅ 추가: 즐겨찾기 응답용
class FavoriteOut(FavoriteBase):
    id: int
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True

class LogoOut(BaseModel):
    id: int
    user_id: str
    logo_path: str
    s3_url: str
    brand_name: str
    logo_style: str
    colors: str
    created_at: datetime
    s3_uploaded: bool
    s3_uploaded_at: Optional[datetime]
    is_favorite: bool  # ✅ 추가

    class Config:
        from_attributes = True  # ✅ pydantic v2 호환