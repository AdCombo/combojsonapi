from marshmallow.base import FieldABC
from marshmallow.fields import Nested, Field
from marshmallow_jsonapi.fields import Relationship as GenericRelationship, BaseRelationship

from combojsonapi.utils import Relationship


class TestRelationship:
    def test_mro(self):
        assert Relationship.mro() == [Relationship,
                                      GenericRelationship,
                                      BaseRelationship,
                                      Nested,
                                      Field,
                                      FieldABC,
                                      object]
