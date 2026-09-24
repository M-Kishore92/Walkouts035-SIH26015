"""Watersheds API — list, detail, and GeoJSON endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.db.session import get_db
from app.models.models import Watershed, District, User
from app.core.security import get_current_user

router = APIRouter()


@router.get("/")
async def list_watersheds(
    district_code: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    q = select(Watershed)
    if district_code:
        district = await db.scalar(select(District).where(District.code == district_code))
        if district:
            q = q.where(Watershed.district_id == district.id)
    q = q.limit(limit)
    ws = (await db.scalars(q)).all()
    return {
        "count": len(ws),
        "watersheds": [
            {"id": str(w.id), "watershed_code": w.watershed_code, "name": w.name, "area_ha": w.area_ha}
            for w in ws
        ],
    }


@router.get("/{watershed_code}")
async def get_watershed(
    watershed_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    w = await db.scalar(select(Watershed).where(Watershed.watershed_code == watershed_code))
    if not w:
        raise HTTPException(status_code=404, detail="Watershed not found")
    return {"id": str(w.id), "watershed_code": w.watershed_code, "name": w.name, "area_ha": w.area_ha}


@router.get("/{watershed_code}/geojson")
async def get_watershed_geojson(
    watershed_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(text("""
        SELECT ST_AsGeoJSON(geom::geometry)::json AS geojson
        FROM watersheds WHERE watershed_code = :code
    """), {"code": watershed_code})
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Watershed not found")
    return {"type": "Feature", "geometry": row.geojson, "properties": {"watershed_code": watershed_code}}
