from flask import render_template, request
from werkzeug.utils import redirect

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


@app.route('/plugin_subscriptions')
def hello():
    return redirect(f'http://api.raidmax.org/plugin_subscriptions?subscription_id={request.args.get("subscription_id")}&instance_id={request.args.get("instance_id")}', code=302)
