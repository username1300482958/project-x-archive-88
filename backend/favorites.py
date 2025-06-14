from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db
from backend import models, schemas
from backend.auth_jwt_utils import get_current_user

router = APIRouter(prefix="/favorites", tags=["Favorites"])

# ✅ 즐겨찾기 추가
@router.post("/", response_model=schemas.FavoriteOut)
def add_favorite(
    favorite: schemas.FavoriteCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    user_id = user["sub"]

    print(f"🔥 즐겨찾기 추가 요청: user_id={user_id}, logo_id={favorite.logo_id}")

    user_exists = db.query(models.User).filter_by(id=user_id).first()
    if not user_exists:
        raise HTTPException(status_code=400, detail="해당 user_id가 users 테이블에 존재하지 않습니다.")

    existing = db.query(models.Favorite).filter_by(user_id=user_id, logo_id=favorite.logo_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="이미 즐겨찾기된 항목입니다.")
    
    favorite_count = db.query(models.Favorite).filter_by(user_id=user_id).count()
    if favorite_count >= 5:
        raise HTTPException(status_code=409, detail="즐겨찾기는 최대 5개까지만 가능합니다.")

    db_favorite = models.Favorite(user_id=user_id, logo_id=favorite.logo_id)
    db.add(db_favorite)
    db.commit()
    db.refresh(db_favorite)
    print("✅ 즐겨찾기 추가 완료:", db_favorite)
    return db_favorite

# ✅ 즐겨찾기 삭제
@router.delete("/by-logo/{logo_id}")
def remove_favorite_by_logo(
    logo_id: int = Path(..., title="Logo ID"),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    user_id = user["sub"]

    print(f"🔥 즐겨찾기 삭제 요청: user_id={user_id}, logo_id={logo_id}")
    favorite = db.query(models.Favorite).filter_by(user_id=user_id, logo_id=logo_id).first()
    if not favorite:
        raise HTTPException(status_code=404, detail="즐겨찾기 항목을 찾을 수 없습니다.")
    db.delete(favorite)
    db.commit()
    print("✅ 즐겨찾기 삭제 완료")
    return {"detail": "Favorite removed"}

# ✅ 즐겨찾기 전체 조회
@router.get("/", response_model=List[schemas.FavoriteOut])
def get_my_favorites(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    user_id = user["sub"]
    print(f"📦 즐겨찾기 목록 요청: user_id={user_id}")
    return db.query(models.Favorite).filter_by(user_id=user_id).all()