from fastapi import APIRouter, Query

from app.services import catalog_service

router = APIRouter()


@router.get("")
@router.get("/")
def list_catalog(
    skill: str | None = Query(default=None),
    level: str | None = Query(default=None),
    item_type: str | None = Query(default=None),
):
    items = catalog_service.load_catalog()
    if skill:
        key = skill.lower()
        items = [i for i in items if any(key in s.lower() for s in i.get("skills", []))]
    if level:
        items = [i for i in items if i.get("level") == level]
    if item_type:
        items = [i for i in items if i.get("type") == item_type]
    return {"items": items, "count": len(items)}
