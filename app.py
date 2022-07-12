from flask import Flask, render_template
from funcs import get_v, get_today, get_token, get_adapter
import time
import redis
import requests
import datetime
import json
import threading


app = Flask(__name__)

redis = redis.Redis(host='127.0.0.1', port=6379, db=0, decode_responses=True)


def get_swaps():
    while True:
        try:
            SwapQ = "{swaps(first: 25, orderBy: blockNumber, orderDirection: desc) {trader {id countSwaps} transactionHash fromToken {id symbol decimals name} fromAmount toToken {id symbol decimals name} toAmount blockTimestamp blockNumber } }"
            request = requests.post(
                'https://api.thegraph.com/subgraphs/name/yieldyak/yak-aggregator', json={'query': SwapQ})
            r = request.json()
            for i in r['data']['swaps']:
                tx = i['transactionHash']
                exists = redis.sismember('flasktx', tx)
                if not exists:
                    from_amount_decimals = int(i['fromToken']['decimals'])
                    from_amount = float(i['fromAmount']) / \
                        10 ** from_amount_decimals
                    from_token_name = i['fromToken']['name']
                    from_token_symbol = i['fromToken']['symbol']
                    from_token_id = i['fromToken']['id']

                    to_amount_decimals = int(i['toToken']['decimals'])
                    to_amount = float(i['toAmount']) / 10 ** to_amount_decimals
                    to_token_name = i['toToken']['name']
                    to_token_symbol = i['toToken']['symbol']
                    to_token_id = i['toToken']['id']

                    today = get_today()
                    swap_value = round(get_v(from_token_id, from_amount))

                    # volume swap for today
                    redis.incrby(f"TotalVolumeSwap#{today}", swap_value)
                    redis.incrby(
                        f"TokenVolumeSwap#{today}#{from_token_id}", swap_value)  # volume swap for from_token for today
                    redis.incrby(
                        f"TokenVolumeSwap#{today}#{to_token_id}", swap_value)  # volume swap for to_token for today

                    redis.incr(f"TotalCountSwap#{today}")  # count swap for today
                    redis.incr(
                        f"TokenCountSwap#{today}#{from_token_id}")  # count swap for from_token for today
                    redis.incr(
                        f"TokenCountSwap#{today}#{to_token_id}")  # count swap for to_token for today

                    fromtokenCountSwap = redis.zscore(
                        f"TokenCountSwap#{today}", f"{from_token_id}")
                    if fromtokenCountSwap is None:
                        fromtokenCountSwap = 1
                    else:
                        fromtokenCountSwap = int(fromtokenCountSwap) + 1
                    data = from_token_id
                    score = fromtokenCountSwap
                    redis.zadd(f"TokenCountSwap#{today}", {data: score})

                    fromtokenVolumeSwap = redis.zscore(
                        f"TokenVolumeSwap#{today}", f"{from_token_id}")
                    if fromtokenVolumeSwap is None:
                        fromtokenVolumeSwap = swap_value
                    else:
                        fromtokenVolumeSwap = int(fromtokenVolumeSwap) + swap_value
                    data = from_token_id
                    score = fromtokenVolumeSwap
                    redis.zadd(f"TokenVolumeSwap#{today}", {data: score})

                    totokenCountSwap = redis.zscore(
                        f"TokenCountSwap#{today}", f"{to_token_id}")
                    if totokenCountSwap is None:
                        totokenCountSwap = 1
                    else:
                        totokenCountSwap = int(totokenCountSwap) + 1
                    data = to_token_id
                    score = totokenCountSwap
                    redis.zadd(f"TokenCountSwap#{today}", {data: score})

                    totokenVolumeSwap = redis.zscore(
                        f"TokenVolumeSwap#{today}", f"{to_token_id}")
                    if totokenVolumeSwap is None:
                        totokenVolumeSwap = swap_value
                    else:
                        totokenVolumeSwap = int(totokenVolumeSwap) + swap_value
                    data = to_token_id
                    score = totokenVolumeSwap
                    redis.zadd(f"TokenVolumeSwap#{today}", {data: score})

                    ##########################################

                    AdaperQ = """{adapterSwaps(where : {transactionHash : "%s"} first: 10, orderBy: logIndex) { transactionHash fromToken { symbol decimals id name } fromAmount toToken { symbol decimals id name } toAmount adapter {name id} } }""" % (
                        tx.lower())
                    request = requests.post(
                        'https://api.thegraph.com/subgraphs/name/yieldyak/yak-aggregator', json={'query': AdaperQ})
                    r = request.json()
                    for adapter in r['data']['adapterSwaps']:
                        adapter_id = adapter['adapter']['id']

                        redis.incrby(
                            f"AdapterVolumeSwap#{today}#{adapter_id}", swap_value)  # volume swap for adapter for today
                        redis.incr(
                            f"AdapterCountSwap#{today}#{adapter_id}")  # count swap for for adapter for today

                        AdapterCountSwap = redis.zscore(
                            f"AdapterCountSwap#{today}", f"{adapter_id}")
                        if AdapterCountSwap is None:
                            AdapterCountSwap = 1
                        else:
                            AdapterCountSwap = int(AdapterCountSwap) + 1
                        data = adapter_id
                        score = AdapterCountSwap
                        redis.zadd(f"AdapterCountSwap#{today}", {data: score})

                        AdapterVolumeSwap = redis.zscore(
                            f"AdapterVolumeSwap#{today}", f"{adapter_id}")
                        if AdapterVolumeSwap is None:
                            AdapterVolumeSwap = swap_value
                        else:
                            AdapterVolumeSwap = int(AdapterVolumeSwap) + swap_value
                        data = adapter_id
                        score = AdapterVolumeSwap
                        redis.zadd(f"AdapterVolumeSwap#{today}", {data: score})

                        #  - #  - #  - #  - #  - #  - #  - #  - #  - #  - #  - #

                        from_token_id = adapter['fromToken']['id']
                        to_token_id = adapter['toToken']['id']

                        redis.incrby(
                            f"UnderlyingTotalVolumeSwap#{today}", swap_value)
                        redis.incrby(
                            f"UnderlyingTokenVolumeSwap#{today}#{from_token_id}", swap_value)
                        redis.incrby(
                            f"UnderlyingTokenVolumeSwap#{today}#{to_token_id}", swap_value)

                        redis.incr(f"UnderlyingTotalCountSwap#{today}")
                        redis.incr(
                            f"UnderlyingTokenCountSwap#{today}#{from_token_id}")
                        redis.incr(
                            f"UnderlyingTokenCountSwap#{today}#{to_token_id}")

                        fromtokenCountSwap = redis.zscore(
                            f"UnderlyingTokenCountSwap#{today}", f"{from_token_id}")
                        if fromtokenCountSwap is None:
                            fromtokenCountSwap = 1
                        else:
                            fromtokenCountSwap = int(fromtokenCountSwap) + 1
                        data = from_token_id
                        score = fromtokenCountSwap
                        redis.zadd(
                            f"UnderlyingTokenCountSwap#{today}", {data: score})

                        fromtokenVolumeSwap = redis.zscore(
                            f"UnderlyingTokenVolumeSwap#{today}", f"{from_token_id}")
                        if fromtokenVolumeSwap is None:
                            fromtokenVolumeSwap = swap_value
                        else:
                            fromtokenVolumeSwap = int(
                                fromtokenVolumeSwap) + swap_value
                        data = from_token_id
                        score = fromtokenVolumeSwap
                        redis.zadd(
                            f"UnderlyingTokenVolumeSwap#{today}", {data: score})

                        totokenCountSwap = redis.zscore(
                            f"UnderlyingTokenCountSwap#{today}", f"{to_token_id}")
                        if totokenCountSwap is None:
                            totokenCountSwap = 1
                        else:
                            totokenCountSwap = int(totokenCountSwap) + 1
                        data = to_token_id
                        score = totokenCountSwap
                        redis.zadd(
                            f"UnderlyingTokenCountSwap#{today}", {data: score})

                        totokenVolumeSwap = redis.zscore(
                            f"UnderlyingTokenVolumeSwap#{today}", f"{to_token_id}")
                        if totokenVolumeSwap is None:
                            totokenVolumeSwap = swap_value
                        else:
                            totokenVolumeSwap = int(totokenVolumeSwap) + swap_value
                        data = to_token_id
                        score = totokenVolumeSwap
                        redis.zadd(
                            f"UnderlyingTokenVolumeSwap#{today}", {data: score})

                        #  - #  - #  - #  - #  - #  - #  - #  - #  - #  - #  - #

                        Adapter_totoken_MostSwap = redis.zscore(
                            f"AdapterMostTokenSwap#{today}#{adapter_id}", f"{to_token_id}")
                        if Adapter_totoken_MostSwap is None:
                            Adapter_totoken_MostSwap = 1
                        else:
                            Adapter_totoken_MostSwap = int(
                                Adapter_totoken_MostSwap) + 1
                        data = to_token_id
                        score = Adapter_totoken_MostSwap
                        redis.zadd(
                            f"AdapterMostTokenSwap#{today}#{adapter_id}", {data: score})

                        Adapter_fromtoken_MostSwap = redis.zscore(
                            f"AdapterMostTokenSwap#{today}#{adapter_id}", f"{from_token_id}")
                        if Adapter_fromtoken_MostSwap is None:
                            Adapter_fromtoken_MostSwap = 1
                        else:
                            Adapter_fromtoken_MostSwap = int(
                                Adapter_fromtoken_MostSwap) + 1
                        data = from_token_id
                        score = Adapter_fromtoken_MostSwap
                        redis.zadd(
                            f"AdapterMostTokenSwap#{today}#{adapter_id}", {data: score})

                        totoken_MostSwap = redis.zscore(
                            f"tokenMostTokenSwap#{today}#{to_token_id}", f"{adapter_id}")
                        if totoken_MostSwap is None:
                            totoken_MostSwap = 1
                        else:
                            totoken_MostSwap = int(
                                totoken_MostSwap) + 1
                        data = adapter_id
                        score = totoken_MostSwap
                        redis.zadd(
                            f"tokenMostTokenSwap#{today}#{to_token_id}", {data: score})

                        fromtoken_MostSwap = redis.zscore(
                            f"tokenMostTokenSwap#{today}#{from_token_id}", f"{adapter_id}")
                        if fromtoken_MostSwap is None:
                            fromtoken_MostSwap = 1
                        else:
                            fromtoken_MostSwap = int(
                                fromtoken_MostSwap) + 1
                        data = adapter_id
                        score = fromtoken_MostSwap
                        redis.zadd(
                            f"tokenMostTokenSwap#{today}#{from_token_id}", {data: score})

                    redis.sadd(f"UniqueTraders#{today}", i['trader']['id'])

                    redis.sadd("flasktx", tx)

            time.sleep(30)
        except Exception as e:
            print(e)


@app.route('/')
def home():
    daysList = []
    TotalCountSwapList = []
    TotalVolumeSwapList = []
    tokenitemsCountSwapList = []
    tokenitemsVolumeSwapList = []
    AdapteritemsCountSwapList = []
    AdapteritemsVolumeSwapList = []
    UniqueTradersList = []

    UnderlyingTotalCountSwapList = []
    UnderlyingTotalVolumeSwapList = []
    UnderlyingtokenitemsCountSwapList = []
    UnderlyingtokenitemsVolumeSwapList = []
    UnderlyingAdapteritemsCountSwapList = []
    UnderlyingAdapteritemsVolumeSwapList = []

    now = datetime.datetime.now()
    for i in range(0, 7):
        week_ago = now - datetime.timedelta(days=i)
        week_ago = week_ago.strftime('%Y-%m-%d')
        daysList.append(week_ago)

        TotalCountSwap = redis.get(f"TotalCountSwap#{week_ago}")
        if TotalCountSwap is None:
            TotalCountSwap = 0
        TotalCountSwapList.append(int(TotalCountSwap))

        TotalVolumeSwap = redis.get(f"TotalVolumeSwap#{week_ago}")
        if TotalVolumeSwap is None:
            TotalVolumeSwap = 0
        TotalVolumeSwapList.append(int(TotalVolumeSwap))

        UnderlyingTotalCountSwap = redis.get(
            f"UnderlyingTotalCountSwap#{week_ago}")
        if UnderlyingTotalCountSwap is None:
            UnderlyingTotalCountSwap = 0
        UnderlyingTotalCountSwapList.append(int(UnderlyingTotalCountSwap))

        UnderlyingTotalVolumeSwap = redis.get(
            f"UnderlyingTotalVolumeSwap#{week_ago}")
        if UnderlyingTotalVolumeSwap is None:
            UnderlyingTotalVolumeSwap = 0
        UnderlyingTotalVolumeSwapList.append(int(UnderlyingTotalVolumeSwap))

        UniqueTraders = redis.scard(f"UniqueTraders#{week_ago}")
        if UniqueTraders is None:
            UniqueTraders = 0
        UniqueTradersList.append(int(UniqueTraders))

    daysList.reverse()
    TotalCountSwapList.reverse()
    TotalVolumeSwapList.reverse()
    UnderlyingTotalCountSwapList.reverse()
    UnderlyingTotalVolumeSwapList.reverse()
    UniqueTradersList.reverse()

    newnow = now.strftime('%Y-%m-%d')
    TokenCountSwap = redis.zrange(
        f"TokenCountSwap#{newnow}", 0, 9, desc=True, withscores=True)
    tokenitemsCountSwap = [item[0] for item in TokenCountSwap]
    scoreitemsCountSwapList = [int(item[1]) for item in TokenCountSwap]

    for token in tokenitemsCountSwap:
        symbol = get_token(token)
        tokenitemsCountSwapList.append(symbol)

    TokenVolumeSwap = redis.zrange(
        f"TokenVolumeSwap#{newnow}", 0, 9, desc=True, withscores=True)
    tokenitemsVolumeSwap = [item[0] for item in TokenVolumeSwap]
    scoreitemsVolumeSwapList = [int(item[1]) for item in TokenVolumeSwap]

    for token in tokenitemsVolumeSwap:
        symbol = get_token(token)
        tokenitemsVolumeSwapList.append(symbol)

    UnderlyingTokenCountSwap = redis.zrange(
        f"UnderlyingTokenCountSwap#{newnow}", 0, 9, desc=True, withscores=True)
    UnderlyingtokenitemsCountSwap = [item[0]
                                     for item in UnderlyingTokenCountSwap]
    UnderlyingscoreitemsCountSwapList = [
        int(item[1]) for item in UnderlyingTokenCountSwap]

    for token in UnderlyingtokenitemsCountSwap:
        symbol = get_token(token)
        UnderlyingtokenitemsCountSwapList.append(symbol)

    UnderlyingTokenVolumeSwap = redis.zrange(
        f"UnderlyingTokenVolumeSwap#{newnow}", 0, 9, desc=True, withscores=True)
    UnderlyingtokenitemsVolumeSwap = [item[0]
                                      for item in UnderlyingTokenVolumeSwap]
    UnderlyingscoreitemsVolumeSwapList = [
        int(item[1]) for item in UnderlyingTokenVolumeSwap]

    for token in UnderlyingtokenitemsVolumeSwap:
        symbol = get_token(token)
        UnderlyingtokenitemsVolumeSwapList.append(symbol)

    AdapterCountSwap = redis.zrange(
        f"AdapterCountSwap#{newnow}", 0, 9, desc=True, withscores=True)
    AdapteritemsCountSwap = [item[0] for item in AdapterCountSwap]
    AdapterscoreitemsCountSwapList = [
        int(item[1]) for item in AdapterCountSwap]

    for adapter in AdapteritemsCountSwap:
        symbol = get_adapter(adapter)
        AdapteritemsCountSwapList.append(symbol)

    AdapterVolumeSwap = redis.zrange(
        f"AdapterVolumeSwap#{newnow}", 0, 9, desc=True, withscores=True)
    AdapteritemsVolumeSwap = [item[0] for item in AdapterVolumeSwap]
    AdapterscoreitemsVolumeSwapList = [
        int(item[1]) for item in AdapterVolumeSwap]

    for adapter in AdapteritemsVolumeSwap:
        symbol = get_adapter(adapter)
        AdapteritemsVolumeSwapList.append(symbol)

    return render_template('home.html', daysList=daysList, TotalCountSwapList=TotalCountSwapList, TotalVolumeSwapList=TotalVolumeSwapList, scoreitemsCountSwapList=scoreitemsCountSwapList, tokenitemsCountSwapList=tokenitemsCountSwapList, scoreitemsVolumeSwapList=scoreitemsVolumeSwapList, tokenitemsVolumeSwapList=tokenitemsVolumeSwapList, AdapteritemsCountSwapList=AdapteritemsCountSwapList, AdapterscoreitemsCountSwapList=AdapterscoreitemsCountSwapList, AdapterscoreitemsVolumeSwapList=AdapterscoreitemsVolumeSwapList, AdapteritemsVolumeSwapList=AdapteritemsVolumeSwapList, UniqueTradersList=UniqueTradersList, UnderlyingTotalCountSwapList=UnderlyingTotalCountSwapList, UnderlyingTotalVolumeSwapList=UnderlyingTotalVolumeSwapList, UnderlyingscoreitemsCountSwapList=UnderlyingscoreitemsCountSwapList, UnderlyingtokenitemsCountSwapList=UnderlyingtokenitemsCountSwapList, UnderlyingscoreitemsVolumeSwapList=UnderlyingscoreitemsVolumeSwapList, UnderlyingtokenitemsVolumeSwapList=UnderlyingtokenitemsVolumeSwapList)


@app.route('/topweekly')
def topWeekly():
    TokenVolumeSwapList = []
    TokenCountSwapList = []
    AdapterCountSwapList = []
    AdapterVolumeSwapList = []

    tokenitemsCountSwapList = []
    tokenitemsVolumeSwapList = []
    AdapteritemsCountSwapList = []
    AdapteritemsVolumeSwapList = []

    UnderlyingTokenVolumeSwapList = []
    UnderlyingTokenCountSwapList = []

    UnderlyingtokenitemsCountSwapList = []
    UnderlyingtokenitemsVolumeSwapList = []

    now = datetime.datetime.now()
    for i in range(0, 7):
        week_ago = now - datetime.timedelta(days=i)
        week_ago = week_ago.strftime('%Y-%m-%d')
        TokenVolumeSwapList.append(f"TokenVolumeSwap#{week_ago}")
        TokenCountSwapList.append(f"TokenCountSwap#{week_ago}")
        AdapterCountSwapList.append(f"AdapterCountSwap#{week_ago}")
        AdapterVolumeSwapList.append(f"AdapterVolumeSwap#{week_ago}")

        UnderlyingTokenVolumeSwapList.append(
            f"UnderlyingTokenVolumeSwap#{week_ago}")
        UnderlyingTokenCountSwapList.append(
            f"UnderlyingTokenCountSwap#{week_ago}")

    redis.zunionstore(dest='TokenCountSwapWeekly', keys=TokenCountSwapList)
    redis.zunionstore(dest='TokenVolumeSwapWeekly', keys=TokenVolumeSwapList)
    redis.zunionstore(dest='AdapterCountSwapWeekly', keys=AdapterCountSwapList)
    redis.zunionstore(dest='AdapterVolumeSwapWeekly',
                      keys=AdapterVolumeSwapList)
    redis.zunionstore(dest='UnderlyingTokenCountSwapWeekly',
                      keys=UnderlyingTokenCountSwapList)
    redis.zunionstore(dest='UnderlyingTokenVolumeSwapWeekly',
                      keys=UnderlyingTokenVolumeSwapList)

    newnow = now.strftime('%Y-%m-%d')

    TokenCountSwap = redis.zrange(
        "TokenCountSwapWeekly", 0, 9, desc=True, withscores=True)
    tokenitemsCountSwap = [item[0] for item in TokenCountSwap]
    scoreitemsCountSwapList = [int(item[1]) for item in TokenCountSwap]

    for token in tokenitemsCountSwap:
        symbol = get_token(token)
        tokenitemsCountSwapList.append(symbol)

    TokenVolumeSwap = redis.zrange(
        "TokenVolumeSwapWeekly", 0, 9, desc=True, withscores=True)
    tokenitemsVolumeSwap = [item[0] for item in TokenVolumeSwap]
    scoreitemsVolumeSwapList = [int(item[1]) for item in TokenVolumeSwap]

    for token in tokenitemsVolumeSwap:
        symbol = get_token(token)
        tokenitemsVolumeSwapList.append(symbol)

    UnderlyingTokenCountSwap = redis.zrange(
        "UnderlyingTokenCountSwapWeekly", 0, 9, desc=True, withscores=True)
    UnderlyingtokenitemsCountSwap = [item[0]
                                     for item in UnderlyingTokenCountSwap]
    UnderlyingscoreitemsCountSwapList = [
        int(item[1]) for item in UnderlyingTokenCountSwap]

    for token in UnderlyingtokenitemsCountSwap:
        symbol = get_token(token)
        UnderlyingtokenitemsCountSwapList.append(symbol)

    UnderlyingTokenVolumeSwap = redis.zrange(
        "UnderlyingTokenVolumeSwapWeekly", 0, 9, desc=True, withscores=True)
    UnderlyingtokenitemsVolumeSwap = [item[0]
                                      for item in UnderlyingTokenVolumeSwap]
    UnderlyingscoreitemsVolumeSwapList = [
        int(item[1]) for item in UnderlyingTokenVolumeSwap]

    for token in UnderlyingtokenitemsVolumeSwap:
        symbol = get_token(token)
        UnderlyingtokenitemsVolumeSwapList.append(symbol)

    AdapterCountSwap = redis.zrange(
        "AdapterCountSwapWeekly", 0, 9, desc=True, withscores=True)
    AdapteritemsCountSwap = [item[0] for item in AdapterCountSwap]
    AdapterscoreitemsCountSwapList = [
        int(item[1]) for item in AdapterCountSwap]

    for adapter in AdapteritemsCountSwap:
        symbol = get_adapter(adapter)
        AdapteritemsCountSwapList.append(symbol)

    AdapterVolumeSwap = redis.zrange(
        "AdapterVolumeSwapWeekly", 0, 9, desc=True, withscores=True)
    AdapteritemsVolumeSwap = [item[0] for item in AdapterVolumeSwap]
    AdapterscoreitemsVolumeSwapList = [
        int(item[1]) for item in AdapterVolumeSwap]

    for adapter in AdapteritemsVolumeSwap:
        symbol = get_adapter(adapter)
        AdapteritemsVolumeSwapList.append(symbol)

    return render_template('topweekly.html', scoreitemsCountSwapList=scoreitemsCountSwapList, tokenitemsCountSwapList=tokenitemsCountSwapList, scoreitemsVolumeSwapList=scoreitemsVolumeSwapList, tokenitemsVolumeSwapList=tokenitemsVolumeSwapList, AdapteritemsCountSwapList=AdapteritemsCountSwapList, AdapterscoreitemsCountSwapList=AdapterscoreitemsCountSwapList, AdapterscoreitemsVolumeSwapList=AdapterscoreitemsVolumeSwapList, AdapteritemsVolumeSwapList=AdapteritemsVolumeSwapList, UnderlyingscoreitemsCountSwapList=UnderlyingscoreitemsCountSwapList, UnderlyingtokenitemsCountSwapList=UnderlyingtokenitemsCountSwapList, UnderlyingscoreitemsVolumeSwapList=UnderlyingscoreitemsVolumeSwapList, UnderlyingtokenitemsVolumeSwapList=UnderlyingtokenitemsVolumeSwapList)


@app.route('/token/<tok>')
def token(tok):

    symbol = get_token(tok)

    daysList = []
    MostTokenSwapList = []
    TokenMostTokenSwapitemsList = []
    TokenTotalCountSwapList = []
    TokenTotalVolumeSwapList = []

    UnderlyingTokenTotalCountSwapList = []
    UnderlyingTokenTotalVolumeSwapList = []

    now = datetime.datetime.now()
    for i in range(0, 7):
        week_ago = now - datetime.timedelta(days=i)
        week_ago = week_ago.strftime('%Y-%m-%d')
        daysList.append(week_ago)
        MostTokenSwapList.append(f"tokenMostTokenSwap#{week_ago}#{tok}")

        TokenTotalCountSwap = redis.get(f"TokenCountSwap#{week_ago}#{tok}")
        if TokenTotalCountSwap is None:
            TokenTotalCountSwap = 0
        TokenTotalCountSwapList.append(int(TokenTotalCountSwap))

        tokenTotalVolumeSwap = redis.get(
            f"TokenVolumeSwap#{week_ago}#{tok}")
        if tokenTotalVolumeSwap is None:
            tokenTotalVolumeSwap = 0
        TokenTotalVolumeSwapList.append(int(tokenTotalVolumeSwap))

        UnderlyingTokenTotalCountSwap = redis.get(
            f"UnderlyingTokenCountSwap#{week_ago}#{tok}")
        if UnderlyingTokenTotalCountSwap is None:
            UnderlyingTokenTotalCountSwap = 0
        UnderlyingTokenTotalCountSwapList.append(
            int(UnderlyingTokenTotalCountSwap))

        UnderlyingtokenTotalVolumeSwap = redis.get(
            f"UnderlyingTokenVolumeSwap#{week_ago}#{tok}")
        if UnderlyingtokenTotalVolumeSwap is None:
            UnderlyingtokenTotalVolumeSwap = 0
        UnderlyingTokenTotalVolumeSwapList.append(
            int(UnderlyingtokenTotalVolumeSwap))

    daysList.reverse()
    TokenTotalCountSwapList.reverse()
    TokenTotalVolumeSwapList.reverse()
    UnderlyingTokenTotalCountSwapList.reverse()
    UnderlyingTokenTotalVolumeSwapList.reverse()

    redis.zunionstore(dest='TokenMostTokenSwapWeekly',
                      keys=MostTokenSwapList)

    newnow = now.strftime('%Y-%m-%d')

    TokenMostTokenSwap = redis.zrange(
        "TokenMostTokenSwapWeekly", 0, -1, desc=True, withscores=True)

    for tup in TokenMostTokenSwap:
        TokenMostTokenSwapitemsList.append({
         'x': get_adapter(tup[0]),
         'y': int(tup[1]),
        })

    return render_template('token.html', TokenMostTokenSwapitemsList=TokenMostTokenSwapitemsList, daysList=daysList, TokenTotalCountSwapList=TokenTotalCountSwapList, TokenTotalVolumeSwapList=TokenTotalVolumeSwapList, symbol=symbol, UnderlyingTokenTotalCountSwapList=UnderlyingTokenTotalCountSwapList, UnderlyingTokenTotalVolumeSwapList=UnderlyingTokenTotalVolumeSwapList)


@app.route('/adapter/<ad>')
def adapter(ad):

    symbol = get_adapter(ad)

    daysList = []
    MostTokenSwapList = []
    AdapterMostTokenSwapitemsList = []
    AdapterTotalCountSwapList = []
    AdapterTotalVolumeSwapList = []

    now = datetime.datetime.now()
    for i in range(0, 7):
        week_ago = now - datetime.timedelta(days=i)
        week_ago = week_ago.strftime('%Y-%m-%d')
        daysList.append(week_ago)
        MostTokenSwapList.append(f"AdapterMostTokenSwap#{week_ago}#{ad}")

        AdapterTotalCountSwap = redis.get(f"AdapterCountSwap#{week_ago}#{ad}")
        if AdapterTotalCountSwap is None:
            AdapterTotalCountSwap = 0
        AdapterTotalCountSwapList.append(int(AdapterTotalCountSwap))

        AdapterTotalVolumeSwap = redis.get(
            f"AdapterVolumeSwap#{week_ago}#{ad}")
        if AdapterTotalVolumeSwap is None:
            AdapterTotalVolumeSwap = 0
        AdapterTotalVolumeSwapList.append(int(AdapterTotalVolumeSwap))

    daysList.reverse()
    AdapterTotalCountSwapList.reverse()
    AdapterTotalVolumeSwapList.reverse()

    redis.zunionstore(dest='AdapterMostTokenSwapWeekly',
                      keys=MostTokenSwapList)

    newnow = now.strftime('%Y-%m-%d')

    AdapterMostTokenSwap = redis.zrange(
        "AdapterMostTokenSwapWeekly", 0, -1, desc=True, withscores=True)

    for tup in AdapterMostTokenSwap:
        AdapterMostTokenSwapitemsList.append({
         'x': get_token(tup[0]),
         'y': int(tup[1]),
        })

    return render_template('adapter.html', AdapterMostTokenSwapitemsList=AdapterMostTokenSwapitemsList, daysList=daysList, AdapterTotalCountSwapList=AdapterTotalCountSwapList, AdapterTotalVolumeSwapList=AdapterTotalVolumeSwapList, symbol=symbol)


@app.route('/contracts')
def contracts():
    adaptersList = []
    q_adapters = """ {adapters(orderBy: countSwaps, orderDirection: desc, where : {countSwaps_gt : "0", name_not : ""}) { id name } } """
    request = requests.post(
        'https://api.thegraph.com/subgraphs/name/yieldyak/yak-aggregator', json={'query': q_adapters})
    r = request.json()
    for adp in r['data']['adapters']:
        adaptersList.append({
            'address': adp['id'],
            'name': adp['name'].replace('YakAdapterV0', '').replace('AdapterV0', '').replace('V1YakAdapterV0', '').replace('V1', '').replace('Adapter', '')
        })

    tokensList = []
    q_tokens = """{tokens(orderBy: name, orderDirection: asc, where : {name_not : ""}, first : 400) { id symbol } }"""
    request = requests.post(
        'https://api.thegraph.com/subgraphs/name/yieldyak/yak-aggregator', json={'query': q_tokens})
    r = request.json()
    for token in r['data']['tokens']:
        tokensList.append({
            'address': token['id'],
            'name': token['symbol']
        })
    return render_template('contracts.html', adaptersList=adaptersList, tokensList=tokensList)


def web():
    app.run('0.0.0.0', port=80)


if __name__ == '__main__':
    threading.Thread(target=web, daemon=True).start()
    threading.Thread(target=get_swaps, daemon=True).start()
    while True:
        time.sleep(1)
