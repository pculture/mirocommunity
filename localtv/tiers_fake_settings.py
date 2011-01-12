class BooleanRepresentingUploadTemplatePermission(object):
    def __nonzero__(self):
        import localtv.tiers
        default = False # By default, we say that custom themes are disabled.

        tier = localtv.tiers.Tier.get()
        if tier is None:
            return default
        return tier.permit_custom_css()
        
    def __init__(self):
        pass

