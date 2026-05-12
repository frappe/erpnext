from django.urls import get_script_prefix, resolve


def get_breadcrumbs(url, request=None):
    """
    Given a url returns a list of breadcrumbs, which are each a
    tuple of (name, url).
    """
    from rest_framework.reverse import preserve_builtin_query_params
    from rest_framework.views import APIView

    def breadcrumbs_recursive(url, breadcrumbs_list, prefix, seen):
        """
        Add tuples of (name, url) to the breadcrumbs list,
        progressively chomping off parts of the url.
        """
        try:
            (view, unused_args, unused_kwargs) = resolve(url)
        except Exception:
            pass
        else:
            # Check if this is a REST framework view,
            # and if so add it to the breadcrumbs
            cls = getattr(view, 'cls', None)
            initkwargs = getattr(view, 'initkwargs', {})
            if cls is not None and issubclass(cls, APIView):
                # Don't list the same view twice in a row.
                # Probably an optional trailing slash.
                if not seen or seen[-1] != view:
                    c = cls(**initkwargs)
                    name = c.get_view_name()
                    insert_url = preserve_builtin_query_params(prefix + url, request)
                    breadcrumbs_list.insert(0, (name, insert_url))
                    seen.append(view)

        if url == '':
            # All done
            return breadcrumbs_list

        elif url.endswith('/'):
            # Drop trailing slash off the end and continue to try to
            # resolve more breadcrumbs
            url = url.rstrip('/')
            return breadcrumbs_recursive(url, breadcrumbs_list, prefix, seen)

        # Drop trailing non-slash off the end and continue to try to
        # resolve more breadcrumbs
        url = url[:url.rfind('/') + 1]
        return breadcrumbs_recursive(url, breadcrumbs_list, prefix, seen)

    prefix = get_script_prefix().rstrip('/')
    url = url[len(prefix):]
    return breadcrumbs_recursive(url, [], prefix, [])
