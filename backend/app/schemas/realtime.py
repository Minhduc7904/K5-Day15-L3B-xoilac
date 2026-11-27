from pydantic import BaseModel


class SocketTicketOut(BaseModel):
    ticket: str
    expires_in: int  # giây
