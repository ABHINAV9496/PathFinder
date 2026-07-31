from fastapi import Header, HTTPException

from coverletter.config import SERVICE_KEY


async def verify_service_key(x_service_key: str = Header(...)):
    if not SERVICE_KEY:
        return True
    if x_service_key != SERVICE_KEY:
        raise HTTPException(status_code=401, detail="Invalid service key")
    return True
