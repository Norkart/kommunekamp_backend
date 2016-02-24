# -*- coding: utf-8 -*-

import os
import json
import requests
import urllib
import time
from flask import Flask, request, make_response
from cartodb import CartoDBAPIKey, CartoDBException


app = Flask(__name__)
app.debug = True

TEMPLATE_ID = '4ySbCCCqx'
TOKEN = os.environ.get('TOKEN', None)

CDB_KEY = os.environ.get('CDB_KEY', None)
CDB_DOMAIN = os.environ.get('CDB_DOMAIN', None)

DATAVAREHUS_URL = os.environ.get('DATAVAREHUS_URL', None)
RAPPORT_URL = os.environ.get('RAPPORT_URL', None)


def get_komm(komm_id):
    headers = {
        'X-WAAPI-TOKEN': TOKEN,
        'Content-type': 'application/json'
    }
    query = urllib.quote_plus('FTEMA=4003 AND KOMM=%s' % komm_id)
    url = '%s/datasets/7/features/query?Query=%s' % (DATAVAREHUS_URL, query)
    r = requests.get(url, headers=headers)
    d = r.json()
    if 'features' in d:
        return d['features'][0]


def createkomm(id):
    komm = get_komm(id)
    return {
        "komm": id,
        "name": komm['properties']['ADMENHETNAVN.NAVN'],
        "numBreweries": get_breweries(komm),
        "kmTrails": 100,
        "percentageUnder35": 30,
        "winner": False
    }


def get_breweries(komm):
    cl = CartoDBAPIKey(CDB_KEY, CDB_DOMAIN)
    try:
        res = cl.sql('select count(*) FROM osm_breweries WHERE ST_Contains(ST_SetSrid(ST_GeomFromGeoJSON(\'%s\'), 4326), the_geom)' % json.dumps(komm['geometry']))
        return res['rows'][0]['count']
    except CartoDBException:
        return -1


@app.route('/')
def index():
    get_breweries(get_komm('1601'))
    return 'test'


def get_scores(komm1, komm2, attribute, factor):
    total = float(komm1[attribute] + komm2[attribute])
    if total > 0:
        komm1_percentage = float(komm1[attribute]) / total
        komm2_percentage = float(komm2[attribute]) / total

        return komm1_percentage * factor, komm2_percentage * factor
    return 0.0, 0.0


def get_winner(komm1, komm2):
    komm1_scores = []
    komm2_scores = []
    attrs = [
        {'attr': 'numBreweries', 'factor': 0.6},
        {'attr': 'kmTrails', 'factor': 0.2},
        {'attr': 'percentageUnder35', 'factor': 0.3}
    ]

    for attr in attrs:
        komm1_score, komm2_score = get_scores(komm1, komm2, attr['attr'], attr['factor'])
        komm1_scores.append(komm1_score)
        komm2_scores.append(komm2_score)

    return sum(komm1_scores), sum(komm2_scores)


@app.route('/report', methods=['POST'])
def api():
    data = request.json

    komm1_id = data.get('komm1')
    komm1 = createkomm(komm1_id)

    komm2_id = data.get('komm2')
    komm2 = createkomm(komm2_id)

    komm1_score, komm2_score = get_winner(komm1, komm2)

    if komm1_score > komm2_score:
        komm1['winner'] = True
    elif komm1_score < komm2_score:
        komm2['winner'] = True

    komm = [komm1, komm2]

    headers = {
        'X-WAAPI-TOKEN': TOKEN,
        'Content-type': 'application/json'
    }

    url = '%s/generateReport/%s' % (RAPPORT_URL, TEMPLATE_ID)

    data = {
        'Data': json.dumps({"data": komm})
    }

    r = requests.post(url, data=json.dumps(data), headers=headers, stream=True)

    response = make_response(r.content)

    filename = 'Norkart_Kommunekamp_%s_vs_%s_%s.pdf' % (komm1_id, komm2_id, int(time.time()))
    response.headers['Content-Disposition'] = 'attachment; filename="%s"' % filename
    response.mimetype = r.headers['content-type']
    return response


if __name__ == '__main__':
    app.run(debug=True)
