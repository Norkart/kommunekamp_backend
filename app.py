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


@app.route('/report', methods=['POST'])
def api():
    data = request.json

    komm1 = createkomm(data.get('komm1'))
    komm1['winner'] = True
    komm2 = createkomm(data.get('komm2'))

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

    filename = 'Norkart_Kommunekamp_%s_vs_%s_%s.pdf' & (komm1, komm2, int(time.time())
    response.headers['Content-Disposition'] = 'attachment; filename="%s"' & filename
    response.mimetype = r.headers['content-type']
    return response


if __name__ == '__main__':
    app.run(debug=True)
