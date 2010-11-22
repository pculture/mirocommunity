## These "CHOICES" are used in the SiteLocation model.
## They describe the different account types.
CHOICES = [
    ('free', 'Free account'),
    ('plus', 'Plus account'),
    ('premium', 'Premium account'),
    ('executive', 'Executive account')]

class Tier(object):
    def __init__(self, tier_name):
        self.tier_name = tier_name

    def videos_limit(self):
        special_cases = {'free': 500,
                'plus': 1000,
                'premium': 5000,
                'executive': 25000}
        return special_cases[self.tier_name]

    def admins_limit(self):
        special_cases = {'free': 1,
                'plus': 5}
        default = None
        return special_cases.get(self.tier_name, default)

    def permit_custom_css(self):
        special_cases = {'free': False}
        default = True
        return special_cases.get(self.tier_name, default)

    def permit_custom_template(self):
        special_cases = {'executive': True}
        default = False
        return special_cases.get(self.tier_name, default)

    def dollar_cost(self):
        special_cases = {'free': 0,
                'plus': 15,
                'premium': 35,
                'executive': 75}
        return special_cases[self.tier_name]
