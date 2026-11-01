""" rdf-array: the LIST shape expression in ShExJ (rdf-array/docs/array-syntax.md §7): a ListShape whose expression is a
Member, a ListEachOf (ordered) or a ListOneOf, each with min and max as on triple expressions, and its ShExC. """
import json
from io import StringIO

from pyjsg.jsglib.loader import loads, is_valid

from ShExJSG import ShExJ, ShExC

XSD = "http://www.w3.org/2001/XMLSchema#"
EX = "http://a.example/"


def iri(local: str) -> ShExJ.IRIREF:
    return ShExJ.IRIREF(EX + local)


def dt(local: str) -> ShExJ.NodeConstraint:
    return ShExJ.NodeConstraint(datatype=ShExJ.IRIREF(XSD + local))


def member(se, mn=None, mx=None) -> ShExJ.Member:
    return ShExJ.Member(shapeExpr=se, min=mn, max=mx)


def schema_of(*shapes) -> ShExJ.Schema:
    schema = ShExJ.Schema(shapes=list(shapes))
    schema['@context'] = "http://www.w3.org/ns/shex.jsonld"
    return schema


def valid(schema: ShExJ.Schema) -> ShExJ.Schema:
    log = StringIO()
    reloaded = loads(schema._as_json, ShExJ)
    assert is_valid(reloaded, log), log.getvalue()
    return reloaded


def shexc(schema: ShExJ.Schema) -> str:
    return ' '.join(str(ShExC(schema)).split())


def test_the_objects_and_their_json():
    ls = ShExJ.ListShape(id=iri("S"), expression=ShExJ.ListEachOf(expressions=[
        member(dt("integer"), 3, 3),
        ShExJ.ListOneOf(expressions=[member(EX + "T"), member(ShExJ.Shape())], min=0, max=-1)]))
    assert json.loads(schema_of(ls)._as_json)["shapes"][0] == {
        "type": "ListShape", "id": EX + "S", "expression": {"type": "ListEachOf", "expressions": [
            {"type": "Member", "shapeExpr": {"type": "NodeConstraint", "datatype": XSD + "integer"}, "min": 3, "max": 3},
            {"type": "ListOneOf", "expressions": [{"type": "Member", "shapeExpr": EX + "T"},
                                                  {"type": "Member", "shapeExpr": {"type": "Shape"}}],
             "min": 0, "max": -1}]}}
    back = valid(schema_of(ls)).shapes[0]
    assert isinstance(back, ShExJ.ListShape) and isinstance(back.expression, ShExJ.ListEachOf)
    assert isinstance(back.expression.expressions[1], ShExJ.ListOneOf)
    assert not hasattr(ShExJ, "Collection"), "the Collection strawman is gone"


def test_list_shape_wherever_a_shape_expression_may_appear():
    ints = ShExJ.ListShape(expression=member(dt("integer"), 0, -1))
    valid(schema_of(ShExJ.ShapeNot(id=iri("N"), shapeExpr=ints),
                    ShExJ.ShapeAnd(id=iri("A"), shapeExprs=[ints, ShExJ.Shape()]),
                    ShExJ.Shape(id=iri("T"), expression=ShExJ.TripleConstraint(predicate=iri("p"), valueExpr=ints)),
                    ShExJ.ListShape(id=iri("M"), expression=member(ints, 2, 2)),
                    ShExJ.ShapeDecl(id=iri("D"), shapeExpr=ints)))


def test_the_writer():
    # one Member with a cardinality over an inline shape atom: the short form, LIST card x
    assert shexc(schema_of(ShExJ.ListShape(id=iri("S"), expression=member(ShExJ.ListShape(
        expression=member(dt("integer"), 3, 3)), 2, 2)))) == f"<{EX}S> LIST {{2}} LIST {{3}} <{XSD}integer>"
    assert shexc(schema_of(ShExJ.ListShape(id=iri("S"), expression=member(EX + "T", 1, -1)))) == f"<{EX}S> LIST + @<{EX}T>"
    # otherwise the regular expression form, LIST ( ... )
    assert shexc(schema_of(ShExJ.ListShape(id=iri("S"), expression=member(dt("integer"))))) == f"<{EX}S> LIST ( <{XSD}integer> )"
    assert shexc(schema_of(ShExJ.ListShape(id=iri("S"), expression=member(ShExJ.ShapeNot(shapeExpr=dt("integer")), 1, -1)))) \
        == f"<{EX}S> LIST ( NOT ( <{XSD}integer> ) + )"
    assert shexc(schema_of(ShExJ.ListShape(id=iri("S"), expression=ShExJ.ListEachOf(
        expressions=[member(dt("string")), member(dt("integer"))])))) == f"<{EX}S> LIST ( <{XSD}string> ; <{XSD}integer> )"
    assert shexc(schema_of(ShExJ.ListShape(id=iri("S"), expression=ShExJ.ListEachOf(
        expressions=[member(dt("string")), member(dt("integer"))], min=0, max=-1)))) \
        == f"<{EX}S> LIST ( ( <{XSD}string> ; <{XSD}integer> )* )"
    assert shexc(schema_of(ShExJ.ListShape(id=iri("S"), expression=ShExJ.ListOneOf(
        expressions=[member(dt("integer")), ShExJ.ListEachOf(expressions=[member(dt("string")), member(dt("integer"))])],
        min=1, max=-1)))) == f"<{EX}S> LIST ( ( <{XSD}integer> | ( <{XSD}string> ; <{XSD}integer> ) )+ )"
    # as a triple constraint's value
    text = shexc(schema_of(ShExJ.Shape(id=iri("S"), expression=ShExJ.TripleConstraint(
        predicate=iri("p"), valueExpr=ShExJ.ListShape(expression=member(EX + "T", 1, -1)), min=1, max=2))))
    assert f"<{EX}p> LIST + @<{EX}T>" in text
