class Image:

    def __init__(self, name, href):
        self.href = href
        self.name = name


class Tag:
    def __init__(self, name, href):
        self.name = name
        self.href = href


class API_CONSTANTS:

    NAMESPACE = 'library'