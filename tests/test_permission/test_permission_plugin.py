from sqlalchemy import Column, Integer
from sqlalchemy.ext.declarative import declarative_base

from combojsonapi.permission.permission_plugin import get_columns_for_query

Base = declarative_base()


class MyModel(Base):
    __tablename__ = "model"
    # we need a PK
    id = Column(Integer, primary_key=True)
    # creating a column
    model_type = Column(Integer)
    # for no reason creating a column
    # which takes the same name
    model_entity = Column("model_type", Integer)


def test_get_columns_for_query():
    """
    Test if the model with some names
    overlapping is processed without errors
    :return:
    """

    res = get_columns_for_query(MyModel)
    # expecting columns names
    assert res == ["id", "model_entity"]
