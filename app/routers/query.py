from fastapi import APIRouter

router = APIRouter()

@router.get("/query-test")
def test_query():
    return {"msg": "query working"}