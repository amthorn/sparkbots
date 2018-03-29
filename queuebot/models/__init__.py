from . import person

class ApiBase:
    @classmethod
    def _get(cls, primary_id):
        value = app.session.query(cls).filter(cls.id == primary_id).first()
        return value._dict() if value else None