import urllib.parse

from flask import url_for
from entities import Image, Tag, API_CONSTANTS


class RepoFlavour:
    V1 = 1
    V2 = 2


class ResponseParser:

    def __init__(self, repo_flavour):
        self._repo_flavour = repo_flavour

    def get_images_from_list(self, resp):
        images = list()
        if self._repo_flavour == RepoFlavour.V1:
            for image in resp.json()["results"]:
                images.append(Image(image["name"].lstrip(API_CONSTANTS.NAMESPACE).lstrip('/'),
                                    url_for('img_detail',
                                            image_name=urllib.parse.quote_plus(image["name"].lstrip(API_CONSTANTS.NAMESPACE)))))
            images.sort(key=lambda x: x.name)
            return images
        if self._repo_flavour == RepoFlavour.V2:
            for image in resp.json()["repositories"]:
                images.append(Image(image,
                                    url_for('img_detail', image_name=urllib.parse.quote_plus(image))))
            images.sort(key=lambda x: x.name)
            return images

    def get_tags_from_img(self, resp, image_name):
        tags = list()
        if self._repo_flavour == RepoFlavour.V1:
            for tag_name, tag_id in resp.json().items():
                tags.append(Tag(tag_name, url_for('tag_detail',
                                                  image_name=urllib.parse.quote_plus(image_name),
                                                  tag_name=urllib.parse.quote_plus(tag_name))))

            tags.sort(key=lambda x: x.name, reverse=True)
            return tags
        if self._repo_flavour == RepoFlavour.V2:
            if 'tags' in resp.json() and resp.json()['tags']:
                for tag_name in resp.json()['tags']:
                    tags.append(Tag(tag_name, url_for('tag_detail',
                                                      image_name=urllib.parse.quote_plus(image_name),
                                                      tag_name=urllib.parse.quote_plus(tag_name))))
            return tags


class EndpointProvider:

    def __init__(self, repo_flavour, repo_address):
        self._repo_flavour = repo_flavour
        self._repo_address = repo_address

    def base_endpoint(self):
        if self._repo_flavour == RepoFlavour.V1:
            return '{}/v1/_ping'.format(self._repo_address)
        elif self._repo_flavour == RepoFlavour.V2:
            return '{}/v2/'.format(self._repo_address)
        else:
            raise NotImplementedError()

    def img_detail_endpoint(self, image_name):
        if self._repo_flavour == RepoFlavour.V1:
            return '{}/v1/repositories/{}/{}/tags'.format(self._repo_address, API_CONSTANTS.NAMESPACE, image_name)
        elif self._repo_flavour == RepoFlavour.V2:
            return '{}/v2/{}/tags/list'.format(self._repo_address, image_name)
        else:
            raise NotImplementedError()

    def tag_detail_endpoint(self, image_name, tag_name):
        if self._repo_flavour == RepoFlavour.V1:
            return '{}/v1/repositories/{}/{}/tags/{}'.format(self._repo_address, API_CONSTANTS.NAMESPACE, image_name, tag_name)
        elif self._repo_flavour == RepoFlavour.V2:
            return '{}/v2/{}/manifests/{}'.format(self._repo_address, image_name, tag_name)
        else:
            raise NotImplementedError()

    def tag_image_detail_endpoint(self, tag_id, image_name, tag_name):
        if self._repo_flavour == RepoFlavour.V1:
            return '{}/v1/images/{}/json'.format(self._repo_address, API_CONSTANTS.NAMESPACE, tag_id)
        elif self._repo_flavour == RepoFlavour.V2:
            return '{}/v2/{}/manifests/{}'.format(self._repo_address, image_name, tag_name)
        else:
            raise NotImplementedError()

    def image_list_endpoint(self):
        if self._repo_flavour == RepoFlavour.V1:
            return '{}/v1/search'.format(self._repo_address)
        elif self._repo_flavour == RepoFlavour.V2:
            return '{}/v2/_catalog'.format(self._repo_address)
        else:
            raise NotImplementedError()

    def delete_repo_endpoint(self, image_name):
        if self._repo_flavour == RepoFlavour.V1:
            return '{}/v1/repositories/{}/{}/'.format(self._repo_address, API_CONSTANTS.NAMESPACE, image_name)
        else:
            raise NotImplementedError()

    def delete_manifest_endpoint(self, image_name, manifest_digest):
        if self._repo_flavour == RepoFlavour.V2:
            return '{}/v2/{}/manifests/{}'.format(self._repo_address, image_name, manifest_digest)
        else:
            raise NotImplementedError()
