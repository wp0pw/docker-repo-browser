from flask import Flask, render_template
import json
import requests
from collections import OrderedDict

app = Flask(__name__, static_folder='res')

FOREST = OrderedDict()


class Action:

    def __init__(self, href, link, name):
        self.href = href
        self.link = link
        self.name = name


class Image:

    def __init__(self, name, href):
        self.href = href
        self.name = name


class Tag:
    def __init__(self, name, href):
        self.name = name
        self.href = href


def get_common_actions():
    actions = list()
    actions.append(Action('/', 'Home', 'Home'))
    actions.append(Action('/list/', 'Images', 'List Images'))
    actions.append(Action('/tree/', 'Tree view', 'Tree view'))
    return actions

NAMESPEC = 'library'
REPOADDRESS = 'xxx'


@app.route("/image/<image_name>/del", methods=['POST'])
def del_image(image_name):
    global FOREST
    resp = requests.delete('{}/v1/repositories/{}/{}/'.format(REPOADDRESS, NAMESPEC, image_name))

    actions = get_common_actions()

    FOREST = OrderedDict()

    return render_template('infoonly.html', info=json.dumps(resp.json(), indent=2), actions=actions)

@app.route("/image/<image_name>", methods=['GET'])
def img_detail(image_name):
    resp = requests.get('{}/v1/repositories/{}/{}/tags'.format(REPOADDRESS, NAMESPEC, image_name))

    actions = get_common_actions()
    subactions = list()
    subactions.append(Action('/image/{}'.format(image_name), image_name, image_name))

    tags = list()
    for tag_name, tag_id in resp.json().items():
        tags.append(Tag(tag_name, "/image/{}/{}".format(image_name, tag_name)))

    tags.sort(key=lambda x: x.name, reverse=True)

    return render_template('image_page.html', info=json.dumps(resp.json(), indent=2), parent_item_name=image_name,
                           items=tags, actions=actions, subactions=subactions)

@app.route("/image/<image_name>/<tag_name>", methods=['GET'])
def tag_detail(image_name, tag_name):
    resp = requests.get('{}/v1/repositories/{}/{}/tags/{}'.format(REPOADDRESS, NAMESPEC, image_name, tag_name))

    actions = get_common_actions()
    subactions = list()
    subactions.append(Action('/image/{}'.format(image_name), image_name, image_name))
    subactions.append(Action('/image/{}/{}'.format(image_name, tag_name), tag_name, tag_name))

    show_tag_id = resp.text

    resp = requests.get('{}/v1/images/{}/json'.format(REPOADDRESS, show_tag_id.strip('"')))

    more_info = 'To pull use: docker pull {}/{}:{}'.format(REPOADDRESS.strip('http://'), image_name, tag_name)

    return render_template('infoonly.html', info=json.dumps(resp.json(), indent=2), actions=actions,
                           more_info=more_info, subactions=subactions)

@app.route("/list/", methods=['GET'])
def img_list():
    resp = requests.get('{}/v1/search'.format(REPOADDRESS))

    actions = get_common_actions()

    images = list()
    for image in resp.json()["results"]:
        images.append(Image(image["name"].lstrip(NAMESPEC).lstrip('/'),
                            "/image" + image["name"].lstrip(NAMESPEC)))
    images.sort(key=lambda x: x.name)

    return render_template('itemlist.html', info=json.dumps(resp.json(), indent=2), itemtype='Images',
                           items=images, actions=actions)


@app.route("/tree/", methods=['GET'])
def tree():
    actions = get_common_actions()

    def find_leaf(l_id, search_domain=FOREST):
        for leaf in search_domain.values():
            if leaf.id == l_id:
                return leaf
            find_leaf(l_id, leaf.childs)
        return None

    def merge_childs(leaf, existing_leaf):
        for key, val in leaf.childs.items():
            if key in existing_leaf.childs.keys():
                if val.name:
                    existing_leaf.childs[key].name = val.name
                merge_childs(val, existing_leaf.childs[key])
            else:
                existing_leaf.childs[key] = val
                val.parent = existing_leaf

    def fit_into_forest(leaf):
        if not len(FOREST):
            # if empty forest attach and return leaf
            FOREST[leaf.id] = leaf
            return leaf
        else:
            # detach childs from FOREST
            for key, child in leaf.childs.items():
                if key in FOREST.keys():
                    del FOREST[key]
                    child.parent = leaf

            existing_leaf = find_leaf(leaf.id)
            if existing_leaf:
                # if we're an existing leaf then add new all childs and return our existing leaf ref
                merge_childs(leaf, existing_leaf)
                return existing_leaf
            else:
                # if we're new leaf add us to the FOREST
                FOREST[leaf.id] = leaf
                return leaf

    class Leaf:

        def __init__(self, n_id, name, child):
            self.parent = None
            self.id = n_id
            self.childs = OrderedDict()
            if child:
                self.childs[child.id] = child
            self.name = name
            self.shown = False

        @property
        def child_list(self):
            return list(self.childs.values())

    def add_parent(leaf):
        parent_resp = requests.get('{}/v1/images/{}/json'.format(REPOADDRESS, leaf.id))

        if "parent" not in parent_resp.json():
            return
        new_leaf = Leaf(parent_resp.json()["parent"], '', leaf)
        new_leaf = fit_into_forest(new_leaf)
        add_parent(new_leaf)

    resp = requests.get('{}/v1/search'.format(REPOADDRESS))

    forest_of_trees = ""
    if True:

        for repo in resp.json()["results"]:
            tags_resp = requests.get('{}/v1/repositories/{}/tags'.format(REPOADDRESS, repo["name"]))
            if tags_resp.status_code != 200:
                continue

            for tag_name, tag_id in tags_resp.json().items():
                # this is all leaves
                tag_image_resp = requests.get('{}/v1/images/{}/json'.format(REPOADDRESS, tag_id.strip('"')))
                print('LEAF->', tag_name, repo["name"], tag_image_resp.json()["id"])
                new_leaf = Leaf(tag_image_resp.json()["id"], repo["name"]+":"+tag_name, None)
                if find_leaf(new_leaf.id):
                    continue
                new_leaf = fit_into_forest(new_leaf)
                add_parent(new_leaf)

    resutls = list(FOREST.values())
    resutls.sort(key=lambda x: x.id)
    return render_template('tree.html', info=forest_of_trees, items=resutls, actions=actions)


@app.route("/", methods=['GET'])
def index():

    resp = requests.get('{}/v1/_ping'.format(REPOADDRESS))

    actions = get_common_actions()

    return render_template('infoonly.html', info=json.dumps(resp.json(), indent=2), actions=actions)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081, debug=True)

