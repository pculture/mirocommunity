class Tier(object):
    def __init__(self, tier_name):
        self.tier_name = tier_name

    def videos_limit(self):
        data = {'free': 500,
                'plus': 1000,
                'premium': 5000,
                'executive': 25000}
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

    def permit_custom_template(self):
        data = {'executive': True}
        default = False
        return data.get(self.tier_name, default)

    def dollar_cost(self):
        data = {'free': 0,
                'plus': 15,
                'premium': 35,
                'executive': 75}
        return data[self.tier_name]
