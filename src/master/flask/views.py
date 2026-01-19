import datetime

from flask import render_template, request
from werkzeug.utils import redirect

from .. import app, ctx
from ..config import config
from ..database import db
from collections import defaultdict


@app.route('/', defaults={'start': 0})
@app.route('/<int:start>')
def home(start):
    # Get current counts - from database if available, otherwise from in-memory context
    if db.is_connected:
        with db.get_cursor(commit=False) as cursor:
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM instances WHERE last_heartbeat > NOW() - INTERVAL '5 minutes') as instance_count,
                    (SELECT COUNT(*) FROM servers s JOIN instances i ON s.instance_id = i.id 
                     WHERE i.last_heartbeat > NOW() - INTERVAL '5 minutes') as server_count,
                    (SELECT COALESCE(SUM(s.clientnum), 0) FROM servers s JOIN instances i ON s.instance_id = i.id 
                     WHERE i.last_heartbeat > NOW() - INTERVAL '5 minutes') as client_count
            """)
            counts = cursor.fetchone()
            instance_count = counts['instance_count']
            server_count = counts['server_count']
            client_count = counts['client_count']
    else:
        # Fallback to in-memory context
        instance_count = len(ctx.instance_list)
        server_count = sum(len(inst.servers) for inst in ctx.instance_list.values())
        client_count = sum(s.clientnum for inst in ctx.instance_list.values() for s in inst.servers)

    return render_template('index.html',
                           title='API Overview',
                           grafana_base_url=config.grafana_base_url,
                           instance_count={'value': instance_count},
                           client_count={'value': client_count},
                           server_count={'value': server_count},
                           page_id='graph')


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
                           games=server_dict,
                           page_id='servers')


def count_by_key(source_key, source, dest_key, dest, sort_by='count', count_by='count', limit=9, metric_name='Metric',
                 metric_count='Count', formatter=None):
    if not source:
        dest[dest_key] = {}
        return

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
    if formatter:
        for tup in dest[dest_key]:
            formatter(tup[1])


@app.route('/stats')
def stats():
    stats_dict = {}

    server_list = [instance.servers for instance in ctx.instance_list.values()]
    flat_servers = [item for sublist in server_list for item in sublist]
    count_by_key('version', ctx.instance_list.values(), 'Instances By Version', stats_dict, metric_name='Version', metric_count='Instances')
    count_by_key('game', flat_servers, 'Servers By Game', stats_dict, metric_name='Game', metric_count='Servers')
    count_by_key('game', flat_servers, 'Players By Game', stats_dict, count_by='clientnum', metric_name='Game', metric_count='Players')
    count_by_key('gametype', flat_servers, 'Servers By Game Type', stats_dict, metric_name='Game Type', metric_count='Servers')
    count_by_key('gametype', flat_servers, 'Players By Game Type', stats_dict, count_by='clientnum', metric_name='Game Type', metric_count='Players')
    count_by_key('map', flat_servers, 'Servers By Map', stats_dict, metric_name='Map', metric_count='Servers')
    count_by_key('map', flat_servers, 'Players By Map', stats_dict, count_by='clientnum', metric_name='Map', metric_count='Players')

    def uptime_formatter(item):
        item['count'] = str(datetime.timedelta(seconds=item['count']))

    count_by_key('ip_address', ctx.instance_list.values(), 'Uptime By Instance', stats_dict, count_by='uptime', metric_name='IP Address', metric_count='Uptime', formatter=uptime_formatter)

    return render_template('stats.html', title='Stats', stats=stats_dict, page_id='stats')


@app.route('/plugin_subscriptions')
def hello():
    return redirect(
        f'https://store.raidmax.org/plugin_subscriptions?subscription_id={request.args.get("subscription_id")}&instance_id={request.args.get("instance_id")}',
        code=302)
