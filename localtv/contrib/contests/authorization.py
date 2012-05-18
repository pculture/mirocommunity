from tastypie.authorization import Authorization

class UserAuthorization(Authorization):
    """
    Checks ownership of an object via the object's user attribute.
    Allows all methods (reading/writing) for owners.
    """

    def apply_limits(self, request, object_list):
        """
        Limits objects returned to objects whose user matches the user on
        the request.
        """
        if hasattr(request, 'user') and request.user.is_authenticated():
            return object_list.filter(user=request.user)
        return object_list.none()