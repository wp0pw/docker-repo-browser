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

NAMESPACE = 'library'
REPOADDRESS = 'localhost'
REPO_FLAVOUR = 2


class EndpointProvider:

    @staticmethod
    def base_endpoint():
        if REPO_FLAVOUR == 1:
            return '{}/v1/_ping'.format(REPOADDRESS)
        elif REPO_FLAVOUR == 2:
            return '{}/v2/'.format(REPOADDRESS)

    @staticmethod
    def img_detail_endpoint(image_name):
        if REPO_FLAVOUR == 1:
            return '{}/v1/repositories/{}/{}/tags'.format(REPOADDRESS, NAMESPACE, image_name)
        elif REPO_FLAVOUR == 2:
            return '{}/v2/{}/tags/list'.format(REPOADDRESS, image_name)

    @staticmethod
    def tag_detail_endpoint(image_name, tag_name):
        if REPO_FLAVOUR == 1:
            return '{}/v1/repositories/{}/{}/tags/{}'.format(REPOADDRESS, NAMESPACE, image_name, tag_name)
        elif REPO_FLAVOUR == 2:
            return '{}/v2/{}/manifests/{}'.format(REPOADDRESS, image_name, tag_name)

    @staticmethod
    def tag_image_detail_endpoint(tag_id, image_name, tag_name):
        if REPO_FLAVOUR == 1:
            return '{}/v1/images/{}/json'.format(REPOADDRESS, NAMESPACE, tag_id)
        elif REPO_FLAVOUR == 2:
            return '{}/v2/{}/manifests/{}'.format(REPOADDRESS, image_name, tag_name)

    @staticmethod
    def image_list_endpoint():
        if REPO_FLAVOUR == 1:
            return '{}/v1/search'.format(REPOADDRESS)
        elif REPO_FLAVOUR == 2:
            return '{}/v2/_catalog'.format(REPOADDRESS)

    @staticmethod
    def delete_repo_endpoint(image_name):
        if REPO_FLAVOUR == 1:
            return '{}/v1/repositories/{}/{}/'.format(REPOADDRESS, NAMESPACE, image_name)
        elif REPO_FLAVOUR == 2:
            raise NotImplementedError()

    @staticmethod
    def delete_manifest_endpoint(image_name, manifest_digest):
        if REPO_FLAVOUR == 1:
            raise NotImplementedError()
        elif REPO_FLAVOUR == 2:
            return '{}/v2/{}/manifests/{}'.format(REPOADDRESS, image_name, manifest_digest)


@app.route("/image/<image_name>/del", methods=['POST'])
def del_image(image_name):
    global FOREST
    resp_info = {}
    if REPO_FLAVOUR == 1:
        resp = requests.delete(EndpointProvider.delete_repo_endpoint(image_name))
        resp_info = resp.json()

    elif REPO_FLAVOUR == 2:
        resp = requests.get(EndpointProvider.img_detail_endpoint(image_name))
        tags = ResponseParser.get_tags_from_img(resp, image_name)
        for tag in tags:
            header = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}
            resp = requests.get(EndpointProvider.tag_image_detail_endpoint("", image_name, tag.name),
                                headers=header)
            manifest_digest = resp.headers['Docker-Content-Digest']
            resp = requests.delete(EndpointProvider.delete_manifest_endpoint(image_name, manifest_digest))
            resp_info[tag.name] = 'DELETED' if resp.status_code == 202 else 'FAILED {}'.format(resp.status_code)

    actions = get_common_actions()
    subactions = list()
    subactions.append(Action('/image/{}'.format(image_name), image_name, image_name))
    FOREST = OrderedDict()

    return render_template('infoonly.html', info=json.dumps(resp_info, indent=2), actions=actions, subactions=subactions)

@app.route("/image/<image_name>/<tag_name>/del", methods=['POST'])
def del_tag(image_name, tag_name):
    global FOREST
    actions = get_common_actions()
    subactions = list()
    subactions.append(Action('/image/{}'.format(image_name), image_name, image_name))
    FOREST = OrderedDict()
    resp_info = {}

    header = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}
    resp = requests.get(EndpointProvider.tag_image_detail_endpoint("", image_name, tag_name),
                        headers=header)
    manifest_digest = resp.headers['Docker-Content-Digest']
    resp = requests.delete(EndpointProvider.delete_manifest_endpoint(image_name, manifest_digest))
    resp_info[tag_name] = 'DELETED' if resp.status_code == 202 else 'FAILED {}'.format(resp.status_code)

    return render_template('infoonly.html', info=json.dumps(resp_info, indent=2), actions=actions, subactions=subactions)

@app.route("/image/<image_name>", methods=['GET'])
def img_detail(image_name):
    resp = requests.get(EndpointProvider.img_detail_endpoint(image_name))

    actions = get_common_actions()
    subactions = list()
    subactions.append(Action('/image/{}'.format(image_name), image_name, image_name))

    tags = ResponseParser.get_tags_from_img(resp, image_name)

    return render_template('image_page.html', info=json.dumps(resp.json(), indent=2), parent_item_name=image_name,
                           items=tags, actions=actions, subactions=subactions)

@app.route("/image/<image_name>/<tag_name>", methods=['GET'])
def tag_detail(image_name, tag_name):
    resp = requests.get(EndpointProvider.tag_detail_endpoint(image_name, tag_name))

    actions = get_common_actions()
    subactions = list()
    subactions.append(Action('/image/{}'.format(image_name), image_name, image_name))
    subactions.append(Action('/image/{}/{}'.format(image_name, tag_name), tag_name, tag_name))

    show_tag_id = resp.text

    resp = requests.get(EndpointProvider.tag_image_detail_endpoint(show_tag_id.strip('"'), image_name, tag_name))
    more_info = 'To pull use: docker pull {}/{}:{}'.format(REPOADDRESS.strip('http://'), image_name, tag_name)

    return render_template('tag_info.html', info=json.dumps(resp.json(), indent=2), actions=actions,
                           more_info=more_info, subactions=subactions, v2_repo=REPO_FLAVOUR == 2)

@app.route("/list/", methods=['GET'])
def img_list():
    resp = requests.get(EndpointProvider.image_list_endpoint())

    actions = get_common_actions()

    images = ResponseParser.get_images_from_list(resp)

    return render_template('itemlist.html', info=json.dumps(resp.json(), indent=2), itemtype='Images',
                           items=images, actions=actions)


class ResponseParser:

    @staticmethod
    def get_images_from_list(resp):
        images = list()
        if REPO_FLAVOUR == 1:
            for image in resp.json()["results"]:
                images.append(Image(image["name"].lstrip(NAMESPACE).lstrip('/'),
                                    "/image" + image["name"].lstrip(NAMESPACE)))
            images.sort(key=lambda x: x.name)
            return images
        if REPO_FLAVOUR == 2:
            for image in resp.json()["repositories"]:
                images.append(Image(image,
                                    "/image" + '/' + image))
            images.sort(key=lambda x: x.name)
            return images

    @staticmethod
    def get_tags_from_img(resp, image_name):
        tags = list()
        if REPO_FLAVOUR == 1:
            for tag_name, tag_id in resp.json().items():
                tags.append(Tag(tag_name, "/image/{}/{}".format(image_name, tag_name)))

            tags.sort(key=lambda x: x.name, reverse=True)
            return tags
        if REPO_FLAVOUR == 2:
            print(resp.json())
            if resp.json()['tags']:
                for tag_name in resp.json()['tags']:
                    tags.append(Tag(tag_name, "/image/{}/{}".format(image_name, tag_name)))
            return tags


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
        if leaf.name and not existing_leaf.name:
            existing_leaf.name = leaf.name
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
                new_leaf = Leaf(tag_image_resp.json()["id"], repo["name"]+":"+tag_name, None)
                existing_leaf = find_leaf(new_leaf.id)
                if existing_leaf and existing_leaf.name == new_leaf.name:
                    continue
                new_leaf = fit_into_forest(new_leaf)
                add_parent(new_leaf)

    resutls = list(FOREST.values())
    resutls.sort(key=lambda x: x.id)
    return render_template('tree.html', info=forest_of_trees, items=resutls, actions=actions)


@app.route("/", methods=['GET'])
def index():
    global REPO_FLAVOUR

    resp = requests.get(EndpointProvider.base_endpoint())
    if resp.status_code == 404:
        REPO_FLAVOUR = 1
        resp = requests.get(EndpointProvider.base_endpoint())

    actions = get_common_actions()

    return render_template('infoonly.html', info=json.dumps(resp.json(), indent=2), actions=actions)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081, debug=True)

