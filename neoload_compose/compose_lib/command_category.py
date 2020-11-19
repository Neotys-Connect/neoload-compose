class CommandCategory(object):

    def __init__(self, category):
        self.category = category

    def __call__(self, f):
        f.__dict__['category'] = self.category
        return f
