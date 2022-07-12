import requests
import datetime


def get_v(token, amount):
    try:
        q = '{token(id: "%s") { symbol derivedAVAX } bundle(id: 1) { avaxPrice }}' % (
            token.lower())
        request = requests.post(
            'https://api.thegraph.com/subgraphs/name/traderjoe-xyz/exchange', json={'query': q})
        r = request.json()
        avax_price = float(r['data']['bundle']['avaxPrice'])
        in_avax = float(r['data']['token']['derivedAVAX'])
        in_usd = in_avax * avax_price
        return amount * in_usd
    except Exception as e:
        return 0


def get_today():
    now = datetime.datetime.now()
    d = now.strftime('%Y-%m-%d')
    return d


def get_token(token):
    q = '{token(id: "%s") { symbol }}' % (token.lower())
    request = requests.post(
        'https://api.thegraph.com/subgraphs/name/yieldyak/yak-aggregator', json={'query': q})
    r = request.json()
    return r['data']['token']['symbol']


def get_adapter(adapter):
    q = '{adapter(id: "%s") { name }}' % (adapter.lower())
    request = requests.post(
        'https://api.thegraph.com/subgraphs/name/yieldyak/yak-aggregator', json={'query': q})
    r = request.json()
    return r['data']['adapter']['name'].replace('YakAdapterV0', '').replace('AdapterV0', '').replace('V1YakAdapterV0', '').replace('V1', '').replace('Adapter', '')
