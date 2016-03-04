# -*- coding: utf-8 -*-

import urllib
import os

import requests


DATAVAREHUS_URL = os.environ.get('DATAVAREHUS_URL', None)


def get_komm(komm_id):
    headers = {
        'X-WAAPI-TOKEN': '99b083ae-bd53-4a7d-be32-ac8e57d732bd',
        'Content-type': 'application/json'
    }
    query = urllib.quote_plus('FTEMA=4003 AND KOMM=%s' % komm_id)
    url = '%s/datasets/7/features/query?Query=%s' % (DATAVAREHUS_URL, query)
    r = requests.get(url, headers=headers)
    d = r.json()
    if 'features' in d:
        return d['features'][0]


def dataset_bbox(dataset_id, bounds):
    headers = {
        'X-WAAPI-TOKEN': '99b083ae-bd53-4a7d-be32-ac8e57d732bd',
        'Content-type': 'application/json'
    }
    bbox = ','.join([str(c) for c in list(bounds)])

    print bbox

    url = '%s/datasets/%s/features/bboxquery?Bbox=%s' % (DATAVAREHUS_URL, dataset_id, bbox)
    r = requests.get(url, headers=headers)
    return r.json()
