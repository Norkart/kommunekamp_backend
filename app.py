# -*- coding: utf-8 -*-

import os
import json
import requests

import time
from flask import Flask, request, make_response
from cartodb import CartoDBAPIKey, CartoDBException
from shapely.geometry import shape

from datavarehus import get_komm, dataset_bbox

app = Flask(__name__)
app.debug = True

TEMPLATE_ID = '4ySbCCCqx'
TOKEN = os.environ.get('TOKEN', None)

CDB_KEY = os.environ.get('CDB_KEY', None)
CDB_DOMAIN = os.environ.get('CDB_DOMAIN', None)

RAPPORT_URL = os.environ.get('RAPPORT_URL', None)


def createkomm(id):
    komm = get_komm(id)
    return {
        'komm': id,
        'name': komm['properties']['ADMENHETNAVN.NAVN'],
        'numBreweries': get_breweries(komm),
        'kmFootTrails': get_foot_trails(komm),
        'rain': get_nedboer(komm),
        'percentageUnder35': 30,
        'winner': False
    }


def geojson_sql(geometry):
    return 'ST_SetSrid(ST_GeomFromGeoJSON(\'%s\'), 4326)' % json.dumps(geometry)


def get_breweries(komm):
    cl = CartoDBAPIKey(CDB_KEY, CDB_DOMAIN)
    try:
        res = cl.sql('''
            SELECT
                 count(*)
            FROM
                osm_breweries
            WHERE
                ST_Contains(%s, the_geom)
        ''' % geojson_sql(komm['geometry']))

        return res['rows'][0]['count']
    except CartoDBException:
        return -1


def get_nedboer(komm):
    geom = shape(komm['geometry'])
    features = dataset_bbox(80, geom.bounds)

    komm_features = [feature for feature in features['features']
                     if inside(feature, geom)]

    nedboer = []
    for feature in komm_features:
        props = feature['properties']
        nedboer.append(
            int(props['NEDBOR_VAAR']) +
            int(props['NEDBOR_HOST']) +
            int(props['NEDBOR_SOMMER']) +
            int(props['NEDBOR_VINTER'])
        )

    nedboer = round(float(sum(nedboer)) / float(len(nedboer)))

    return nedboer

def get_foot_trails(komm):
    cl = CartoDBAPIKey(CDB_KEY, CDB_DOMAIN)
    try:
        gj = geojson_sql(komm['geometry'])
        query = '''
            SELECT
                SUM(
                  ST_Length(
                    ST_INTERSECTION(
                        s.the_geom::geography,
                        %s::geography
                    )
                  )
                ) / 1000 as len
            FROM
                fotrute s
            WHERE
                ST_Intersects(%s, s.the_geom);
        ''' % (gj, gj)
        res = cl.sql(query)
        length = res['rows'][0]['len']
        return round(length) if length is not None else 0
    except CartoDBException:
        return -1


def inside(point_feature, poly):
    geom = shape(point_feature['geometry'])
    return geom.within(poly)


@app.route('/')
def index():
    komm = get_komm('1201')
    n = get_nedboer(komm)

    return '%s' % n


def get_scores(komm1, komm2, attr):
    attribute = attr['attr']
    factor = attr['factor']
    total = float(komm1[attribute] + komm2[attribute])

    minumum_best = attr.get('min', False)

    if total > 0:
        komm1_percentage = float(komm1[attribute]) / total
        komm2_percentage = float(komm2[attribute]) / total
        if minumum_best:
            return (total - komm1_percentage) * factor, (total - komm2_percentage) * factor
        return komm1_percentage * factor, komm2_percentage * factor
    return 0.0, 0.0


def get_winner(komm1, komm2):
    komm1_scores = []
    komm2_scores = []
    attrs = [
        {'attr': 'numBreweries', 'factor': 0.6},
        {'attr': 'kmFootTrails', 'factor': 0.2},
        {'attr': 'rain', 'factor': 0.3, 'min': True},
    ]

    for attr in attrs:
        komm1_score, komm2_score = get_scores(komm1, komm2, attr)
        komm1_scores.append(komm1_score)
        komm2_scores.append(komm2_score)

    return sum(komm1_scores), sum(komm2_scores)


def get_komm_data():
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

    return [komm1, komm2]


@app.route('/data', methods=['POST'])
def data():
    return json.dumps(get_komm_data())


@app.route('/report', methods=['POST'])
def report():
    rdata = request.json

    komm1_id = rdata.get('komm1')
    komm2_id = rdata.get('komm2')

    komm = get_komm_data()

    data = {
        'Data': json.dumps({'data': komm})
    }

    headers = {
        'X-WAAPI-TOKEN': TOKEN,
        'Content-type': 'application/json'
    }

    url = '%s/generateReport/%s' % (RAPPORT_URL, TEMPLATE_ID)

    r = requests.post(url, data=json.dumps(data), headers=headers, stream=True)

    response = make_response(r.content)

    filename = 'Norkart_Kommunekamp_%s_vs_%s_%s.pdf' % (komm1_id, komm2_id, int(time.time()))
    response.headers['Content-Disposition'] = 'attachment; filename="%s"' % filename
    response.mimetype = r.headers['content-type']
    return response


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
