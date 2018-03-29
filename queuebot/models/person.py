from sqlalchemy import Column, Integer, String
from queuebot.queuebotalchemy import Base


class PersonModel(Base):
    __tablename__ = 'people'

    id = Column(Integer, primary_key=True)

    SparkId = Column(String(256))
    DisplayName = Column(String(64), nullable=False)
