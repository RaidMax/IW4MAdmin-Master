from flask import render_template, request
from werkzeug.utils import redirect

from .. import app
from ..config import config


@app.route('/', defaults={'start': 0})
@app.route('/<int:start>')
def home(start):
    return render_template('index.html',
                           title='Dashboard',
                           grafana_base_url=config.grafana_base_url,
                           page_id='graph')


@app.route('/servers')
def servers():
    return render_template('serverlist.html',
                           title='Server List',
                           grafana_base_url=config.grafana_base_url,
                           page_id='servers')


@app.route('/plugin_subscriptions')
def hello():
    return redirect(
        f'https://store.raidmax.org/plugin_subscriptions?subscription_id={request.args.get("subscription_id")}&instance_id={request.args.get("instance_id")}',
        code=302)

