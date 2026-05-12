"""
Helper function for returning the field information that is associated
with a model class. This includes returning all the forward and reverse
relationships and their associated metadata.

Usage: `get_field_info(model)` returns a `FieldInfo` instance.
"""
from collections import OrderedDict, namedtuple

FieldInfo = namedtuple('FieldResult', [
    'pk',  # Model field instance
    'fields',  # Dict of field name -> model field instance
    'forward_relations',  # Dict of field name -> RelationInfo
    'reverse_relations',  # Dict of field name -> RelationInfo
    'fields_and_pk',  # Shortcut for 'pk' + 'fields'
    'relations'  # Shortcut for 'forward_relations' + 'reverse_relations'
])

RelationInfo = namedtuple('RelationInfo', [
    'model_field',
    'related_model',
    'to_many',
    'to_field',
    'has_through_model',
    'reverse'
])


def get_field_info(model):
    """
    Given a model class, returns a `FieldInfo` instance, which is a
    `namedtuple`, containing metadata about the various field types on the model
    including information about their relationships.
    """
    opts = model._meta.concrete_model._meta

    pk = _get_pk(opts)
    fields = _get_fields(opts)
    forward_relations = _get_forward_relationships(opts)
    reverse_relations = _get_reverse_relationships(opts)
    fields_and_pk = _merge_fields_and_pk(pk, fields)
    relationships = _merge_relationships(forward_relations, reverse_relations)

    return FieldInfo(pk, fields, forward_relations, reverse_relations,
                     fields_and_pk, relationships)


def _get_pk(opts):
    pk = opts.pk
    rel = pk.remote_field

    while rel and rel.parent_link:
        # If model is a child via multi-table inheritance, use parent's pk.
        pk = pk.remote_field.model._meta.pk
        rel = pk.remote_field

    return pk


def _get_fields(opts):
    fields = OrderedDict()
    for field in [field for field in opts.fields if field.serialize and not field.remote_field]:
        fields[field.name] = field

    return fields


def _get_to_field(field):
    return getattr(field, 'to_fields', None) and field.to_fields[0]


def _get_forward_relationships(opts):
    """
    Returns an `OrderedDict` of field names to `RelationInfo`.
    """
    forward_relations = OrderedDict()
    for field in [field for field in opts.fields if field.serialize and field.remote_field]:
        forward_relations[field.name] = RelationInfo(
            model_field=field,
            related_model=field.remote_field.model,
            to_many=False,
            to_field=_get_to_field(field),
            has_through_model=False,
            reverse=False
        )

    # Deal with forward many-to-many relationships.
    for field in [field for field in opts.many_to_many if field.serialize]:
        forward_relations[field.name] = RelationInfo(
            model_field=field,
            related_model=field.remote_field.model,
            to_many=True,
            # manytomany do not have to_fields
            to_field=None,
            has_through_model=(
                not field.remote_field.through._meta.auto_created
            ),
            reverse=False
        )

    return forward_relations


def _get_reverse_relationships(opts):
    """
    Returns an `OrderedDict` of field names to `RelationInfo`.
    """
    reverse_relations = OrderedDict()
    all_related_objects = [r for r in opts.related_objects if not r.field.many_to_many]
    for relation in all_related_objects:
        accessor_name = relation.get_accessor_name()
        reverse_relations[accessor_name] = RelationInfo(
            model_field=None,
            related_model=relation.related_model,
            to_many=relation.field.remote_field.multiple,
            to_field=_get_to_field(relation.field),
            has_through_model=False,
            reverse=True
        )

    # Deal with reverse many-to-many relationships.
    all_related_many_to_many_objects = [r for r in opts.related_objects if r.field.many_to_many]
    for relation in all_related_many_to_many_objects:
        accessor_name = relation.get_accessor_name()
        reverse_relations[accessor_name] = RelationInfo(
            model_field=None,
            related_model=relation.related_model,
            to_many=True,
            # manytomany do not have to_fields
            to_field=None,
            has_through_model=(
                (getattr(relation.field.remote_field, 'through', None) is not None) and
                not relation.field.remote_field.through._meta.auto_created
            ),
            reverse=True
        )

    return reverse_relations


def _merge_fields_and_pk(pk, fields):
    fields_and_pk = OrderedDict()
    fields_and_pk['pk'] = pk
    fields_and_pk[pk.name] = pk
    fields_and_pk.update(fields)

    return fields_and_pk


def _merge_relationships(forward_relations, reverse_relations):
    return OrderedDict(
        list(forward_relations.items()) +
        list(reverse_relations.items())
    )


def is_abstract_model(model):
    """
    Given a model class, returns a boolean True if it is abstract and False if it is not.
    """
    return hasattr(model, '_meta') and hasattr(model._meta, 'abstract') and model._meta.abstract
