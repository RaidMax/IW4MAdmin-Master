from flask import render_template, request
from werkzeug.utils import redirect
from itertools import groupby

from .. import app, ctx
from ..resources.history_graph import HistoryGraph
from collections import defaultdict


@app.route('/', defaults={'start': 0})
@app.route('/<int:start>')
def home(start):
    _history_graph = HistoryGraph().get(start)

    return render_template('index.html',
                           title='API Overview',
                           history_graph=_history_graph[0]['message'],
                           instance_count=_history_graph[0]['instance_count'],
                           client_count=_history_graph[0]['client_count'],
                           server_count=_history_graph[0]['server_count'],
                           next_zoom_point=_history_graph[0]['next_zoom_point'],
                           previous_zoom_point=_history_graph[0]['previous_zoom_point'])


@app.route('/servers')
def servers():
    server_dict = defaultdict(list)
    if ctx.instance_list.values():
        ungrouped_servers = [server.set_instance(instance) for instance in ctx.instance_list.values() for server in
                             instance.servers]
        for server_group in sorted(ungrouped_servers, key=lambda server: server.game):
            server_dict[server_group.game].append(server_group)
    return render_template('serverlist.html',
                           title='Server List',
                           games=server_dict)


def count_by_key(source_key, source, dest_key, dest, sort_by='count', count_by='count', limit=9, metric_name='Metric',
                 metric_count='Count'):
    for instance in source:
        if not dest.get(dest_key):
            dest[dest_key] = {}

        segment = dest[dest_key]
        segment_value = segment.get(getattr(instance, source_key))

        if not segment_value:
            total = len(source) if count_by == 'count' else sum([getattr(item, count_by, 0) for item in source])
            segment[getattr(instance, source_key)] = {'count': 0, 'total': total, 'metric_name': metric_name,
                                                      'metric_count': metric_count}
        data = segment[getattr(instance, source_key)]

        if count_by == 'count':
            data['count'] = data['count'] + 1
        else:
            count_by_count_value = getattr(instance, count_by, 0)
            data['count'] = data['count'] + count_by_count_value

        data['percent'] = round((data['count'] / max(data['total'], 1)) * 100)

    dest[dest_key] = sorted(dest[dest_key].items(), key=lambda d: d[1][sort_by], reverse=True)[:limit]


@app.route('/stats')
def stats():
    stats_dict = {}

    server_list = [instance.servers for instance in ctx.instance_list.values()]
    flat_servers = [item for sublist in server_list for item in sublist]
    count_by_key('version', ctx.instance_list.values(), 'Instances By Version', stats_dict, metric_name='Version', metric_count='Instance Count')
    count_by_key('game', flat_servers, 'Servers By Game', stats_dict, metric_name='Game', metric_count='Servers')
    count_by_key('game', flat_servers, 'Players By Game', stats_dict, count_by='clientnum', metric_name='Game', metric_count='Players')
    count_by_key('gametype', flat_servers, 'Servers By GameType', stats_dict, metric_name='Game Type', metric_count='Servers')
    count_by_key('gametype', flat_servers, 'Players By GameType', stats_dict, count_by='clientnum', metric_name='Game Type', metric_count='Players')
    count_by_key('map', flat_servers, 'Servers By Map', stats_dict, metric_name='Map', metric_count='Servers')
    count_by_key('map', flat_servers, 'Players By Map', stats_dict, count_by='clientnum', metric_name='Map', metric_count='Players')

    return render_template('stats.html', title='Stats', stats=stats_dict)


@app.route('/plugin_subscriptions')
def hello():
    return redirect(
        f'http://api.raidmax.org/plugin_subscriptions?subscription_id={request.args.get("subscription_id")}&instance_id={request.args.get("instance_id")}',
        code=302)
