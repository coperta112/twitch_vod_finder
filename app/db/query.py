from .session import get_db_session
from .models import Clip

def get_all_clips():
    session = get_db_session()
    clips = session.query(Clip).order_by(Clip.created_at.desc()).all()
    session.close()
    return clips
