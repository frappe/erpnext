from fastapi import Depends, HTTPException, status
from Goldfish.auth.jwt import get_current_user
from Goldfish.models.user import User

def has_permission(required_role: str):
    def check_permission(current_user = Depends(get_current_user)):
        if required_role not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return check_permission

def check_role(user: User, required_role: str):
    if required_role not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have the required permissions to perform this action"
        )