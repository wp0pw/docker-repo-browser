import os
import json
import requests
import urllib.parse
from collections import OrderedDict

from flask import Flask, render_template, request, url_for
from werkzeug.serving import run_simple
from werkzeug.wsgi import DispatcherMiddleware

from api_providers import ResponseParser, EndpointProvider, RepoFlavour
from entities import Tag


class Action:

    def __init__(self, href, link, name):
        self.href = href
        self.link = link
        self.name = name


def get_common_actions():
    actions = list()
    actions.append(Action(url_for('index'), 'Home', 'Home'))
    actions.append(Action(url_for('img_list'), 'Images', 'List Images'))
    return actions

VERIFY_MODE = os.environ.get('SSL_CUSTOM_BUNDLE',  False if os.environ.get('INSECURE', False) else True)
REPOADDRESS = os.environ.get('REGISTRY')
REPO_HOST = os.environ.get('REPOHOST', '')
APPLICATION_ROOT = os.environ.get('ROOT_PATH', '')
DEBUG = True if os.environ.get('DEBUG', False) else False
REPO_FLAVOUR = RepoFlavour.V2
RESPONSE_PARSER = ResponseParser(REPO_FLAVOUR)
ENDPOINT_PROVIDER = EndpointProvider(REPO_FLAVOUR, REPOADDRESS)

app = Flask(__name__, static_folder='res')
app.config.from_object(__name__)


@app.route("/image/<path:image_name>/del", methods=['POST'])
def del_tags(image_name):
    resp_info = {}

    for posted_tag_tuple in request.form.items():
        tag = Tag(posted_tag_tuple[0], url_for('tag_detail',
                                               image_name=image_name,
                                               tag_name=posted_tag_tuple[0]))
        header = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}
        resp = requests.get(ENDPOINT_PROVIDER.tag_image_detail_endpoint("", image_name, tag.name),
                            headers=header, verify=VERIFY_MODE)
        manifest_digest = resp.headers['Docker-Content-Digest']
        resp = requests.delete(ENDPOINT_PROVIDER.delete_manifest_endpoint(image_name, manifest_digest), verify=VERIFY_MODE)
        resp_info[tag.name] = 'DELETED' if resp.status_code == 202 else 'FAILED {}'.format(resp.status_code)

    image_name = urllib.parse.unquote_plus(image_name)

    subactions = list()
    subactions.append(Action(url_for('img_detail', image_name=urllib.parse.quote_plus(image_name)), image_name, image_name))

    return render_template('infoonly.html',
                           info=json.dumps(resp_info, indent=2),
                           actions=get_common_actions(),
                           subactions=subactions)


@app.route("/image/<image_name>/<tag_name>/del", methods=['POST'])
def del_tag(image_name, tag_name):
    resp_info = {}

    header = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}
    resp = requests.get(ENDPOINT_PROVIDER.tag_image_detail_endpoint("", image_name, tag_name),
                        headers=header, verify=VERIFY_MODE)
    manifest_digest = resp.headers['Docker-Content-Digest']
    resp = requests.delete(ENDPOINT_PROVIDER.delete_manifest_endpoint(image_name, manifest_digest), verify=VERIFY_MODE)
    resp_info[tag_name] = 'DELETED' if resp.status_code == 202 else 'FAILED {}'.format(resp.status_code)

    image_name = urllib.parse.unquote_plus(image_name)
    tag_name = urllib.parse.unquote_plus(tag_name)
    subactions = list()
    subactions.append(Action(url_for('img_detail', image_name=urllib.parse.quote_plus(image_name)), image_name, image_name))

    return render_template('infoonly.html',
                           info=json.dumps(resp_info, indent=2),
                           actions=get_common_actions(),
                           subactions=subactions)


@app.route("/image/<image_name>", methods=['GET'])
def img_detail(image_name):

    resp = requests.get(ENDPOINT_PROVIDER.img_detail_endpoint(image_name), verify=VERIFY_MODE)
    image_name = urllib.parse.unquote_plus(image_name)

    subactions = list()
    subactions.append(Action(url_for('img_detail', image_name=urllib.parse.quote_plus(image_name)), image_name, image_name))

    tags = RESPONSE_PARSER.get_tags_from_img(resp, image_name)

    return render_template('image_page.html',
                           info=json.dumps(resp.json(), indent=2),
                           parent_item_name=image_name,
                           items=tags,
                           actions=get_common_actions(),
                           subactions=subactions)


@app.route("/image/<image_name>/<tag_name>", methods=['GET'])
def tag_detail(image_name, tag_name):
    resp = requests.get(ENDPOINT_PROVIDER.tag_detail_endpoint(image_name, tag_name), verify=VERIFY_MODE)

    show_tag_id = resp.text

    resp = requests.get(ENDPOINT_PROVIDER.tag_image_detail_endpoint(show_tag_id.strip('"'), image_name, tag_name),
                        verify=VERIFY_MODE)

    image_name = urllib.parse.unquote_plus(image_name)
    tag_name = urllib.parse.unquote_plus(tag_name)
    more_info = 'To pull use: docker pull {}/{}:{}'.format(REPO_HOST.strip('http://'), image_name, tag_name)

    subactions = list()
    subactions.append(Action(url_for('img_detail', image_name=urllib.parse.quote_plus(image_name)), image_name, image_name))
    subactions.append(Action(url_for('tag_detail',
                                     image_name=urllib.parse.quote_plus(image_name),
                                     tag_name=urllib.parse.quote_plus(tag_name)),
                             tag_name, tag_name))

    tag_detail_dict = resp.json()
    del tag_detail_dict['history']

    return render_template('tag_info.html',
                           info=json.dumps(tag_detail_dict, indent=2),
                           actions=get_common_actions(),
                           more_info=more_info,
                           subactions=subactions,
                           v2_repo=True)


@app.route("/list/", methods=['GET'])
def img_list():
    resp = requests.get(ENDPOINT_PROVIDER.image_list_endpoint(), verify=VERIFY_MODE)

    images = RESPONSE_PARSER.get_images_from_list(resp)

    return render_template('itemlist.html',
                           info=json.dumps(resp.json(), indent=2),
                           itemtype='Images',
                           items=images,
                           actions=get_common_actions())


@app.route("/", methods=['GET'])
def index():
    configured = False
    ssl_error = False
    actions = get_common_actions()
    if REPOADDRESS:
        try:
            resp = requests.get(ENDPOINT_PROVIDER.base_endpoint(), verify=VERIFY_MODE)
            configured = True
        except requests.exceptions.SSLError:
            ssl_error = True

    info = OrderedDict()
    info['Registry Address'] = REPOADDRESS
    info['Registry Version'] = REPO_FLAVOUR
    info['SSL validation'] = VERIFY_MODE
    info['Base path'] = APPLICATION_ROOT

    if not configured or resp.status_code > 299:
        actions.pop()
        info['Error'] = 'Can\'t connect to registry'

    if ssl_error:
        info['SSL Error'] = 'Can\'t connect due to SSL problem'

    return render_template('infoonly.html',
                           info=json.dumps(info, indent=2),
                           actions=actions)


if __name__ == "__main__":
    application = DispatcherMiddleware(Flask('registry_ui'), {app.config['APPLICATION_ROOT']: app})
    run_simple(hostname='0.0.0.0', port=8081, application=application, use_reloader=DEBUG)
