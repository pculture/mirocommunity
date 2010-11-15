class Tier(object):
    def __init__(self, tier_name):
        self.tier_name = tier_name

    def videos_limit(self):
        data = {'free': 500,
                'plus': 1000,
                'premium': 5000}
        return data[self.tier_name]

    def admins_limit(self):
        data = {'free': 1,
                'plus': 5}
        default = None
        return data.get(self.tier_name, default)

    def permit_custom_css(self):
        data = {'free': False}
        default = True
        return data.get(self.tier_name, default)

                    
