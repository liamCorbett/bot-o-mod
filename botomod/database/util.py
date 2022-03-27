def get_or_add(session, model, key, **properties):
    instance = session.query(model).get(key)
    if instance:
        return instance
    else:
        instance = model(**properties)
        session.add(instance)
        session.flush()
        return instance


def get_or_append(*, session, model, key, append_to, by_rel, properties):
    """Gets instance of model; or creates and appends a new one if none found

    Args:
        session: the SQLAlchemy database session
        model: the model to search in, or instantiate
        key: the primary key to search for
        append_to: a list of parent instances to add new child to
        by_rel: the relationship to append to
        properties: a dict of properties to instantiate 

    Returns:
        An instance of child_model
    """
    instance = session.query(model).get(key)
    if instance:
        return instance
    else:
        instance = model(**properties)
        for parent in append_to:
            getattr(parent, by_rel).append(instance)
        return instance